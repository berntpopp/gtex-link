"""Tests for UnifiedServerManager."""

from __future__ import annotations

import os
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

    def test_configure_stdio_environment_sets_expected_vars(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify stdio environment vars are set so non-JSON output cannot
        corrupt the JSON-RPC stream on stdout."""
        for key in (
            "PYTHONUNBUFFERED",
            "GTEX_LINK_TRANSPORT",
            "FASTMCP_DISABLE_BANNER",
            "FASTMCP_NO_BANNER",
            "FASTMCP_QUIET",
            "NO_COLOR",
            "FORCE_COLOR",
            "TERM",
            "PYTHONWARNINGS",
        ):
            monkeypatch.delenv(key, raising=False)

        UnifiedServerManager._configure_stdio_environment()

        assert os.environ["PYTHONUNBUFFERED"] == "1"
        assert os.environ["GTEX_LINK_TRANSPORT"] == "stdio"
        assert os.environ["FASTMCP_DISABLE_BANNER"] == "1"
        assert os.environ["FASTMCP_NO_BANNER"] == "1"
        assert os.environ["FASTMCP_QUIET"] == "1"
        assert os.environ["NO_COLOR"] == "1"
        assert os.environ["FORCE_COLOR"] == "0"
        assert os.environ["TERM"] == "dumb"
        assert os.environ["PYTHONWARNINGS"] == "ignore"

    def test_configure_stdio_environment_does_not_overwrite(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Pre-set env vars are preserved (`setdefault`, not `[]=`)."""
        monkeypatch.setenv("NO_COLOR", "custom-value")
        UnifiedServerManager._configure_stdio_environment()
        assert os.environ["NO_COLOR"] == "custom-value"

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
