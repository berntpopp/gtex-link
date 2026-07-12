"""GTEx Portal API client with rate limiting and error handling."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Self
from urllib.parse import urljoin, urlsplit

import httpx
from asgi_correlation_id import correlation_id as _correlation_id_ctx

from gtex_link.api.url_guard import (
    DisallowedURLError,
    ResponseTooLargeError,
    build_allowed_origins,
    make_url_guard,
)
from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    UpstreamPolicyError,
)
from gtex_link.logging_config import log_api_request, log_error_with_context
from gtex_link.observability.metrics import (
    record_rate_limit_wait,
    record_upstream_call,
)


def _inject_correlation_header(headers: dict[str, str] | None) -> dict[str, str]:
    """Add the current correlation ID to outbound headers when available."""
    out = dict(headers) if headers else {}
    cid = _correlation_id_ctx.get()
    if cid and "X-Request-ID" not in out:
        out["X-Request-ID"] = cid
    return out


if TYPE_CHECKING:
    import types

    from structlog.typing import FilteringBoundLogger

    from gtex_link.config import GTExAPIConfigModel

# Constants
MAX_RESPONSE_TIMES = 100

# Fail-closed response byte cap (F-17). GTEx is GET-only JSON; a real multi-gene
# payload of ~1.73 MB has been observed, so the cap is generous (16 MB, never
# 2 MB) -- but a body past it is REFUSED, never truncated (a truncated JSON body
# is unparseable). Read as a module global at call time so tests can shrink it.
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API requests."""

    # Constants for rate calculation
    _RATE_WINDOW_SECONDS = 10.0
    _MIN_REQUESTS_FOR_RATE = 2

    def __init__(self, rate: float, burst: int = 1) -> None:
        """Initialize rate limiter.

        Args:
            rate: Requests per second
            burst: Maximum burst size
        """
        self.rate = rate
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last_update = time.time()
        self._lock = asyncio.Lock()
        self.request_times: list[float] = []

    async def acquire(self) -> float:
        """Acquire a token, waiting if necessary.

        Returns:
            Wait time in seconds (0 if no wait required)
        """
        async with self._lock:
            now = time.time()
            # Add tokens based on elapsed time
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= 1:
                self.tokens -= 1
                # Track request time for rate calculation
                self.request_times.append(now)
                # Keep only recent requests
                self.request_times = [
                    t for t in self.request_times if now - t <= self._RATE_WINDOW_SECONDS
                ]
                return 0.0
            # Calculate wait time for next token
            return (1 - self.tokens) / self.rate

    @property
    def current_tokens(self) -> float:
        """Get current number of available tokens without updating state."""
        now = time.time()
        elapsed = now - self.last_update
        return min(self.burst, self.tokens + elapsed * self.rate)

    def current_rate(self) -> float:
        """Get current rate based on recent request times.

        Returns:
            Current estimated rate in requests per second
        """
        now = time.time()
        # Clean up old request times
        recent_requests = [t for t in self.request_times if now - t <= self._RATE_WINDOW_SECONDS]

        if len(recent_requests) < self._MIN_REQUESTS_FOR_RATE:
            return 0.0

        # Calculate rate based on requests over time window
        time_window = now - recent_requests[0]
        if time_window <= 0:
            return 0.0

        return len(recent_requests) / time_window


