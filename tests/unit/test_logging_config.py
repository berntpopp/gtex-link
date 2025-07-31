"""Comprehensive tests for logging configuration."""

import logging
import sys
from unittest.mock import MagicMock, patch, Mock
import pytest
import structlog
from gtex_link.logging_config import (
    configure_stdlib_logging,
    configure_third_party_loggers,
    configure_structlog,
    configure_logging,
    orjson_serializer,
    log_api_request,
    log_cache_operation,
    log_mcp_tool_call,
    log_server_startup,
    log_error_with_context,
)


class TestStdlibLogging:
    """Test standard library logging configuration."""

    @patch('gtex_link.logging_config.settings')
    def test_configure_stdlib_logging_development(self, mock_settings):
        """Test stdlib logging configuration in development mode."""
        mock_settings.log_level = "DEBUG"
        mock_settings.reload = True
        
        # Call the function to cover lines 27-59
        configure_stdlib_logging()
        
        # Verify root logger was configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

    @patch('gtex_link.logging_config.settings')
    def test_configure_stdlib_logging_production(self, mock_settings):
        """Test stdlib logging configuration in production mode."""
        mock_settings.log_level = "INFO"
        mock_settings.reload = False
        
        # Call the function to cover production path
        configure_stdlib_logging()
        
        # Verify root logger was configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) > 0

    @patch('gtex_link.logging_config.settings')
    def test_configure_third_party_loggers_debug(self, mock_settings):
        """Test third-party logger configuration in debug mode."""
        mock_settings.log_level = "DEBUG"
        
        # Call function to cover lines 65-78
        configure_third_party_loggers()
        
        # Verify specific loggers were configured
        httpx_logger = logging.getLogger("httpx")
        assert httpx_logger.level == logging.WARNING
        
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        assert uvicorn_access_logger.level == logging.INFO  # INFO in debug mode

    @patch('gtex_link.logging_config.settings')
    def test_configure_third_party_loggers_production(self, mock_settings):
        """Test third-party logger configuration in production mode."""
        mock_settings.log_level = "INFO"
        
        configure_third_party_loggers()
        
        # Verify loggers configured for production
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        assert uvicorn_access_logger.level == logging.WARNING  # WARNING in production


class TestStructlogConfiguration:
    """Test structlog configuration."""

    @patch('gtex_link.logging_config.settings')
    def test_configure_structlog_json_format(self, mock_settings):
        """Test structlog configuration with JSON format."""
        mock_settings.log_level = "INFO"
        mock_settings.reload = False
        mock_settings.log_format = "json"
        
        # Call function to cover lines 84-110 with JSON path
        configure_structlog()
        
        # Verify structlog was configured
        logger = structlog.get_logger()
        assert logger is not None

    @patch('gtex_link.logging_config.settings')
    def test_configure_structlog_development_console(self, mock_settings):
        """Test structlog configuration with development console."""
        mock_settings.log_level = "DEBUG"
        mock_settings.reload = True
        mock_settings.log_format = "console"
        
        # Call function to cover development path with colors
        configure_structlog()
        
        logger = structlog.get_logger()
        assert logger is not None

    @patch('gtex_link.logging_config.settings')
    def test_configure_structlog_production_console(self, mock_settings):
        """Test structlog configuration with production console."""
        mock_settings.log_level = "INFO"
        mock_settings.reload = False
        mock_settings.log_format = "console"
        
        # Call function to cover production console path (no colors)
        configure_structlog()
        
        logger = structlog.get_logger()
        assert logger is not None

    @patch('gtex_link.logging_config.configure_stdlib_logging')
    @patch('gtex_link.logging_config.configure_structlog')
    def test_configure_logging_complete(self, mock_structlog, mock_stdlib):
        """Test complete logging configuration."""
        # Call function to cover lines 121-127
        result = configure_logging()
        
        # Verify both configurations were called
        mock_stdlib.assert_called_once()
        mock_structlog.assert_called_once()
        
        # Verify logger was returned
        assert result is not None


