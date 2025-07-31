"""Basic logging config tests for coverage."""

import logging
from unittest.mock import patch, MagicMock

from gtex_link.logging_config import configure_stdlib_logging, configure_logging


class TestLoggingConfigBasic:
    """Basic logging config tests."""

    def test_configure_stdlib_logging_development(self):
        """Test stdlib logging configuration in development mode."""
        with patch('gtex_link.logging_config.settings') as mock_settings, \
             patch('gtex_link.logging_config.logging') as mock_logging, \
             patch('gtex_link.logging_config.Console') as mock_console, \
             patch('gtex_link.logging_config.RichHandler') as mock_rich_handler:
            
            # Mock settings for development mode
            mock_settings.log_level = "DEBUG"
            mock_settings.reload = True
            
            # Mock logger
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = []
            mock_logging.getLogger.return_value = mock_root_logger
            mock_logging.DEBUG = 10
            
            # Mock console and handler
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            mock_handler = MagicMock()
            mock_rich_handler.return_value = mock_handler
            
            # Call function
            configure_stdlib_logging()
            
            # Verify development setup
            mock_root_logger.setLevel.assert_called_once_with(10)
            mock_console.assert_called_once()
            mock_rich_handler.assert_called_once()

    def test_configure_stdlib_logging_production(self):
        """Test stdlib logging configuration in production mode."""
        with patch('gtex_link.logging_config.settings') as mock_settings, \
             patch('gtex_link.logging_config.logging') as mock_logging, \
             patch('gtex_link.logging_config.sys') as mock_sys:
            
            # Mock settings for production mode
            mock_settings.log_level = "INFO"
            mock_settings.reload = False
            
            # Mock logger
            mock_root_logger = MagicMock()
            mock_root_logger.handlers = []
            mock_logging.getLogger.return_value = mock_root_logger
            mock_logging.INFO = 20
            mock_logging.StreamHandler = MagicMock()
            mock_logging.Formatter = MagicMock()
            
            # Call function
            configure_stdlib_logging()
            
            # Verify production setup
            mock_root_logger.setLevel.assert_called_once_with(20)
            mock_logging.StreamHandler.assert_called_once()

    def test_configure_logging_basic(self):
        """Test basic configure_logging function."""
        with patch('gtex_link.logging_config.configure_stdlib_logging') as mock_stdlib, \
             patch('gtex_link.logging_config.structlog') as mock_structlog:
            
            # Mock structlog configuration
            mock_logger = MagicMock()
            mock_structlog.get_logger.return_value = mock_logger
            
            # Call function
            result = configure_logging()
            
            # Verify calls
            mock_stdlib.assert_called_once()
            mock_structlog.configure.assert_called_once()
            mock_structlog.get_logger.assert_called_once_with("gtex_link")
            assert result == mock_logger

    def test_configure_logging_with_name(self):
        """Test configure_logging with custom name."""
        with patch('gtex_link.logging_config.configure_stdlib_logging') as mock_stdlib, \
             patch('gtex_link.logging_config.structlog') as mock_structlog:
            
            # Mock structlog configuration
            mock_logger = MagicMock()
            mock_structlog.get_logger.return_value = mock_logger
            
            # Call function with custom name
            result = configure_logging("custom_name")
            
            # Verify custom name was used
            mock_structlog.get_logger.assert_called_once_with("custom_name")
            assert result == mock_logger

    def test_imports_work(self):
        """Test that logging config module imports work."""
        from gtex_link import logging_config
        
        # Verify key functions exist
        assert hasattr(logging_config, 'configure_logging')
        assert hasattr(logging_config, 'configure_stdlib_logging')
        assert callable(logging_config.configure_logging)
        assert callable(logging_config.configure_stdlib_logging)