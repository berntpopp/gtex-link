"""Integration tests for GTEx API client with real-world scenarios."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from gtex_link.api.client import GTExClient
from gtex_link.config import GTExAPIConfigModel
from gtex_link.exceptions import GTExAPIError, RateLimitError, ValidationError


class TestGTExClientInitialization:
    """Test GTEx client initialization and configuration."""

    def test_client_initialization_with_config(self, test_api_config):
        """Test client initialization with configuration."""
        logger = AsyncMock()
        client = GTExClient(config=test_api_config, logger=logger)

        assert client.config == test_api_config
        assert client.logger == logger
        assert client._rate_limiter is not None
        assert client._session is None  # Not initialized until first use

    def test_client_initialization_defaults(self):
        """Test client initialization with default configuration."""
        client = GTExClient()

        assert isinstance(client.config, GTExAPIConfigModel)
        assert client.config.base_url == "https://gtexportal.org/api/v2/"
        assert client.config.timeout == 30
        assert client.config.rate_limit_per_second == 5.0

    def test_client_custom_user_agent(self):
        """Test client with custom user agent."""
        config = GTExAPIConfigModel(user_agent="Custom-GTEx-Client/1.0.0")
        client = GTExClient(config=config)

        assert client.config.user_agent == "Custom-GTEx-Client/1.0.0"

    def test_client_rate_limiting_configuration(self):
        """Test client rate limiting configuration."""
        config = GTExAPIConfigModel(rate_limit_per_second=10.0, burst_size=50)
        client = GTExClient(config=config)

        assert client._rate_limiter.rate == 10.0
        assert client._rate_limiter.capacity == 50


class TestGTExClientSessionManagement:
    """Test client session management and lifecycle."""

    @pytest.mark.asyncio
    async def test_session_creation_and_cleanup(self, test_api_config):
        """Test session creation and proper cleanup."""
        logger = AsyncMock()
        client = GTExClient(config=test_api_config, logger=logger)

        # Session should be None initially
        assert client._session is None

        # Create session
        session = await client._get_session()
        assert isinstance(session, httpx.AsyncClient)
        assert client._session is session

        # Close client
        await client.close()
        assert client._session is None

    @pytest.mark.asyncio
    async def test_session_reuse(self, test_api_config):
        """Test that session is reused across multiple calls."""
        logger = AsyncMock()
        client = GTExClient(config=test_api_config, logger=logger)

        session1 = await client._get_session()
        session2 = await client._get_session()

        assert session1 is session2

        await client.close()

    @pytest.mark.asyncio
    async def test_session_headers_configuration(self, test_api_config):
        """Test that session has correct headers."""
        client = GTExClient(config=test_api_config)
        session = await client._get_session()

        assert "User-Agent" in session.headers
        assert "Accept" in session.headers
        assert session.headers["Accept"] == "application/json"

        await client.close()


class TestGTExClientRateLimiting:
    """Test client rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_rate_limiting_with_multiple_requests(self, test_api_config):
        """Test that rate limiting works with multiple requests."""
        # Configure very low rate limit for testing
        config = GTExAPIConfigModel(
            base_url=test_api_config.base_url, rate_limit_per_second=2.0, burst_size=2
        )

        client = GTExClient(config=config)

        # Mock successful responses
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": []}

            # Make multiple requests rapidly
            import asyncio

            tasks = [
                client.search_genes(query="BRCA1"),
                client.search_genes(query="TP53"),
                client.search_genes(query="EGFR"),
            ]

            # Should complete without rate limit errors due to token bucket
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All requests should succeed
            for result in results:
                assert not isinstance(result, Exception)

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limit_statistics(self, test_api_config):
        """Test rate limit statistics tracking."""
        client = GTExClient(config=test_api_config)

        # Initial stats should show full capacity
        stats = client.stats
        assert stats["current_tokens"] == test_api_config.burst_size
        assert stats["current_rate"] == test_api_config.rate_limit_per_second

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limiter_token_replenishment(self, test_api_config):
        """Test that rate limiter tokens are replenished over time."""
        import asyncio

        config = GTExAPIConfigModel(
            base_url=test_api_config.base_url,
            rate_limit_per_second=10.0,  # Fast replenishment for testing
            burst_size=5,
        )

        client = GTExClient(config=config)

        # Consume some tokens
        await client._rate_limiter.acquire(3)
        initial_tokens = client._rate_limiter.tokens

        # Wait for replenishment
        await asyncio.sleep(0.5)

        final_tokens = client._rate_limiter.tokens
        assert final_tokens > initial_tokens

        await client.close()


