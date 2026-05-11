"""Edge case tests for GTEx API client to improve coverage."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from gtex_link.api.client import GTExClient, TokenBucketRateLimiter
from gtex_link.config import GTExAPIConfigModel
from gtex_link.exceptions import GTExAPIError

if TYPE_CHECKING:
    import respx

# GTExAPIConfigModel() defaults to the real GTEx Portal base URL; tests in this
# module instantiate clients with default config, so respx patterns target it.
GTEX_DEFAULT_BASE = "https://gtexportal.org/api/v2"


class TestTokenBucketRateLimiterEdgeCases:
    """Test edge cases in TokenBucketRateLimiter that are missing coverage."""

    def test_current_rate_high_frequency(self) -> None:
        """Test current_rate calculation with very close timestamps."""
        limiter = TokenBucketRateLimiter(rate=5.0, burst=10)

        # Timestamps very close together but not identical (current_rate
        # returns 0.0 when time_window == 0, so the oldest must be slightly
        # earlier than `now`)
        now = time.time()
        limiter.request_times = [now - 1e-6, now - 5e-7, now]

        # Should return a high rate when timestamps are very close
        rate = limiter.current_rate()
        assert rate > 1000  # Very high rate due to small time window

    def test_current_rate_insufficient_requests(self) -> None:
        """Test current_rate with fewer than MIN_REQUESTS_FOR_RATE."""
        limiter = TokenBucketRateLimiter(rate=5.0, burst=10)

        # Add only 1 request (less than MIN_REQUESTS_FOR_RATE = 2)
        now = time.time()
        limiter.request_times = [now]

        # Should return 0.0 when insufficient requests
        rate = limiter.current_rate()
        assert rate == 0.0

    async def test_acquire_wait_time_calculation(self) -> None:
        """Test wait time calculation when tokens are insufficient."""
        limiter = TokenBucketRateLimiter(rate=2.0, burst=1)  # Very restrictive

        # Consume all tokens
        await limiter.acquire()

        # Next acquire should return wait time > 0
        wait_time = await limiter.acquire()
        assert wait_time > 0
        # Wait time should be calculated as (1 - tokens) / rate
        # Since we consumed 1 token and have rate=2.0, we need 0.5 seconds to get 1 token
        assert wait_time >= 0.4  # Allow some tolerance for timing


class TestGTExClientJSONErrorHandling:
    """Test JSON parsing error handling that's missing coverage."""

    @pytest.fixture
    def client_with_logger(self) -> GTExClient:
        """Create client with mock logger for testing."""
        config = GTExAPIConfigModel()
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(
        self,
        client_with_logger: GTExClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test handling of invalid JSON responses."""
        client = client_with_logger

        # respx serves a 200 with non-JSON body; httpx.Response.json() will
        # raise JSONDecodeError when the client tries to parse it.
        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
            200,
            content=b"Invalid JSON content",
            headers={"content-type": "application/json"},
        )

        with pytest.raises(GTExAPIError) as exc_info:
            await client._make_request("GET", "test/endpoint")

        # Verify error message contains JSON parsing information
        assert "Invalid JSON response" in str(exc_info.value)

        # Verify logger was called for JSON parsing error
        assert client.logger is not None
        client.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_json_decode_error_without_logger(
        self,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test JSON decode error handling without logger."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)  # No logger

        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
            200,
            content=b"Invalid JSON content",
            headers={"content-type": "application/json"},
        )

        with pytest.raises(GTExAPIError) as exc_info:
            await client._make_request("GET", "test/endpoint")

        assert "Invalid JSON response" in str(exc_info.value)


class TestGTExClientResponseProcessing:
    """Test response processing edge cases."""

    @pytest.fixture
    def client_with_logger(self) -> GTExClient:
        """Create client with mock logger."""
        config = GTExAPIConfigModel()
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_response_times_truncation(
        self,
        client_with_logger: GTExClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test response times list truncation when exceeding MAX_RESPONSE_TIMES."""
        client = client_with_logger

        # Fill response_times to exactly MAX_RESPONSE_TIMES (100)
        client.response_times = [float(i) for i in range(100)]

        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(200, json={"data": "test"})

        await client._make_request("GET", "test/endpoint")

        # Adding one more should trigger truncation
        # Should still be MAX_RESPONSE_TIMES (100) items
        assert len(client.response_times) == 100
        # First item should now be 1.0 (original 0.0 was removed)
        assert client.response_times[0] == 1.0
        # Last item should be the response time from the request (not 99.0)
        assert client.response_times[-1] != 99.0

    @pytest.mark.asyncio
    async def test_successful_request_response_time_tracking(
        self,
        client_with_logger: GTExClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test response time tracking for successful requests."""
        client = client_with_logger
        initial_count = len(client.response_times)

        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(200, json={"data": "test"})

        result = await client._make_request("GET", "test/endpoint")

        # Verify response time was recorded
        assert len(client.response_times) == initial_count + 1
        assert result == {"data": "test"}


class TestGTExClientRateLimitingLogging:
    """Test rate limiting logging that's missing coverage."""

    @pytest.mark.asyncio
    async def test_rate_limit_logging_when_applied(
        self,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test logging when rate limit is applied (wait_time > 0)."""
        config = GTExAPIConfigModel(rate_limit_per_second=1.0, burst_size=1)  # Very restrictive
        logger = MagicMock()
        client = GTExClient(config=config, logger=logger)

        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint1").respond(200, json={"data": "test"})
        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint2").respond(200, json={"data": "test"})

        # Make first request to consume tokens
        await client._make_request("GET", "test/endpoint1")

        # Make second request immediately - should trigger rate limiting
        await client._make_request("GET", "test/endpoint2")

        # Verify rate limit logging was called
        logger.debug.assert_called()
        # Check if any debug call was about rate limiting
        debug_calls = [
            call
            for call in logger.debug.call_args_list
            if len(call[0]) > 0 and "Rate limit applied" in call[0][0]
        ]
        assert len(debug_calls) > 0

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limit_no_logging_without_logger(
        self,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test rate limiting works without logger."""
        config = GTExAPIConfigModel(rate_limit_per_second=1.0, burst_size=1)
        client = GTExClient(config=config, logger=None)  # No logger

        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(200, json={"data": "test"})

        # Should not raise error even without logger
        result = await client._make_request("GET", "test/endpoint")
        assert result == {"data": "test"}

        await client.close()


class TestGTExClientRetryLogging:
    """Test retry logic logging that's missing coverage."""

    @pytest.fixture
    def client_with_logger(self) -> GTExClient:
        """Create client with logger and retry config."""
        config = GTExAPIConfigModel(max_retries=2, retry_delay=0.1)
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_retry_warning_logging(
        self,
        client_with_logger: GTExClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test retry warning logging when request fails and retries."""
        client = client_with_logger

        # First call raises a network error, second call succeeds.
        # ``side_effect`` accepts a list of httpx-like objects/exceptions.
        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").mock(
            side_effect=[
                httpx.RequestError("Network error"),
                httpx.Response(200, json={"data": "success"}),
            ]
        )

        result = await client._make_request("GET", "test/endpoint")

        # Verify retry warning was logged
        assert client.logger is not None
        client.logger.warning.assert_called()
        warning_calls = client.logger.warning.call_args_list
        retry_warnings = [
            call
            for call in warning_calls
            if len(call[0]) > 0 and "Request failed, retrying" in call[0][0]
        ]
        assert len(retry_warnings) > 0

        # Verify successful result after retry
        assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_error_logging_without_retry(
        self,
        client_with_logger: GTExClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test error logging when max retries exceeded."""
        client = client_with_logger

        # Persistent network error on every attempt.
        respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").mock(
            side_effect=httpx.RequestError("Persistent network error")
        )

        with pytest.raises(GTExAPIError):
            await client._make_request("GET", "test/endpoint")

        # Verify error was logged
        assert client.logger is not None
        client.logger.error.assert_called()


class TestGTExClientEndpointMethods:
    """Test specific endpoint methods that may have missing coverage."""

    @pytest.fixture
    def client_with_mock_request(self) -> GTExClient:
        """Create client with mocked _make_request method."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        # Mock the _make_request method
        client._make_request = AsyncMock(return_value={"data": "test"})  # type: ignore[method-assign]
        return client

    @pytest.mark.asyncio
    async def test_get_service_info(self, client_with_mock_request: GTExClient) -> None:
        """Test get_service_info method."""
        client = client_with_mock_request

        result = await client.get_service_info()

        assert result == {"data": "test"}
        client._make_request.assert_called_once_with("GET", "")  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_all_endpoint_methods(self, client_with_mock_request: GTExClient) -> None:
        """Test all endpoint methods for coverage."""
        client = client_with_mock_request
        params = {"test": "param"}

        # Test all endpoint methods
        endpoint_methods = [
            "search_genes",
            "get_genes",
            "get_transcripts",
            "get_exons",
            "get_neighbor_genes",
            "get_median_gene_expression",
            "get_median_transcript_expression",
            "get_median_exon_expression",
            "get_median_junction_expression",
            "get_gene_expression",
            "get_top_expressed_genes",
            "get_single_nucleus_gene_expression",
            "get_tissue_site_details",
            "get_samples",
            "get_subjects",
            "get_variants",
            "get_variants_by_location",
        ]

        for method_name in endpoint_methods:
            method = getattr(client, method_name)
            result = await method(params)
            assert result == {"data": "test"}

        # Verify _make_request was called for each method
        assert client._make_request.call_count == len(endpoint_methods)  # type: ignore[attr-defined]

    def test_stats_method(self) -> None:
        """Test stats method for coverage."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        # Add some test data
        client.response_times = [0.1, 0.2, 0.3]
        client.total_requests = 3
        client.successful_requests = 3

        stats = client.stats

        # Check actual stats structure from the implementation
        assert "total_requests" in stats
        assert "successful_requests" in stats
        assert "success_rate" in stats
        assert "current_rate" in stats
        assert "current_tokens" in stats
        assert "avg_response_time" in stats

        assert stats["total_requests"] == 3
        assert stats["successful_requests"] == 3
        assert stats["success_rate"] == 1.0
        assert abs(stats["avg_response_time"] - 0.2) < 1e-10  # (0.1 + 0.2 + 0.3) / 3


class TestGTExClientContextManager:
    """Test context manager edge cases."""

    @pytest.mark.asyncio
    async def test_context_manager_enter_returns_self(self) -> None:
        """Test that __aenter__ returns self."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        async with client as ctx_client:
            assert ctx_client is client

    @pytest.mark.asyncio
    async def test_context_manager_exit_with_exception(self) -> None:
        """Test __aexit__ handling with exception."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        # Mock close method to verify it's called
        client.close = AsyncMock()  # type: ignore[method-assign]

        try:
            async with client:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected

        # Verify close was called even with exception
        client.close.assert_called_once()  # type: ignore[attr-defined]


class TestGTExClientSessionProperties:
    """Test session-related properties and edge cases."""

    @pytest.mark.asyncio
    async def test_client_property_without_session(self) -> None:
        """Test client property when no session exists."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        # Should raise RuntimeError when no session exists
        with pytest.raises(RuntimeError, match="Session not initialized"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_client_property_with_session(self) -> None:
        """Test client property when session exists."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)

        # Initialize session
        await client._get_session()

        # Should return the session
        session = client.client
        assert isinstance(session, httpx.AsyncClient)
