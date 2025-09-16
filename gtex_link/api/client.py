"""GTEx Portal API client with rate limiting and error handling."""

from __future__ import annotations

import asyncio
import json
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import httpx
from typing_extensions import Self

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
)
from gtex_link.logging_config import log_api_request, log_error_with_context

if TYPE_CHECKING:
    import types

    from structlog.typing import FilteringBoundLogger

    from gtex_link.config import GTExAPIConfigModel

# Constants
MAX_RESPONSE_TIMES = 100


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
            self._session = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept": "application/json",
                },
                follow_redirects=True,
            )
        return self._session

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client for backwards compatibility."""
        if self._session is None:
            raise RuntimeError("Session not initialized. Call _get_session() first.")
        return self._session

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
            if self.logger:
                self.logger.debug("Rate limit applied", wait_time=wait_time)
            await asyncio.sleep(wait_time)

        # Construct full URL
        url = urljoin(self.config.base_url, endpoint)

        # Get session (lazy initialization)
        session = await self._get_session()

        # Make request with retries
        last_error: Exception | None = None
        start_time = time.time()

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await session.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                )

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
                    error_text = response.text[:200] if response.text else "Unknown error"
                    msg = f"HTTP {response.status_code}: {error_text}"
                    raise GTExAPIError(
                        msg,
                        status_code=response.status_code,
                    )

                response.raise_for_status()

                # Track successful request statistics
                self.total_requests += 1
                self.successful_requests += 1
                self.response_times.append(response_time)
                # Keep only recent response times (last MAX_RESPONSE_TIMES requests)
                if len(self.response_times) > MAX_RESPONSE_TIMES:
                    self.response_times = self.response_times[-MAX_RESPONSE_TIMES:]

                # Parse JSON response
                try:
                    result = response.json()
                    if not isinstance(result, dict):
                        # If API returns a list or other type, wrap it
                        return {"data": result}
                    return result
                except json.JSONDecodeError as e:
                    if self.logger:
                        log_error_with_context(
                            self.logger,
                            e,
                            "JSON parsing failed",
                            {"url": url, "response_text": response.text[:200]},
                        )
                    msg = f"Invalid JSON response from {url}: {e}"
                    raise GTExAPIError(
                        msg,
                        status_code=response.status_code,
                        response_data={"raw_text": response.text[:200]},
                    ) from e

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = e
                response_time = time.time() - start_time

                if self.logger:
                    log_api_request(
                        self.logger,
                        method,
                        url,
                        response_time,
                        0,
                        error=str(e),
                    )

                if attempt < self.config.max_retries:
                    if self.logger:
                        self.logger.warning(
                            "Request failed, retrying",
                            attempt=attempt + 1,
                            max_retries=self.config.max_retries,
                            error=str(e),
                            url=url,
                        )
                    await asyncio.sleep(
                        self.config.retry_delay * (2**attempt)
                    )  # Exponential backoff
                    continue

        # All retries exhausted
        self.total_requests += 1
        if last_error:
            attempts = self.config.max_retries + 1
            msg = f"Failed to connect to GTEx Portal API after {attempts} attempts: {last_error}"
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