class TestGTExClientErrorHandling:
    """Test client error handling and retry logic."""

    @pytest.mark.asyncio
    async def test_http_error_handling(self, test_api_config):
        """Test handling of HTTP errors."""
        client = GTExClient(config=test_api_config)

        # Mock HTTP error response
        with patch.object(client, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"detail": "Not found"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404 Not Found", request=AsyncMock(), response=mock_response
            )

            mock_session.return_value.get.return_value = mock_response

            with pytest.raises(GTExAPIError) as exc_info:
                await client.search_genes(query="NONEXISTENT")

            assert "404" in str(exc_info.value)

        await client.close()

    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, test_api_config):
        """Test handling of rate limit errors from server."""
        client = GTExClient(config=test_api_config)

        # Mock rate limit response
        with patch.object(client, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.headers = {"Retry-After": "60"}
            mock_response.json.return_value = {"detail": "Rate limit exceeded"}
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "429 Too Many Requests", request=AsyncMock(), response=mock_response
            )

            mock_session.return_value.get.return_value = mock_response

            with pytest.raises(RateLimitError) as exc_info:
                await client.search_genes(query="BRCA1")

            assert "Rate limit exceeded" in str(exc_info.value)
            assert exc_info.value.retry_after == 60

        await client.close()

    @pytest.mark.asyncio
    async def test_network_timeout_handling(self, test_api_config):
        """Test handling of network timeouts."""
        client = GTExClient(config=test_api_config)

        # Mock timeout error
        with patch.object(client, "_get_session") as mock_session:
            mock_session.return_value.get.side_effect = httpx.TimeoutException("Request timed out")

            with pytest.raises(GTExAPIError) as exc_info:
                await client.search_genes(query="BRCA1")

            assert "timeout" in str(exc_info.value).lower()

        await client.close()

    @pytest.mark.asyncio
    async def test_retry_logic_on_server_errors(self, test_api_config):
        """Test retry logic on server errors."""
        config = GTExAPIConfigModel(
            base_url=test_api_config.base_url,
            max_retries=2,
            retry_delay=0.1,  # Fast retry for testing
        )

        client = GTExClient(config=config)

        # Mock server error followed by success
        with patch.object(client, "_get_session") as mock_session:
            mock_responses = [
                # First call - server error
                AsyncMock(),
                # Second call - success
                AsyncMock(),
            ]

            # Configure first response (server error)
            mock_responses[0].status_code = 500
            mock_responses[0].raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error", request=AsyncMock(), response=mock_responses[0]
            )

            # Configure second response (success)
            mock_responses[1].status_code = 200
            mock_responses[1].json.return_value = {"data": []}
            mock_responses[1].raise_for_status.return_value = None

            mock_session.return_value.get.side_effect = mock_responses

            # Should succeed after retry
            result = await client.search_genes(query="BRCA1")
            assert result == {"data": []}

            # Should have made 2 requests
            assert mock_session.return_value.get.call_count == 2

        await client.close()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, test_api_config):
        """Test behavior when max retries are exceeded."""
        config = GTExAPIConfigModel(
            base_url=test_api_config.base_url, max_retries=1, retry_delay=0.1
        )

        client = GTExClient(config=config)

        # Mock persistent server error
        with patch.object(client, "_get_session") as mock_session:
            mock_response = AsyncMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error", request=AsyncMock(), response=mock_response
            )

            mock_session.return_value.get.return_value = mock_response

            with pytest.raises(GTExAPIError):
                await client.search_genes(query="BRCA1")

            # Should have made initial request + 1 retry = 2 total
            assert mock_session.return_value.get.call_count == 2

        await client.close()


