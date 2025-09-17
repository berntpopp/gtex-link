"""Comprehensive tests for CLI functionality - simplified approach."""

import argparse
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gtex_link.cli import (
    create_parser,
    main,
    show_config,
)


class TestConfigDisplay:
    """Test configuration display functionality."""

    def test_show_config(self):
        """Test show_config displays configuration correctly."""
        with (
            patch("gtex_link.cli.get_api_config") as mock_get_api_config,
            patch("gtex_link.cli.get_cache_config") as mock_get_cache_config,
        ):
            # Mock API config
            mock_api_config = MagicMock()
            mock_api_config.base_url = "https://gtexportal.org/api/v2/"
            mock_api_config.timeout = 30.0
            mock_api_config.rate_limit_per_second = 5.0
            mock_api_config.burst_size = 10
            mock_api_config.max_retries = 3
            mock_api_config.retry_delay = 1.0
            mock_api_config.user_agent = "GTEx-Link/0.1.0"
            mock_get_api_config.return_value = mock_api_config

            # Mock cache config
            mock_cache_config = MagicMock()
            mock_cache_config.size = 1000
            mock_cache_config.ttl = 3600
            mock_cache_config.stats_enabled = True
            mock_cache_config.cleanup_interval = 60
            mock_get_cache_config.return_value = mock_cache_config

            # Test show_config
            show_config()

            mock_get_api_config.assert_called_once()
            mock_get_cache_config.assert_called_once()


class TestArgumentParser:
    """Test argument parser functionality."""

    def test_create_parser(self):
        """Test create_parser creates parser correctly."""
        parser = create_parser()

        assert isinstance(parser, argparse.ArgumentParser)
        assert "GTEx-Link" in parser.description

    def test_parser_server_command(self):
        """Test parser handles server command correctly."""
        parser = create_parser()
        args = parser.parse_args(
            ["server", "--host", "0.0.0.0", "--port", "8080", "--mode", "http", "--reload"]
        )

        assert args.command == "server"
        assert args.host == "0.0.0.0"
        assert args.port == 8080
        assert args.mode == "http"
        assert args.reload is True

    def test_parser_test_command(self):
        """Test parser handles test command correctly."""
        parser = create_parser()
        args = parser.parse_args(["test"])

        assert args.command == "test"

    def test_parser_search_command(self):
        """Test parser handles search command correctly."""
        parser = create_parser()
        args = parser.parse_args(["search", "BRCA1", "--limit", "20"])

        assert args.command == "search"
        assert args.query == "BRCA1"
        assert args.limit == 20

    def test_parser_config_command(self):
        """Test parser handles config command correctly."""
        parser = create_parser()
        args = parser.parse_args(["config"])

        assert args.command == "config"


