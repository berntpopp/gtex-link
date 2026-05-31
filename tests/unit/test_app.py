"""Tests for FastAPI app creation and configuration."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from gtex_link.app import app, create_app, lifespan


class TestAppCreation:
    """Test FastAPI application creation and configuration."""

    def test_create_app_basic(self) -> None:
        """Test basic app creation."""
        test_app = create_app()

        assert test_app.title == "GTEx-Link"
        assert test_app.version == "0.2.0"
        assert test_app.docs_url == "/docs"
        assert test_app.redoc_url == "/redoc"
        assert test_app.openapi_url == "/openapi.json"

    def test_app_root_endpoint(self) -> None:
        """Test root endpoint functionality."""
        with patch("gtex_link.app.settings") as mock_settings:
            mock_settings.mcp_path = "/mcp"

            client = TestClient(app)
            response = client.get("/")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "GTEx-Link"
            assert data["version"] == "0.2.0"
            assert data["docs"] == "/docs"
            assert data["health"] == "/api/health"
            assert data["metrics"] == "/metrics"
            assert data["mcp_endpoint"] == "/mcp"

    @pytest.mark.asyncio
    async def test_lifespan_manager(self) -> None:
        """Test application lifespan manager."""
        with (
            patch("gtex_link.app.configure_logging") as mock_configure,
            patch("gtex_link.app.log_server_startup") as mock_log_startup,
            patch("gtex_link.app.settings") as mock_settings,
        ):
            mock_logger = MagicMock()
            mock_configure.return_value = mock_logger
            mock_settings.host = "127.0.0.1"
            mock_settings.port = 8000

            mock_app = MagicMock()

            async with lifespan(mock_app):
                mock_configure.assert_called_once()
                mock_log_startup.assert_called_once_with(mock_logger, "startup", "127.0.0.1", 8000)

            mock_logger.info.assert_called_with("Application shutting down")

    def test_app_middleware_configuration(self) -> None:
        """Test CORS middleware configuration."""
        with patch("gtex_link.app.settings") as mock_settings:
            mock_settings.cors_origins = ["*"]
            mock_settings.cors_allow_credentials = True
            mock_settings.cors_allow_methods = ["GET", "POST"]
            mock_settings.cors_allow_headers = ["*"]

            test_app = create_app()

            assert len(test_app.user_middleware) > 0

    def test_app_router_inclusion(self) -> None:
        """Test that all routers are included."""
        test_app = create_app()

        routes = [route.path for route in test_app.routes if hasattr(route, "path")]

        assert "/" in routes
        assert any("/api/health" in str(route) for route in test_app.routes)

    def test_imports_work(self) -> None:
        """Test that all imports work correctly."""
        from gtex_link import app as app_module

        assert hasattr(app_module, "create_app")
        assert hasattr(app_module, "lifespan")
        assert hasattr(app_module, "app")
        assert callable(app_module.create_app)