class GTExClient:
    """HTTP client for GTEx Portal API with rate limiting and error handling."""

    # HTTP status code constants
    _HTTP_TOO_MANY_REQUESTS = 429
    _HTTP_SERVER_ERROR = 500
    _HTTP_CLIENT_ERROR = 400

    def __init__(
        self,
        config: GTExAPIConfigModel,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        """Initialize GTEx client.

        Args:
            config: API configuration
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger

        # Exact normalized origin allowlist for every outbound hop (F-17). Derived from the
        # configured base URL -- never hardcoded -- so an operator override of
        # base_url stays enforceable.
        self._allowed_origins = build_allowed_origins(config.base_url)

        # Initialize statistics tracking
        self.total_requests = 0
        self.successful_requests = 0
        self.response_times: list[float] = []

        # Initialize rate limiter (private attribute for tests)
        self._rate_limiter = TokenBucketRateLimiter(
            rate=config.rate_limit_per_second,
            burst=config.burst_size,
        )

        # Initialize HTTP session (lazy initialization)
        self._session: httpx.AsyncClient | None = None

    @property
    def rate_limiter(self) -> TokenBucketRateLimiter:
        """Get rate limiter (public accessor)."""
        return self._rate_limiter

    async def _get_session(self) -> httpx.AsyncClient:
        """Get or create HTTP session (lazy initialization).

        Returns:
            HTTP client session
        """
        if self._session is None:
            # Keep httpx's redirect machinery, but validate every hop (initial
            # request + each auto-followed redirect) via a request event-hook
            # (F-17). A cross-host / http-downgrade / userinfo hop raises the
            # non-retryable DisallowedURLError, mapped by _make_request.
            request_hooks: list[Callable[..., Any]] = [make_url_guard(self._allowed_origins)]
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "application/json",
                },
                follow_redirects=True,
                max_redirects=5,
                event_hooks={"request": request_hooks},
            )
        return self._session

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client for backwards compatibility."""
        if self._session is None:
            raise RuntimeError("Session not initialized. Call _get_session() first.")
        return self._session

    def _endpoint_label(self, url: str) -> str:
        """Reduce a full URL to a label suitable for a Prometheus counter."""
        path = urlsplit(url).path
        parts = [p for p in path.split("/") if p]
        return "/".join(parts[-3:]) if parts else "unknown"

    async def _read_capped_bytes(self, response: httpx.Response) -> bytes:
        """Read a response body under the fail-closed byte cap (F-17).

        Content-Length is a cheap first guard but is NOT trusted alone
        (chunked / gzip); the running total is enforced while streaming. A body
        past the cap is REFUSED (never truncated).

        Raises:
            ResponseTooLargeError: when the body exceeds ``MAX_RESPONSE_BYTES``.
        """
        max_bytes = MAX_RESPONSE_BYTES
        declared = response.headers.get("Content-Length")
        if declared is not None:
            try:
                declared_len = int(declared)
            except ValueError:
                declared_len = -1  # malformed -> rely on the streamed check
            if declared_len > max_bytes:
                raise ResponseTooLargeError()
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise ResponseTooLargeError()
            chunks.append(chunk)
        return b"".join(chunks)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._session is not None:
            await self._session.aclose()
            self._session = None

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with rate limiting and error handling.

        Args:
            method: HTTP method
            endpoint: API endpoint
            params: URL parameters
            data: Request body data

        Returns:
            Response data

        Raises:
            RateLimitError: When rate limit is exceeded
            ServiceUnavailableError: When service is unavailable
            GTExAPIError: For other API errors
        """
        # Apply rate limiting
        wait_time = await self._rate_limiter.acquire()
        if wait_time > 0:
            record_rate_limit_wait(wait_s=wait_time)
            if self.logger:
                self.logger.debug("Rate limit applied", wait_time=wait_time)
            await asyncio.sleep(wait_time)

        # Construct full URL
        url = urljoin(self.config.base_url, endpoint)

        # Build per-request headers; propagate inbound correlation ID if present.
        headers = _inject_correlation_header(None)

        # Get session (lazy initialization)
        session = await self._get_session()

        # Make request with retries
        last_error: Exception | None = None
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):
            attempt_start = time.time()
            status_for_metric = 0
            try:
                # Stream so the response body can be capped BEFORE decoding
                # (F-17). The request event-hook validates every hop (initial +
                # each auto-followed redirect) as it fires inside send().
                async with session.stream(
                    method,
                    url,
                    params=params,
                    json=data,
                    headers=headers,
                ) as response:
                    status_for_metric = response.status_code

                    response_time = time.time() - start_time

                    # Log successful request
                    if self.logger:
                        log_api_request(
                            self.logger,
                            method,
                            url,
                            response_time,
                            response.status_code,
                        )

                    # Handle different status codes
                    if response.status_code == self._HTTP_TOO_MANY_REQUESTS:
                        retry_after = float(response.headers.get("Retry-After", 60))
                        msg = f"Rate limit exceeded for {url}"
                        raise RateLimitError(
                            msg,
                            retry_after=retry_after,
                        )
                    if response.status_code >= self._HTTP_SERVER_ERROR:
                        msg = f"GTEx Portal service error: HTTP {response.status_code}"
                        raise ServiceUnavailableError(
                            msg,
                        )
                    if response.status_code >= self._HTTP_CLIENT_ERROR:
                        # Do NOT interpolate the upstream response BODY: a
                        # caller-influenced query can make GTEx reflect hostile
                        # prose (control/zero-width/bidi/NUL) into a 4xx body.
                        # The HTTP status is a safe bounded scalar; the body is
                        # never surfaced or logged (and is left unread).
                        msg = f"GTEx Portal rejected the request (HTTP {response.status_code})."
                        raise GTExAPIError(
                            msg,
                            status_code=response.status_code,
                        )

                    response.raise_for_status()

                    # Read the body under the fail-closed byte cap BEFORE decode
                    # (F-17); an oversized body is REFUSED, never truncated.
                    body = await self._read_capped_bytes(response)

                    # Track successful request statistics
                    self.total_requests += 1
                    self.successful_requests += 1
                    self.response_times.append(response_time)
                    # Keep only recent response times (last MAX_RESPONSE_TIMES).
                    if len(self.response_times) > MAX_RESPONSE_TIMES:
                        self.response_times = self.response_times[-MAX_RESPONSE_TIMES:]

                    # Parse JSON response
                    try:
                        result = json.loads(body)
                        if not isinstance(result, dict):
                            # If API returns a list or other type, wrap it
                            return {"data": result}
                        return result
                    except json.JSONDecodeError as e:
                        if self.logger:
                            # Log only the request path -- never the raw upstream
                            # body (no-PII-in-logs invariant); the response body
                            # can carry caller-influenced hostile prose.
                            log_error_with_context(
                                self.logger,
                                e,
                                "JSON parsing failed",
                                {"path": urlsplit(url).path},
                            )
                        # Fixed, body-free message: neither the raw body nor the
                        # URL (host) nor the decoder position text is surfaced.
                        msg = (
                            f"Invalid JSON response from GTEx Portal (HTTP {response.status_code})."
                        )
                        raise GTExAPIError(
                            msg,
                            status_code=response.status_code,
                        ) from e

            except (DisallowedURLError, ResponseTooLargeError, httpx.TooManyRedirects) as e:
                # Fail-closed URL/size policy violation on some hop (F-17).
                # NON-RETRYABLE: mapped to the dedicated UpstreamPolicyError so
                # the MCP error mapping classifies it retryable=False (a
                # deterministic policy block, not a transient upstream fault).
                # Body-free: str(e) can name a caller-influenced redirect host,
                # so log only the exception type + path. Chain with `from None`
                # (NOT `from e`) so a chained-exception log (`logger.exception`)
                # up the stack can never render the host via __cause__/__context__.
                if self.logger:
                    self.logger.warning(
                        "Outbound request blocked by URL/size policy",
                        error_type=type(e).__name__,
                        path=urlsplit(url).path,
                    )
                msg = "GTEx Portal request blocked by the URL/size policy."
                raise UpstreamPolicyError(msg) from None
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e
                response_time = time.time() - start_time

                if self.logger:
                    # Log only the exception TYPE (and path), never str(e): a
                    # transport error's text can reflect a caller-influenced
                    # value, so keep it out of the log sink.
                    log_api_request(
                        self.logger,
                        method,
                        url,
                        response_time,
                        0,
                        error=type(e).__name__,
                    )

                if attempt < self.config.max_retries:
                    if self.logger:
                        # Log only the request path + exception type, not str(e)
                        # (no caller-influenced transport text in the log sink).
                        self.logger.warning(
                            "Request failed, retrying",
                            attempt=attempt + 1,
                            max_retries=self.config.max_retries,
                            error_type=type(e).__name__,
                            path=urlsplit(url).path,
                        )
                    await asyncio.sleep(
                        self.config.retry_delay * (2**attempt)
                    )  # Exponential backoff
                    continue
            finally:
                record_upstream_call(
                    endpoint=self._endpoint_label(url),
                    status=status_for_metric,
                    duration_s=time.time() - attempt_start,
                )

        # All retries exhausted
        self.total_requests += 1
        if last_error:
            attempts = self.config.max_retries + 1
            # Do NOT interpolate the transport exception text: a reviewer probe
            # reproduced hostile control/zero-width/bidi/NUL code points reflected
            # through it. A fixed, detail-free message is raised (the exception
            # type is available in logs, not in the caller-visible message).
            msg = f"Failed to connect to GTEx Portal API after {attempts} attempts."
            raise GTExAPIError(
                msg,
            )
        msg = "Unknown error occurred"
        raise GTExAPIError(msg)

    # Service info endpoint
    async def get_service_info(self) -> dict[str, Any]:
        """Get GTEx Portal service information."""
        endpoint = self.config.endpoints["service_info"]
        return await self._make_request("GET", endpoint)

    # Reference endpoints
    async def search_genes(
        self,
        query: str,
        gencode_version: str | None = None,
        genome_build: str | None = None,
        page: int = 0,
        page_size: int = 250,
    ) -> dict[str, Any]:
        """Search for genes."""
        endpoint = self.config.endpoints["gene_search"]
        params = {
            "geneId": query,
            "page": page,
            "itemsPerPage": page_size,
        }
        if gencode_version:
            params["gencodeVersion"] = gencode_version
        if genome_build:
            params["genomeBuild"] = genome_build
        return await self._make_request("GET", endpoint, params=params)

    async def get_genes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get gene information."""
        endpoint = self.config.endpoints["gene"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_transcripts(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get transcript information."""
        endpoint = self.config.endpoints["transcript"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_exons(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get exon information."""
        endpoint = self.config.endpoints["exon"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_neighbor_genes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get neighboring genes."""
        endpoint = self.config.endpoints["neighbor_gene"]
        return await self._make_request("GET", endpoint, params=params)

    # Expression endpoints
    async def get_median_gene_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get median gene expression data."""
        endpoint = self.config.endpoints["median_gene_expression"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_median_transcript_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get median transcript expression data."""
        endpoint = self.config.endpoints["median_transcript_expression"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_median_exon_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get median exon expression data."""
        endpoint = self.config.endpoints["median_exon_expression"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_median_junction_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get median junction expression data."""
        endpoint = self.config.endpoints["median_junction_expression"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_gene_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get gene expression data."""
        endpoint = self.config.endpoints["gene_expression"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_top_expressed_genes(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get top expressed genes."""
        endpoint = self.config.endpoints["top_expressed_gene"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_single_nucleus_gene_expression(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get single nucleus gene expression data."""
        endpoint = self.config.endpoints["single_nucleus_gene_expression"]
        return await self._make_request("GET", endpoint, params=params)

    # Dataset endpoints
    async def get_tissue_site_details(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get tissue site details."""
        endpoint = self.config.endpoints["tissue_site_detail"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_samples(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get sample information."""
        endpoint = self.config.endpoints["sample"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_subjects(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get subject information."""
        endpoint = self.config.endpoints["subject"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_variants(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get variant information."""
        endpoint = self.config.endpoints["variant"]
        return await self._make_request("GET", endpoint, params=params)

    async def get_variants_by_location(self, params: dict[str, Any]) -> dict[str, Any]:
        """Get variants by genomic location."""
        endpoint = self.config.endpoints["variant_by_location"]
        return await self._make_request("GET", endpoint, params=params)

    @property
    def stats(self) -> dict[str, Any]:
        """Get client statistics."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "current_rate": self._rate_limiter.current_rate(),
            "current_tokens": self._rate_limiter.current_tokens,
            "avg_response_time": (
                sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
            ),
        }