class TestMainFunction:
    """Test main function and CLI entry point."""

    def test_main_no_command(self):
        """Test main function with no command specified."""
        with (
            patch("sys.argv", ["gtex-link"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = None
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Test main with no command
            main()

        assert exc_info.value.code == 1
        mock_parser.print_help.assert_called_once()

    def test_main_server_command(self):
        """Test main function with server command."""
        with (
            patch("sys.argv", ["gtex-link", "server"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "server"
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.mode = "http"
            mock_args.reload = False
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Test main with server command
            main()

            mock_asyncio_run.assert_called_once()

    def test_main_test_command_success(self):
        """Test main function with test command (success)."""
        with (
            patch("sys.argv", ["gtex-link", "test"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "test"
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to return True (success)
            mock_asyncio_run.return_value = True

            # Test main with test command (should exit 0)
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0

    def test_main_test_command_failure(self):
        """Test main function with test command (failure)."""
        with (
            patch("sys.argv", ["gtex-link", "test"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "test"
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to return False (failure)
            mock_asyncio_run.return_value = False

            # Test main with test command (should exit 1)
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_main_search_command(self):
        """Test main function with search command."""
        with (
            patch("sys.argv", ["gtex-link", "search", "BRCA1"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "search"
            mock_args.query = "BRCA1"
            mock_args.limit = 10
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Test main with search command
            main()

            mock_asyncio_run.assert_called_once()

    def test_main_config_command(self):
        """Test main function with config command."""
        with (
            patch("sys.argv", ["gtex-link", "config"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("gtex_link.cli.show_config") as mock_show_config,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "config"
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Test main with config command
            main()

            mock_show_config.assert_called_once()

    def test_main_unknown_command(self):
        """Test main function with unknown command."""
        with (
            patch("sys.argv", ["gtex-link", "unknown"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "unknown"
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Test main with unknown command
            main()

        assert exc_info.value.code == 1
        mock_parser.print_help.assert_called_once()

    def test_main_keyboard_interrupt(self):
        """Test main function handles KeyboardInterrupt."""
        with (
            patch("sys.argv", ["gtex-link", "server"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "server"
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.mode = "http"
            mock_args.reload = False
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to raise KeyboardInterrupt
            mock_asyncio_run.side_effect = KeyboardInterrupt()

            # Test main with KeyboardInterrupt
            main()

        assert exc_info.value.code == 1

    def test_main_value_error(self):
        """Test main function handles ValueError."""
        with (
            patch("sys.argv", ["gtex-link", "server"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "server"
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.mode = "http"
            mock_args.reload = False
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to raise ValueError
            mock_asyncio_run.side_effect = ValueError("Invalid argument")

            # Test main with ValueError
            main()

        assert exc_info.value.code == 1

    def test_main_runtime_error(self):
        """Test main function handles RuntimeError."""
        with (
            patch("sys.argv", ["gtex-link", "server"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "server"
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.mode = "http"
            mock_args.reload = False
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to raise RuntimeError
            mock_asyncio_run.side_effect = RuntimeError("Runtime error")

            # Test main with RuntimeError
            main()

        assert exc_info.value.code == 1

    def test_main_os_error(self):
        """Test main function handles OSError."""
        with (
            patch("sys.argv", ["gtex-link", "server"]),
            patch("gtex_link.cli.create_parser") as mock_create_parser,
            patch("asyncio.run") as mock_asyncio_run,
            pytest.raises(SystemExit) as exc_info,
        ):
            # Mock parser
            mock_parser = MagicMock()
            mock_args = MagicMock()
            mock_args.command = "server"
            mock_args.host = "127.0.0.1"
            mock_args.port = 8000
            mock_args.mode = "http"
            mock_args.reload = False
            mock_parser.parse_args.return_value = mock_args
            mock_create_parser.return_value = mock_parser

            # Mock asyncio.run to raise OSError
            mock_asyncio_run.side_effect = OSError("OS error")

            # Test main with OSError
            main()

        assert exc_info.value.code == 1


# Test async functions with functional approach
@pytest.mark.asyncio
async def test_run_server_success():
    """Test successful server startup using functional approach."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.ServerManager") as mock_server_manager_class,
    ):
        # Setup mocks
        from gtex_link.cli import run_server

        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger

        mock_server_manager = AsyncMock()
        mock_server_manager_class.return_value = mock_server_manager
        mock_server_manager.start_server = AsyncMock()

        # Test run_server
        await run_server(host="127.0.0.1", port=8000, mode="http", reload=False)

        mock_server_manager.start_server.assert_called_once_with(
            host="127.0.0.1", port=8000, mode="http", reload=False
        )


@pytest.mark.asyncio
async def test_run_server_keyboard_interrupt():
    """Test server runner handles KeyboardInterrupt."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.ServerManager") as mock_server_manager_class,
    ):
        from gtex_link.cli import run_server

        # Setup mocks
        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger

        mock_server_manager = AsyncMock()
        mock_server_manager_class.return_value = mock_server_manager
        mock_server_manager.start_server = AsyncMock(side_effect=KeyboardInterrupt())

        # Test run_server with KeyboardInterrupt
        await run_server()


@pytest.mark.asyncio
async def test_run_server_os_error():
    """Test server runner handles OSError."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.ServerManager") as mock_server_manager_class,
        pytest.raises(SystemExit) as exc_info,
    ):
        from gtex_link.cli import run_server

        # Setup mocks
        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger

        mock_server_manager = AsyncMock()
        mock_server_manager_class.return_value = mock_server_manager
        mock_server_manager.start_server = AsyncMock(side_effect=OSError("Port already in use"))

        # Test run_server with OSError
        await run_server()

    assert exc_info.value.code == 1


@pytest.mark.asyncio
async def test_run_server_runtime_error():
    """Test server runner handles RuntimeError."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.ServerManager") as mock_server_manager_class,
        pytest.raises(SystemExit) as exc_info,
    ):
        from gtex_link.cli import run_server

        # Setup mocks
        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger

        mock_server_manager = AsyncMock()
        mock_server_manager_class.return_value = mock_server_manager
        mock_server_manager.start_server = AsyncMock(side_effect=RuntimeError("Server error"))

        # Test run_server with RuntimeError
        await run_server()

    assert exc_info.value.code == 1


# Test connection and search functions by mocking at module level
@pytest.mark.asyncio
async def test_connection_success():
    """Test connection function with successful result."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.get_api_config") as mock_get_config,
    ):
        from gtex_link.cli import test_connection

        # Setup basic mocks
        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger
        mock_get_config.return_value = MagicMock()

        # Mock the import inside the function
        with patch.dict("sys.modules", {"gtex_link.api.client": MagicMock()}):
            mock_gtex_client = AsyncMock()
            mock_gtex_client.get_service_info = AsyncMock(return_value={"version": "2.0"})
            mock_gtex_client.__aenter__ = AsyncMock(return_value=mock_gtex_client)
            mock_gtex_client.__aexit__ = AsyncMock(return_value=None)

            sys.modules["gtex_link.api.client"].GTExClient = MagicMock(
                return_value=mock_gtex_client
            )

            # Test the function - it should succeed
            result = await test_connection()
            assert result is True


@pytest.mark.asyncio
async def test_search_genes_function():
    """Test search genes function with successful result."""
    with (
        patch("gtex_link.cli.configure_logging") as mock_configure,
        patch("gtex_link.cli.get_api_config") as mock_get_config,
        patch("gtex_link.cli.get_cache_config") as mock_get_cache_config,
    ):
        from gtex_link.cli import search_genes

        # Setup basic mocks
        mock_logger = MagicMock()
        mock_configure.return_value = mock_logger
        mock_get_config.return_value = MagicMock()
        mock_get_cache_config.return_value = MagicMock()

        # Mock the imports inside the function
        with patch.dict(
            "sys.modules",
            {"gtex_link.api.client": MagicMock(), "gtex_link.services.gtex_service": MagicMock()},
        ):
            import sys

            # Mock GTExClient
            mock_gtex_client = AsyncMock()
            mock_gtex_client.__aenter__ = AsyncMock(return_value=mock_gtex_client)
            mock_gtex_client.__aexit__ = AsyncMock(return_value=None)
            sys.modules["gtex_link.api.client"].GTExClient = MagicMock(
                return_value=mock_gtex_client
            )

            # Mock GTExService and results
            mock_service = AsyncMock()
            mock_result = MagicMock()
            mock_result.data = []  # Empty results to test no-results path
            mock_service.search_genes = AsyncMock(return_value=mock_result)
            sys.modules["gtex_link.services.gtex_service"].GTExService = MagicMock(
                return_value=mock_service
            )

            # Test the function
            await search_genes("TEST", 10)
            mock_service.search_genes.assert_called_once_with(query="TEST", page_size=10)