class TestGTExClientAPIOperations:
    """Test client API operations with mocked responses."""

    @pytest.mark.asyncio
    async def test_search_genes_success(self, test_api_config, gene_search_response):
        """Test successful gene search operation."""
        client = GTExClient(config=test_api_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = gene_search_response

            result = await client.search_genes(
                query="BRCA1", dataset_id="gtex_v8", page=0, page_size=250
            )

            assert result == gene_search_response
            mock_request.assert_called_once_with(
                "GET",
                client.config.endpoints["gene_search"],
                params={"query": "BRCA1", "datasetId": "gtex_v8", "page": 0, "itemsPerPage": 250},
            )

        await client.close()

    @pytest.mark.asyncio
    async def test_get_median_expression_success(self, test_api_config, median_expression_response):
        """Test successful median expression retrieval."""
        client = GTExClient(config=test_api_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = median_expression_response

            result = await client.get_median_gene_expression(
                gene_symbol=["BRCA1"],
                tissue_site_detail_id=["Breast_Mammary_Tissue"],
                dataset_id="gtex_v8",
            )

            assert result == median_expression_response
            mock_request.assert_called_once()

        await client.close()


    @pytest.mark.asyncio
    async def test_parameter_validation(self, test_api_config):
        """Test client-side parameter validation."""
        client = GTExClient(config=test_api_config)

        # Test invalid page size
        with pytest.raises(ValidationError):
            await client.search_genes(query="BRCA1", page_size=1001)

        # Test invalid page number
        with pytest.raises(ValidationError):
            await client.search_genes(query="BRCA1", page=-1)

        # Test empty query
        with pytest.raises(ValidationError):
            await client.search_genes(query="")

        await client.close()


class TestGTExClientStatistics:
    """Test client statistics tracking."""

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, test_api_config):
        """Test that client tracks statistics correctly."""
        client = GTExClient(config=test_api_config)

        # Initial stats
        initial_stats = client.stats
        assert initial_stats["total_requests"] == 0
        assert initial_stats["successful_requests"] == 0

        # Mock successful request
        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": []}

            await client.search_genes(query="BRCA1")

            # Check updated stats
            updated_stats = client.stats
            assert updated_stats["total_requests"] == 1
            assert updated_stats["successful_requests"] == 1
            assert updated_stats["success_rate"] == 1.0

        await client.close()

    @pytest.mark.asyncio
    async def test_statistics_with_failures(self, test_api_config):
        """Test statistics tracking with failures."""
        client = GTExClient(config=test_api_config)

        # Mock failed request
        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = GTExAPIError("API Error")

            with pytest.raises(GTExAPIError):
                await client.search_genes(query="BRCA1")

            # Check stats reflect failure
            stats = client.stats
            assert stats["total_requests"] == 1
            assert stats["successful_requests"] == 0
            assert stats["success_rate"] == 0.0

        await client.close()

    @pytest.mark.asyncio
    async def test_response_time_tracking(self, test_api_config):
        """Test response time tracking."""
        client = GTExClient(config=test_api_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": []}

            await client.search_genes(query="BRCA1")

            stats = client.stats
            assert "avg_response_time" in stats
            assert isinstance(stats["avg_response_time"], (int, float))
            assert stats["avg_response_time"] >= 0

        await client.close()


class TestGTExClientConcurrency:
    """Test client behavior under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, test_api_config):
        """Test handling of concurrent requests."""
        client = GTExClient(config=test_api_config)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": []}

            # Make multiple concurrent requests
            import asyncio

            async def make_request(gene):
                return await client.search_genes(query=gene)

            genes = ["BRCA1", "BRCA2", "TP53", "EGFR", "MYC"]
            tasks = [make_request(gene) for gene in genes]

            results = await asyncio.gather(*tasks)

            # All requests should succeed
            assert len(results) == 5
            for result in results:
                assert result == {"data": []}

            # Should have made 5 requests
            assert mock_request.call_count == 5

        await client.close()

    @pytest.mark.asyncio
    async def test_concurrent_session_safety(self, test_api_config):
        """Test that session sharing is thread-safe."""
        client = GTExClient(config=test_api_config)

        # Create multiple concurrent tasks that create sessions
        import asyncio

        async def get_session_task():
            return await client._get_session()

        tasks = [get_session_task() for _ in range(10)]
        sessions = await asyncio.gather(*tasks)

        # All should return the same session instance
        first_session = sessions[0]
        for session in sessions[1:]:
            assert session is first_session

        await client.close()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_high_concurrency_load(self, test_api_config):
        """Test client under high concurrent load."""
        config = GTExAPIConfigModel(
            base_url=test_api_config.base_url,
            rate_limit_per_second=50.0,  # Higher rate limit
            burst_size=100,
        )

        client = GTExClient(config=config)

        with patch.object(client, "_make_request") as mock_request:
            mock_request.return_value = {"data": []}

            # Make many concurrent requests
            import asyncio

            async def make_request(i):
                return await client.search_genes(query=f"GENE{i}")

            tasks = [make_request(i) for i in range(50)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful results
            successful = [r for r in results if not isinstance(r, Exception)]
            failed = [r for r in results if isinstance(r, Exception)]

            # Most requests should succeed (allowing for some rate limiting)
            assert len(successful) >= 40
            assert len(failed) <= 10

        await client.close()


class TestGTExClientCleanup:
    """Test client cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, test_api_config):
        """Test client cleanup when used as context manager."""
        session_ref = None

        async with GTExClient(config=test_api_config) as client:
            session_ref = await client._get_session()
            assert session_ref is not None
            assert not session_ref.is_closed

        # Session should be closed after context exit
        assert session_ref.is_closed

    @pytest.mark.asyncio
    async def test_explicit_close(self, test_api_config):
        """Test explicit client close."""
        client = GTExClient(config=test_api_config)
        session = await client._get_session()

        assert not session.is_closed

        await client.close()

        assert session.is_closed
        assert client._session is None

    @pytest.mark.asyncio
    async def test_double_close_safety(self, test_api_config):
        """Test that double close is safe."""
        client = GTExClient(config=test_api_config)
        await client._get_session()

        # First close
        await client.close()

        # Second close should not raise error
        await client.close()

    @pytest.mark.asyncio
    async def test_close_without_session(self, test_api_config):
        """Test closing client that never created session."""
        client = GTExClient(config=test_api_config)

        # Should not raise error
        await client.close()

        assert client._session is None
