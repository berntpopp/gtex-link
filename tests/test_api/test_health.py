"""Test health check endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi import status
from fastapi.testclient import TestClient

from gtex_link.exceptions import GTExAPIError
from gtex_link.models import ServiceInfo, Organization


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, test_client: TestClient):
        """Test basic health check endpoint."""
        response = test_client.get("/api/health/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "gtex-link"

    @patch("gtex_link.api.routes.health.ServiceDep")
    def test_readiness_check_success(self, mock_service_dep, test_client: TestClient):
        """Test successful readiness check."""
        # Mock service response
        mock_service = AsyncMock()
        mock_service.get_service_info.return_value = ServiceInfo(
            id="gtex_v2",
            name="GTEx Portal API",
            version="2.0.0",
            organization=Organization(name="GTEx Consortium", url="https://gtexportal.org"),
            description="High-performance API for GTEx Portal data",
            contact_url="https://gtexportal.org/contact",
            documentation_url="https://gtexportal.org/api/v2/docs",
            environment="production"
        )
        mock_service_dep.return_value = mock_service

        response = test_client.get("/api/health/ready")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ready"
        assert data["service"] == "gtex-link"
        assert data["gtex_api"] == "connected"
        assert "gtex_service_info" in data

    @patch("gtex_link.api.routes.health.ServiceDep")
    def test_readiness_check_api_error(self, mock_service_dep, test_client: TestClient):
        """Test readiness check with GTEx API error."""
        # Mock service to raise GTEx API error
        mock_service = AsyncMock()
        mock_service.get_service_info.side_effect = GTExAPIError("API unavailable")
        mock_service_dep.return_value = mock_service

        response = test_client.get("/api/health/ready")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "not_ready" in data["detail"]["status"]
        assert "disconnected" in data["detail"]["gtex_api"]

    @patch("gtex_link.api.routes.health.ServiceDep")
    def test_readiness_check_unexpected_error(self, mock_service_dep, test_client: TestClient):
        """Test readiness check with unexpected error."""
        # Mock service to raise unexpected error
        mock_service = AsyncMock()
        mock_service.get_service_info.side_effect = Exception("Unexpected error")
        mock_service_dep.return_value = mock_service

        response = test_client.get("/api/health/ready")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "error" in data["detail"]["status"]

    @patch("gtex_link.api.routes.health.ServiceDep")
    def test_service_stats(self, mock_service_dep, test_client: TestClient):
        """Test service statistics endpoint."""
        # Mock service with stats
        mock_service = AsyncMock()
        mock_service.cache_stats = {
            "hits": 10,
            "misses": 5,
            "hit_rate": 66.7,
            "total_requests": 15,
            "cached_functions": 3,
        }
        mock_service.client_stats = {
            "total_requests": 20,
            "successful_requests": 18,
            "success_rate": 0.9,
            "current_rate": 2.5,
            "avg_response_time": 0.15,
        }
        mock_service.get_cache_info.return_value = {
            "search_genes": {
                "hits": 5,
                "misses": 2,
                "current_size": 7,
                "max_size": 100,
                "hit_rate": 71.4,
            }
        }
        mock_service_dep.return_value = mock_service

        response = test_client.get("/api/health/stats")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cache" in data
        assert "client" in data
        assert data["cache"]["global_stats"]["hits"] == 10
        assert data["client"]["success_rate"] == 0.9
        assert "search_genes" in data["cache"]["function_stats"]

    @patch("gtex_link.api.routes.health.ServiceDep")
    def test_service_stats_error(self, mock_service_dep, test_client: TestClient):
        """Test service statistics endpoint with error."""
        # Mock service to raise error
        mock_service = AsyncMock()
        mock_service.cache_stats = Exception("Stats error")
        mock_service_dep.return_value = mock_service

        response = test_client.get("/api/health/stats")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to retrieve service statistics" in data["detail"]