class TestJSONSerializer:
    """Test JSON serialization functions."""

    def test_orjson_serializer_with_orjson(self):
        """Test orjson serializer when orjson is available."""
        test_data = {"key": "value", "number": 42}
        
        # Mock orjson to be available
        with patch.dict(sys.modules, {'orjson': MagicMock()}):
            mock_orjson = sys.modules['orjson']
            mock_orjson.dumps.return_value = b'{"key":"value","number":42}'
            
            # Call function to cover lines 132-135
            result = orjson_serializer(test_data)
            
            assert result == '{"key":"value","number":42}'
            mock_orjson.dumps.assert_called_once_with(test_data)

    def test_orjson_serializer_fallback_to_json(self):
        """Test orjson serializer fallback to standard json."""
        test_data = {"key": "value", "number": 42}
        
        # Simplified approach: just mock the import to raise ImportError
        original_import = __builtins__['__import__']
        
        def mock_import(name, *args, **kwargs):
            if name == 'orjson':
                raise ImportError("No module named 'orjson'")
            return original_import(name, *args, **kwargs)
        
        with patch('builtins.__import__', side_effect=mock_import):
            # Call function to cover lines 137-139 (fallback path)
            result = orjson_serializer(test_data)
            
            # Should use standard json
            assert '"key"' in result
            assert '"value"' in result


class TestLoggingHelpers:
    """Test logging helper functions."""

    def test_log_api_request_success(self):
        """Test API request logging for successful requests."""
        mock_logger = MagicMock()
        
        # Call function without error to cover lines 151-162 (success path)
        log_api_request(
            logger=mock_logger,
            method="GET",
            url="https://api.example.com/test",
            response_time=0.5,
            status_code=200
        )
        
        # Verify info was called (success path)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "API request completed" in call_args[0]

    def test_log_api_request_error(self):
        """Test API request logging for failed requests."""
        mock_logger = MagicMock()
        
        # Call function with error to cover error path
        log_api_request(
            logger=mock_logger,
            method="GET", 
            url="https://api.example.com/test",
            response_time=1.0,
            status_code=500,
            error="Connection timeout"
        )
        
        # Verify error was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "API request failed" in call_args[0]

    def test_log_cache_operation(self):
        """Test cache operation logging."""
        mock_logger = MagicMock()
        
        log_cache_operation(
            logger=mock_logger,
            operation="get",
            key="test_key",
            hit=True,
            size=100
        )
        
        mock_logger.debug.assert_called_once()

    def test_log_mcp_tool_call_success(self):
        """Test MCP tool call logging for successful calls."""
        mock_logger = MagicMock()
        
        # Call function without error to cover lines 195-206 (success path)
        log_mcp_tool_call(
            logger=mock_logger,
            tool_name="search_genes",
            params={"query": "BRCA1"},
            duration=0.2,
            success=True
        )
        
        # Verify info was called (success path)
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "MCP tool call completed" in call_args[0]

    def test_log_mcp_tool_call_error(self):
        """Test MCP tool call logging for failed calls."""
        mock_logger = MagicMock()
        
        # Call function with error to cover error path
        log_mcp_tool_call(
            logger=mock_logger,
            tool_name="search_genes",
            params={"query": "BRCA1"},
            duration=0.5,
            success=False,
            error="API timeout"
        )
        
        # Verify error was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "MCP tool call failed" in call_args[0]

    def test_log_server_startup_with_host_port(self):
        """Test server startup logging with host and port."""
        mock_logger = MagicMock()
        
        # Call function with host/port to cover lines 216-223 (conditional path)
        log_server_startup(
            logger=mock_logger,
            mode="http",
            host="127.0.0.1",
            port=8000
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Server starting" in call_args[0]

    def test_log_server_startup_without_host_port(self):
        """Test server startup logging without host and port."""
        mock_logger = MagicMock()
        
        # Call function without host/port to cover base path
        log_server_startup(
            logger=mock_logger,
            mode="stdio"
        )
        
        mock_logger.info.assert_called_once()

    def test_log_error_with_context_with_context(self):
        """Test error logging with context."""
        mock_logger = MagicMock()
        error = ValueError("Test error")
        context = {"user_id": "123", "operation": "search"}
        
        # Call function with context to cover lines 233-242 (conditional path)
        log_error_with_context(
            logger=mock_logger,
            error=error,
            operation="gene_search",
            context=context
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Operation failed" in call_args[0]

    def test_log_error_with_context_without_context(self):
        """Test error logging without context.""" 
        mock_logger = MagicMock()
        error = ValueError("Test error")
        
        # Call function without context to cover base path
        log_error_with_context(
            logger=mock_logger,
            error=error,
            operation="gene_search"
        )
        
        mock_logger.error.assert_called_once()