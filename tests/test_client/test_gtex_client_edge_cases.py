"""Edge case tests for GTEx API client to improve coverage."""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from gtex_link.api.client import GTExClient, TokenBucketRateLimiter
from gtex_link.config import GTExAPIConfigModel
from gtex_link.exceptions import GTExAPIError


class TestTokenBucketRateLimiterEdgeCases:
    """Test edge cases in TokenBucketRateLimiter that are missing coverage."""

    def test_current_rate_high_frequency(self):
        """Test current_rate calculation with very close timestamps."""
        limiter = TokenBucketRateLimiter(rate=5.0, burst=10)
        
        # Add timestamps very close together (but not identical due to float precision)
        now = time.time()
        limiter.request_times = [now, now, now]
        
        # Should return a high rate when timestamps are very close
        rate = limiter.current_rate()
        assert rate > 1000  # Very high rate due to small time window

    def test_current_rate_insufficient_requests(self):
        """Test current_rate with fewer than MIN_REQUESTS_FOR_RATE."""
        limiter = TokenBucketRateLimiter(rate=5.0, burst=10)
        
        # Add only 1 request (less than MIN_REQUESTS_FOR_RATE = 2)
        now = time.time()
        limiter.request_times = [now]
        
        # Should return 0.0 when insufficient requests
        rate = limiter.current_rate()
        assert rate == 0.0

    async def test_acquire_wait_time_calculation(self):
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
    def client_with_logger(self):
        """Create client with mock logger for testing."""
        config = GTExAPIConfigModel()
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(self, client_with_logger):
        """Test handling of invalid JSON responses."""
        client = client_with_logger
        
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON content"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            with pytest.raises(GTExAPIError) as exc_info:
                await client._make_request("GET", "test/endpoint")
            
            # Verify error message contains JSON parsing information
            assert "Invalid JSON response" in str(exc_info.value)
            
            # Verify logger was called for JSON parsing error
            client.logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_json_decode_error_without_logger(self):
        """Test JSON decode error handling without logger."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)  # No logger
        
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Invalid JSON content"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "doc", 0)
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            with pytest.raises(GTExAPIError) as exc_info:
                await client._make_request("GET", "test/endpoint")
            
            assert "Invalid JSON response" in str(exc_info.value)


class TestGTExClientResponseProcessing:
    """Test response processing edge cases."""

    @pytest.fixture
    def client_with_logger(self):
        """Create client with mock logger."""
        config = GTExAPIConfigModel()
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_response_times_truncation(self, client_with_logger):
        """Test response times list truncation when exceeding MAX_RESPONSE_TIMES."""
        client = client_with_logger
        
        # Fill response_times to exactly MAX_RESPONSE_TIMES (100)
        client.response_times = list(range(100))  # 100 items: [0, 1, 2, ..., 99]
        
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            await client._make_request("GET", "test/endpoint")
            
            # Adding one more should trigger truncation
            # Should still be MAX_RESPONSE_TIMES (100) items
            assert len(client.response_times) == 100
            # First item should now be 1 (original 0 was removed)
            assert client.response_times[0] == 1
            # Last item should be the response time from the request (not 99 anymore)
            assert client.response_times[-1] != 99

    @pytest.mark.asyncio
    async def test_successful_request_response_time_tracking(self, client_with_logger):
        """Test response time tracking for successful requests."""
        client = client_with_logger
        initial_count = len(client.response_times)
        
        # Mock a successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            result = await client._make_request("GET", "test/endpoint")
            
            # Verify response time was recorded
            assert len(client.response_times) == initial_count + 1
            assert result == {"data": "test"}


class TestGTExClientRateLimitingLogging:
    """Test rate limiting logging that's missing coverage."""

    @pytest.mark.asyncio
    async def test_rate_limit_logging_when_applied(self):
        """Test logging when rate limit is applied (wait_time > 0)."""
        config = GTExAPIConfigModel(rate_limit_per_second=1.0, burst_size=1)  # Very restrictive
        logger = MagicMock()
        client = GTExClient(config=config, logger=logger)
        
        # Mock session and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_response
        
        with patch.object(client, '_get_session', return_value=mock_session):
            # Make first request to consume tokens
            await client._make_request("GET", "test/endpoint1")
            
            # Make second request immediately - should trigger rate limiting
            await client._make_request("GET", "test/endpoint2")
            
            # Verify rate limit logging was called
            logger.debug.assert_called()
            # Check if any debug call was about rate limiting
            debug_calls = [call for call in logger.debug.call_args_list 
                          if len(call[0]) > 0 and "Rate limit applied" in call[0][0]]
            assert len(debug_calls) > 0

    @pytest.mark.asyncio 
    async def test_rate_limit_no_logging_without_logger(self):
        """Test rate limiting works without logger."""
        config = GTExAPIConfigModel(rate_limit_per_second=1.0, burst_size=1)
        client = GTExClient(config=config, logger=None)  # No logger
        
        # Mock session and response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        mock_session = AsyncMock()
        mock_session.request.return_value = mock_session
        mock_session.status_code = 200
        mock_session.json.return_value = {"data": "test"}
        
        with patch('httpx.AsyncClient.request', return_value=mock_response):
            # Should not raise error even without logger
            result = await client._make_request("GET", "test/endpoint")
            assert result == {"data": "test"}


