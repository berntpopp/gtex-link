"""Tests for health check routes to achieve 100% coverage."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# TestClient import removed - not used in these tests

from gtex_link.api.routes.health import health_check, version_info, _start_time


class TestHealthRoutes:
    """Test health check routes."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        # Mock client and logger
        mock_client = AsyncMock()
        mock_client.get_service_info = AsyncMock(return_value={"version": "2.0"})
        mock_logger = MagicMock()

        # Mock settings
        with patch("gtex_link.api.routes.health.settings") as mock_settings:
            mock_settings.cache.stats_enabled = True

            # Call health check
            result = await health_check(mock_client, mock_logger)

            # Verify response
            assert result.status == "healthy"
            assert result.gtex_api == "available"
            assert result.cache == "enabled"
            assert result.version == "0.1.0"
            assert result.uptime_seconds > 0

            # Verify client was called
            mock_client.get_service_info.assert_called_once()
            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_gtex_failure(self):
        """Test health check when GTEx API fails."""
        # Mock client that fails
        mock_client = AsyncMock()
        import httpx

        mock_client.get_service_info = AsyncMock(side_effect=httpx.HTTPError("API down"))
        mock_logger = MagicMock()

        # Mock settings
        with patch("gtex_link.api.routes.health.settings") as mock_settings:
            mock_settings.cache.stats_enabled = False

            # Call health check
            result = await health_check(mock_client, mock_logger)

            # Verify degraded response
            assert result.status == "degraded"
            assert result.gtex_api == "unavailable"
            assert result.cache == "disabled"
            assert result.version == "0.1.0"

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            mock_logger.info.assert_called_once()

    @pytest.mark.asyncio
    async def test_version_info(self):
        """Test version info endpoint."""
        with patch("gtex_link.api.routes.health.settings") as mock_settings:
            mock_settings.api.base_url = "https://gtexportal.org/api/v2/"

            result = await version_info()

            assert result["version"] == "0.1.0"
            assert result["api_version"] == "v1"
            assert result["gtex_api"] == "https://gtexportal.org/api/v2/"

    def test_start_time_initialized(self):
        """Test that start time is initialized."""
        # Verify start time is a reasonable timestamp
        current_time = time.time()
        assert isinstance(_start_time, float)
        assert _start_time <= current_time
        assert current_time - _start_time < 3600  # Should be within an hour

    def test_imports_work(self):
        """Test that all imports work correctly."""
        from gtex_link.api.routes import health

        # Verify key components exist
        assert hasattr(health, "health_check")
        assert hasattr(health, "version_info")
        assert hasattr(health, "router")
        assert hasattr(health, "_start_time")
        assert callable(health.health_check)
        assert callable(health.version_info)
