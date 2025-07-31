"""Tests for FastAPI app creation and configuration."""

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from gtex_link.app import create_app, create_mcp_app, lifespan, app


class TestAppCreation:
    """Test FastAPI application creation and configuration."""

    def test_create_app_basic(self):
        """Test basic app creation."""
        test_app = create_app()
        
        # Verify app properties
        assert test_app.title == "GTEx-Link"
        assert test_app.version == "0.1.0"
        assert test_app.docs_url == "/docs"
        assert test_app.redoc_url == "/redoc"
        assert test_app.openapi_url == "/openapi.json"

    def test_app_root_endpoint(self):
        """Test root endpoint functionality."""
        with patch('gtex_link.app.settings') as mock_settings:
            mock_settings.mcp_path = "/mcp"
            
            client = TestClient(app)
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "GTEx-Link"
            assert data["version"] == "0.1.0"
            assert data["docs"] == "/docs"
            assert data["health"] == "/api/health"
            assert data["mcp_endpoint"] == "/mcp"

    @pytest.mark.asyncio
    async def test_lifespan_manager(self):
        """Test application lifespan manager."""
        with patch('gtex_link.app.configure_logging') as mock_configure, \
             patch('gtex_link.app.log_server_startup') as mock_log_startup, \
             patch('gtex_link.app.settings') as mock_settings:
            
            # Mock logger
            mock_logger = MagicMock()
            mock_configure.return_value = mock_logger
            mock_settings.host = "127.0.0.1"
            mock_settings.port = 8000
            
            # Create a mock FastAPI app
            mock_app = MagicMock()
            
            # Test lifespan context manager
            async with lifespan(mock_app):
                # Verify startup logging
                mock_configure.assert_called_once()
                mock_log_startup.assert_called_once_with(
                    mock_logger, "startup", "127.0.0.1", 8000
                )
            
            # Verify shutdown logging
            mock_logger.info.assert_called_with("Application shutting down")

    def test_create_mcp_app_success(self):
        """Test successful MCP app creation."""
        with patch('gtex_link.app.FastMCP') as mock_fastmcp, \
             patch('gtex_link.app.create_app') as mock_create_app:
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_create_app.return_value = mock_app
            
            # Mock FastMCP creation
            mock_mcp_instance = MagicMock()
            mock_fastmcp.from_fastapi.return_value = mock_mcp_instance
            
            # Call create_mcp_app
            result = create_mcp_app()
            
            # Verify FastMCP was called correctly
            mock_fastmcp.from_fastapi.assert_called_once()
            call_args = mock_fastmcp.from_fastapi.call_args
            assert call_args[1]["app"] == mock_app
            assert call_args[1]["name"] == "gtex-link"
            assert "mcp_names" in call_args[1]
            assert "route_maps" in call_args[1]
            
            assert result == mock_mcp_instance

    def test_mcp_name_mappings(self):
        """Test MCP custom name mappings are correct."""
        with patch('gtex_link.app.FastMCP') as mock_fastmcp, \
             patch('gtex_link.app.create_app'):
            
            mock_fastmcp.from_fastapi.return_value = MagicMock()
            
            create_mcp_app()
            
            # Verify custom name mappings
            call_args = mock_fastmcp.from_fastapi.call_args
            mcp_names = call_args[1]["mcp_names"]
            
            expected_mappings = {
                "search_genes": "search_gtex_genes",
                "get_genes": "get_gene_information",
                "get_transcripts": "get_transcript_information",
                "get_median_gene_expression": "get_median_expression_levels",
                "get_gene_expression": "get_individual_expression_data",
                "get_top_expressed_genes": "get_top_expressed_genes_by_tissue",
            }
            
            assert mcp_names == expected_mappings

    def test_app_middleware_configuration(self):
        """Test CORS middleware configuration."""
        with patch('gtex_link.app.settings') as mock_settings:
            mock_settings.cors_origins = ["*"]
            mock_settings.cors_allow_credentials = True
            mock_settings.cors_allow_methods = ["GET", "POST"]
            mock_settings.cors_allow_headers = ["*"]
            
            test_app = create_app()
            
            # Verify middleware was added (check middleware stack)
            assert len(test_app.user_middleware) > 0

    def test_app_router_inclusion(self):
        """Test that all routers are included."""
        test_app = create_app()
        
        # Get all route paths
        routes = [route.path for route in test_app.routes]
        
        # Verify key endpoints exist
        assert "/" in routes  # Root endpoint
        # Health routes should be included via router
        assert any("/api/health" in str(route) for route in test_app.routes)

    def test_mcp_route_maps_configuration(self):
        """Test MCP route maps are properly configured."""
        with patch('gtex_link.app.FastMCP') as mock_fastmcp, \
             patch('gtex_link.app.create_app'):
            
            mock_fastmcp.from_fastapi.return_value = MagicMock()
            
            create_mcp_app()
            
            # Verify route maps were configured
            call_args = mock_fastmcp.from_fastapi.call_args
            route_maps = call_args[1]["route_maps"]
            
            # Should have exclusion patterns
            assert len(route_maps) > 0
            patterns = [rm.pattern for rm in route_maps]
            assert any("health" in pattern for pattern in patterns)
            assert any("docs" in pattern for pattern in patterns)

    def test_imports_work(self):
        """Test that all imports work correctly."""
        from gtex_link import app as app_module
        
        # Verify key components exist
        assert hasattr(app_module, 'create_app')
        assert hasattr(app_module, 'create_mcp_app')
        assert hasattr(app_module, 'lifespan')
        assert hasattr(app_module, 'app')
        assert callable(app_module.create_app)
        assert callable(app_module.create_mcp_app)