class TestGTExClientRetryLogging:
    """Test retry logic logging that's missing coverage."""

    @pytest.fixture
    def client_with_logger(self):
        """Create client with logger and retry config."""
        config = GTExAPIConfigModel(max_retries=2, retry_delay=0.1)
        logger = MagicMock()
        return GTExClient(config=config, logger=logger)

    @pytest.mark.asyncio
    async def test_retry_warning_logging(self, client_with_logger):
        """Test retry warning logging when request fails and retries."""
        client = client_with_logger
        
        # Mock network error that triggers retry
        network_error = httpx.RequestError("Network error")
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"data": "success"}
        
        with patch('httpx.AsyncClient.request', side_effect=[network_error, success_response]):
            result = await client._make_request("GET", "test/endpoint")
            
            # Verify retry warning was logged
            client.logger.warning.assert_called()
            warning_calls = client.logger.warning.call_args_list
            retry_warnings = [call for call in warning_calls 
                            if len(call[0]) > 0 and "Request failed, retrying" in call[0][0]]
            assert len(retry_warnings) > 0
            
            # Verify successful result after retry
            assert result == {"data": "success"}

    @pytest.mark.asyncio
    async def test_error_logging_without_retry(self, client_with_logger):
        """Test error logging when max retries exceeded."""
        client = client_with_logger
        
        # Mock persistent network error
        network_error = httpx.RequestError("Persistent network error")
        
        with patch('httpx.AsyncClient.request', side_effect=network_error):
            with pytest.raises(GTExAPIError):
                await client._make_request("GET", "test/endpoint")
            
            # Verify error was logged
            client.logger.error.assert_called()


class TestGTExClientEndpointMethods:
    """Test specific endpoint methods that may have missing coverage."""

    @pytest.fixture
    def client_with_mock_request(self):
        """Create client with mocked _make_request method."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)
        
        # Mock the _make_request method
        client._make_request = AsyncMock(return_value={"data": "test"})
        return client

    @pytest.mark.asyncio
    async def test_get_service_info(self, client_with_mock_request):
        """Test get_service_info method."""
        client = client_with_mock_request
        
        result = await client.get_service_info()
        
        assert result == {"data": "test"}
        client._make_request.assert_called_once_with("GET", "")

    @pytest.mark.asyncio
    async def test_all_endpoint_methods(self, client_with_mock_request):
        """Test all endpoint methods for coverage."""
        client = client_with_mock_request
        params = {"test": "param"}
        
        # Test all endpoint methods
        endpoint_methods = [
            "search_genes", "get_genes", "get_transcripts", "get_exons",
            "get_neighbor_genes", "get_median_gene_expression", 
            "get_median_transcript_expression", "get_median_exon_expression",
            "get_median_junction_expression", "get_gene_expression",
            "get_top_expressed_genes", "get_single_nucleus_gene_expression",
            "get_tissue_site_details", "get_samples", "get_subjects",
            "get_variants", "get_variants_by_location"
        ]
        
        for method_name in endpoint_methods:
            method = getattr(client, method_name)
            result = await method(params)
            assert result == {"data": "test"}
        
        # Verify _make_request was called for each method
        assert client._make_request.call_count == len(endpoint_methods)

    def test_stats_method(self):
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
    async def test_context_manager_enter_returns_self(self):
        """Test that __aenter__ returns self."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)
        
        async with client as ctx_client:
            assert ctx_client is client

    @pytest.mark.asyncio
    async def test_context_manager_exit_with_exception(self):
        """Test __aexit__ handling with exception."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)
        
        # Mock close method to verify it's called
        client.close = AsyncMock()
        
        try:
            async with client:
                raise ValueError("Test exception")
        except ValueError:
            pass  # Expected
        
        # Verify close was called even with exception
        client.close.assert_called_once()


class TestGTExClientSessionProperties:
    """Test session-related properties and edge cases."""

    @pytest.mark.asyncio
    async def test_client_property_without_session(self):
        """Test client property when no session exists."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)
        
        # Should raise RuntimeError when no session exists
        with pytest.raises(RuntimeError, match="Session not initialized"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_client_property_with_session(self):
        """Test client property when session exists."""
        config = GTExAPIConfigModel()
        client = GTExClient(config=config, logger=None)
        
        # Initialize session
        await client._get_session()
        
        # Should return the session
        session = client.client
        assert isinstance(session, httpx.AsyncClient)