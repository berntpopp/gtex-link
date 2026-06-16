"""Tests for UnifiedServerManager."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from gtex_link.server_manager import UnifiedServerManager


class TestUnifiedServerManager:
    """Test UnifiedServerManager initialization and lifecycle."""

    def test_init_without_logger(self) -> None:
        manager = UnifiedServerManager()
        assert manager.logger is None
        assert manager._uvicorn_server is None

    def test_init_with_logger(self) -> None:
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)
        assert manager.logger is mock_logger
        assert manager._uvicorn_server is None

    def test_no_stdio_transport(self) -> None:
        """Streamable HTTP only: there is no stdio server entry point."""
        assert not hasattr(UnifiedServerManager, "start_stdio_server")
        assert not hasattr(UnifiedServerManager, "_configure_stdio_environment")

    @pytest.mark.asyncio
    async def test_shutdown_is_safe_without_running_server(self) -> None:
        """shutdown() handles the case where no uvicorn server has been started."""
        manager = UnifiedServerManager()
        await manager.shutdown()
        assert manager._uvicorn_server is None

    @pytest.mark.asyncio
    async def test_shutdown_signals_uvicorn_when_running(self) -> None:
        """shutdown() flips `should_exit` on the uvicorn server so its loop ends."""
        mock_server = MagicMock()
        mock_server.should_exit = False
        manager = UnifiedServerManager()
        manager._uvicorn_server = mock_server

        await manager.shutdown()

        assert mock_server.should_exit is True

    @pytest.mark.asyncio
    async def test_shutdown_logs_when_logger_present(self) -> None:
        """When a logger is wired, shutdown emits a structured info event."""
        mock_logger = MagicMock()
        manager = UnifiedServerManager(logger=mock_logger)

        await manager.shutdown()

        mock_logger.info.assert_called_with("Shutdown complete")
