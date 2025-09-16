"""Tests for server manager module to achieve 90%+ coverage."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gtex_link.server_manager import UnifiedServerManager


class TestUnifiedServerManager:
    """Test UnifiedServerManager class."""

    def test_init_without_logger(self):
        """Test initialization without logger."""
        manager = UnifiedServerManager()
        assert manager.logger is None

    def test_init_with_logger(self):
        """Test initialization with logger."""
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)
        assert manager.logger is mock_logger

    @pytest.mark.asyncio
    async def test_start_server_http_mode(self):
        """Test starting server in HTTP mode."""
        with (
            patch("gtex_link.server_manager.uvicorn.Config") as mock_config,
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
        ):
            mock_logger = MagicMock()
            manager = UnifiedServerManager(logger=mock_logger)

            # Mock server instance
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            await manager.start_server(host="127.0.0.1", port=8000, mode="http", reload=False)

            # Verify config was created correctly
            mock_config.assert_called_once()
            config_call = mock_config.call_args
            assert config_call[1]["host"] == "127.0.0.1"
            assert config_call[1]["port"] == 8000
            assert config_call[1]["reload"] is False

            # Verify server was created and serve called
            mock_server_class.assert_called_once()
            mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_stdio_mode(self):
        """Test starting server in stdio mode."""
        with (
            patch("gtex_link.server_manager.mcp_app") as mock_mcp_app,
            patch.dict("os.environ", {}, clear=True),
        ):
            mock_logger = MagicMock()
            manager = UnifiedServerManager(logger=mock_logger)

            # Mock MCP app run method
            mock_mcp_app.run = AsyncMock()

            await manager.start_server(host="127.0.0.1", port=8000, mode="stdio", reload=True)

            # Verify environment variable was set and MCP app was called
            assert os.environ["TRANSPORT"] == "stdio"
            mock_mcp_app.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_unified_stdio_mode(self):
        """Test unified mode with TRANSPORT=stdio environment variable."""
        with (
            patch("gtex_link.server_manager.mcp_app") as mock_mcp_app,
            patch.dict("os.environ", {"TRANSPORT": "stdio"}, clear=True),
        ):
            mock_logger = MagicMock()
            manager = UnifiedServerManager(logger=mock_logger)

            # Mock MCP app run method
            mock_mcp_app.run = AsyncMock()

            await manager.start_server(host="127.0.0.1", port=8000, mode="unified", reload=False)

            # Should call MCP app since TRANSPORT=stdio
            mock_mcp_app.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_server_unified_mode(self):
        """Test starting server in unified mode (default)."""
        with (
            patch("gtex_link.server_manager.uvicorn.Config") as mock_config,
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
            patch.dict("os.environ", {}, clear=False),
        ):  # Ensure TRANSPORT is not set
            mock_logger = MagicMock()
            manager = UnifiedServerManager(logger=mock_logger)

            # Mock server instance
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            await manager.start_server(host="0.0.0.0", port=9000, mode="unified", reload=False)

            # Verify config was created correctly for HTTP server
            mock_config.assert_called_once()
            config_call = mock_config.call_args
            assert config_call[1]["host"] == "0.0.0.0"
            assert config_call[1]["port"] == 9000
            assert config_call[1]["reload"] is False

    @pytest.mark.asyncio
    async def test_start_server_default_parameters(self):
        """Test starting server with default parameters."""
        with (
            patch("gtex_link.server_manager.uvicorn.Config") as mock_config,
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
            patch.dict("os.environ", {}, clear=False),
        ):
            manager = UnifiedServerManager()

            # Mock server instance
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            await manager.start_server()

            # Verify default values were used
            mock_config.assert_called_once()
            config_call = mock_config.call_args
            assert config_call[1]["host"] == "127.0.0.1"
            assert config_call[1]["port"] == 8000
            assert config_call[1]["reload"] is False

    @pytest.mark.asyncio
    async def test_start_server_with_reload_option(self):
        """Test starting server with reload option."""
        with (
            patch("gtex_link.server_manager.uvicorn.Config") as mock_config,
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
            patch.dict("os.environ", {}, clear=False),
        ):
            manager = UnifiedServerManager()

            # Mock server instance
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            await manager.start_server(reload=True)

            # Verify reload was set
            mock_config.assert_called_once()
            config_call = mock_config.call_args
            assert config_call[1]["reload"] is True

    @pytest.mark.asyncio
    async def test_start_server_different_modes(self):
        """Test starting server with different mode values."""
        manager = UnifiedServerManager()

        # Test valid modes
        with (
            patch("gtex_link.server_manager.uvicorn.Config") as mock_config,
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
            patch.dict("os.environ", {}, clear=False),
        ):
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock()
            mock_server_class.return_value = mock_server

            # Test HTTP mode
            await manager.start_server(mode="http")
            mock_config.assert_called_once()

            # Test unified mode
            mock_config.reset_mock()
            await manager.start_server(mode="unified")
            mock_config.assert_called_once()

        # Test invalid mode should raise ValueError
        with pytest.raises(ValueError, match="Unknown server mode: invalid_mode"):
            await manager.start_server(mode="invalid_mode")

    def test_manager_attributes(self):
        """Test manager attributes and properties."""
        # Test without logger
        manager1 = UnifiedServerManager()
        assert hasattr(manager1, "logger")
        assert manager1.logger is None

        # Test with logger
        mock_logger = MagicMock()
        manager2 = UnifiedServerManager(logger=mock_logger)
        assert manager2.logger is mock_logger
        assert hasattr(manager2, "start_server")

    @pytest.mark.asyncio
    async def test_start_server_error_handling(self):
        """Test server startup error handling."""
        with (
            patch("gtex_link.server_manager.uvicorn.Config"),
            patch("gtex_link.server_manager.uvicorn.Server") as mock_server_class,
            patch.dict("os.environ", {}, clear=False),
        ):
            manager = UnifiedServerManager()

            # Mock server to raise an exception during serve
            mock_server = AsyncMock()
            mock_server.serve = AsyncMock(side_effect=Exception("Server failed to start"))
            mock_server_class.return_value = mock_server

            # The exception should propagate
            with pytest.raises(Exception, match="Server failed to start"):
                await manager.start_server()

    def test_import_dependencies(self):
        """Test that all required dependencies are importable."""
        # Test that the module imports work
        import uvicorn

        from gtex_link.app import app, mcp_app
        from gtex_link.server_manager import UnifiedServerManager

        # Verify classes and functions exist
        assert UnifiedServerManager is not None
        assert app is not None
        assert mcp_app is not None
        assert uvicorn is not None
