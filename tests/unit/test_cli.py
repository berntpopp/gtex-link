"""Tests for the GTEx-Link typer CLI (GeneFoundry Logging & CLI Standard v1)."""

from __future__ import annotations

import re
from importlib.metadata import entry_points
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from gtex_link import __version__
from gtex_link.cli import app
from gtex_link.config import settings

runner = CliRunner()

# rich wraps `--help` output to the terminal width. Force a wide, color-free
# render and collapse whitespace so option-name substring checks are stable
# regardless of the CI terminal size (which is narrow and lacks a TTY).
_HELP_ENV = {"COLUMNS": "200", "TERM": "dumb", "NO_COLOR": "1"}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _help(args: list[str]) -> str:
    """Return the de-styled, whitespace-collapsed help text for ``args``."""
    result = runner.invoke(app, args, env=_HELP_ENV)
    assert result.exit_code == 0, result.output
    plain = _ANSI_RE.sub("", result.output)
    return re.sub(r"\s+", " ", plain)


class TestCliStructure:
    """The CLI exposes the standard-mandated command surface."""

    def test_no_args_is_help_not_bare_serve(self) -> None:
        """Invoking with no arguments shows help and never bare-serves."""
        result = runner.invoke(app, [], env=_HELP_ENV)
        plain = re.sub(r"\s+", " ", _ANSI_RE.sub("", result.output))
        for command in ("serve", "config", "health", "cache", "version"):
            assert command in plain

    def test_serve_command_present(self) -> None:
        output = _help(["serve", "--help"])
        for opt in (
            "--transport",
            "--host",
            "--port",
            "--mcp-path",
            "--log-level",
            "--disable-docs",
            "--dev",
        ):
            assert opt in output

    def test_config_command_present(self) -> None:
        assert "--validate" in _help(["config", "--help"])

    def test_health_command_present(self) -> None:
        assert "--url" in _help(["health", "--help"])

    def test_cache_command_present(self) -> None:
        output = _help(["cache", "--help"])
        assert "stats" in output
        assert "clear" in output

    def test_version_command_present(self) -> None:
        result = runner.invoke(app, ["version", "--help"], env=_HELP_ENV)
        assert result.exit_code == 0


class TestVersion:
    """`version` prints the installed version."""

    def test_version_prints_version(self) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestServeTransport:
    """`serve --transport` accepts unified/http and rejects stdio."""

    def test_transport_rejects_stdio(self) -> None:
        result = runner.invoke(app, ["serve", "--transport", "stdio"])
        assert result.exit_code == 2
        assert "stdio" in result.output

    def test_transport_rejects_unknown(self) -> None:
        result = runner.invoke(app, ["serve", "--transport", "bogus"])
        assert result.exit_code == 2

    def test_transport_accepts_unified(self) -> None:
        with (
            patch("gtex_link.cli.asyncio.run") as mock_run,
            patch("gtex_link.cli._serve", new_callable=MagicMock) as mock_serve,
        ):
            result = runner.invoke(app, ["serve", "--transport", "unified", "--port", "8123"])
            assert result.exit_code == 0
            mock_run.assert_called_once()
            mock_serve.assert_called_once_with(settings.host, 8123, unified=True)

    def test_transport_accepts_http(self) -> None:
        with (
            patch("gtex_link.cli.asyncio.run") as mock_run,
            patch("gtex_link.cli._serve", new_callable=MagicMock) as mock_serve,
        ):
            result = runner.invoke(app, ["serve", "--transport", "http", "--port", "8124"])
            assert result.exit_code == 0
            mock_run.assert_called_once()
            mock_serve.assert_called_once_with(settings.host, 8124, unified=False)

    def test_serve_dev_sets_debug_log_level(self) -> None:
        with (
            patch("gtex_link.cli.asyncio.run"),
            patch("gtex_link.cli._serve", new_callable=MagicMock),
        ):
            result = runner.invoke(app, ["serve", "--transport", "http", "--dev"])
            assert result.exit_code == 0
            assert settings.log_level == "DEBUG"
            assert settings.disable_docs is False


class TestConfig:
    """`config` shows and validates the resolved configuration."""

    def test_config_shows_settings(self) -> None:
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "transport" in result.output
        assert "mcp_path" in result.output

    def test_config_validate_ok(self) -> None:
        result = runner.invoke(app, ["config", "--validate"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()


class TestHealth:
    """`health` probes the running server's /api/health endpoint."""

    def test_health_connection_failure_exits_nonzero(self) -> None:
        import httpx

        with patch("gtex_link.cli.httpx.get", side_effect=httpx.ConnectError("nope")):
            result = runner.invoke(app, ["health", "--url", "http://127.0.0.1:9"])
            assert result.exit_code == 1

    def test_health_probes_api_health_path(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "version": __version__,
            "gtex_api": "available",
        }
        with patch("gtex_link.cli.httpx.get", return_value=mock_response) as mock_get:
            result = runner.invoke(app, ["health", "--url", "http://127.0.0.1:8000"])
            assert result.exit_code == 0
            assert "healthy" in result.output
            mock_get.assert_called_once()
            called_url = mock_get.call_args[0][0]
            assert called_url == "http://127.0.0.1:8000/api/health"

    def test_health_non_200_exits_nonzero(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        with patch("gtex_link.cli.httpx.get", return_value=mock_response):
            result = runner.invoke(app, ["health"])
            assert result.exit_code == 1


class TestCache:
    """`cache stats|clear` operate on the in-process service cache."""

    def test_cache_stats(self) -> None:
        result = runner.invoke(app, ["cache", "stats"])
        assert result.exit_code == 0
        assert "cache statistics" in result.output.lower()

    def test_cache_clear(self) -> None:
        result = runner.invoke(app, ["cache", "clear"])
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()


class TestEntryPoint:
    """The single console script resolves to the typer app."""

    def test_console_script_resolves_to_app(self) -> None:
        scripts = entry_points(group="console_scripts")
        gtex = [ep for ep in scripts if ep.name == "gtex-link"]
        assert gtex, "gtex-link console script not registered"
        assert gtex[0].value == "gtex_link.cli:app"
        # The loaded object is the typer app object.
        assert gtex[0].load() is app

    def test_no_stdio_entry_points(self) -> None:
        scripts = entry_points(group="console_scripts")
        names = {ep.name for ep in scripts}
        assert "gtex-link-mcp" not in names
        assert "gtex-mcp" not in names
