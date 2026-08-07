"""Test health check endpoints."""

from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from gtex_link import __version__
from gtex_link.exceptions import GTExAPIError, RateLimitError, ServiceUnavailableError
from gtex_link.models.responses import HealthResponse


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_success(self, test_client: TestClient):
        """Test successful health check endpoint."""
        from gtex_link.api.routes.dependencies import get_gtex_client

        # Mock successful GTEx API call
        mock_client = AsyncMock()
        mock_client.get_service_info.return_value = {"id": "gtex_v2"}

        async def mock_client_generator():
            yield mock_client

        # Override the dependency
        test_client.app.dependency_overrides[get_gtex_client] = mock_client_generator

        try:
            response = test_client.get("/api/health")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"
            assert data["version"] == __version__
            assert data["gtex_api"] == "available"
            assert data["cache"] in ["enabled", "disabled"]
            assert "uptime_seconds" in data
            assert isinstance(data["uptime_seconds"], (int, float))
        finally:
            # Clean up override
            test_client.app.dependency_overrides.clear()

    def test_version_info(self, test_client: TestClient):
        """Test version information endpoint."""
        response = test_client.get("/api/version")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["version"] == __version__
        assert data["api_version"] == "v1"
        assert "gtex_api" in data
        assert data["gtex_api"] == "https://gtexportal.org/api/v2/"

    def test_health_response_model_validation(self):
        """Test HealthResponse model validation."""
        # Test valid response
        valid_data = {
            "status": "healthy",
            "version": "1.0.0",
            "gtex_api": "available",
            "cache": "enabled",
            "uptime_seconds": 123.45,
        }
        health_response = HealthResponse(**valid_data)
        assert health_response.status == "healthy"
        assert health_response.uptime_seconds == 123.45

        # Test invalid uptime (negative)
        try:
            invalid_data = valid_data.copy()
            invalid_data["uptime_seconds"] = -1.0
            HealthResponse(**invalid_data)
            assert False, "Should have raised validation error"
        except Exception:
            pass  # Expected validation error


@pytest.mark.parametrize(
    "upstream_error",
    [
        ServiceUnavailableError("upstream 503"),
        RateLimitError("upstream 429"),
        GTExAPIError("retry exhaustion"),
    ],
)
def test_health_check_client_errors_are_degraded(
    test_client: TestClient, upstream_error: GTExAPIError
) -> None:
    """Client-layer upstream failures degrade the Portal diagnostic."""
    from gtex_link.api.routes.dependencies import get_gtex_client

    mock_client = AsyncMock()
    mock_client.get_service_info.side_effect = upstream_error

    async def mock_client_generator():
        yield mock_client

    test_client.app.dependency_overrides[get_gtex_client] = mock_client_generator
    try:
        response = test_client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["gtex_api"] == "unavailable"
    finally:
        test_client.app.dependency_overrides.clear()
