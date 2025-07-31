"""Comprehensive tests for custom exceptions."""

import pytest

from gtex_link.exceptions import (
    GTExAPIError,
    ValidationError,
    RateLimitError,
    ConfigurationError,
    CacheError,
    ServiceUnavailableError,
)


class TestGTExAPIError:
    """Tests for GTExAPIError base exception."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = GTExAPIError("Test error message")
        assert error.message == "Test error message"
        assert error.status_code is None
        assert error.response_data == {}

    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        response_data = {"error": "details", "code": 400}
        error = GTExAPIError(
            message="Test error",
            status_code=400,
            response_data=response_data
        )
        assert error.message == "Test error"
        assert error.status_code == 400
        assert error.response_data == response_data

    def test_init_with_none_response_data(self):
        """Test initialization with None response_data."""
        error = GTExAPIError("Test error", response_data=None)
        assert error.response_data == {}

    def test_str_with_status_code(self):
        """Test string representation with status code."""
        error = GTExAPIError("Test error", status_code=404)
        assert str(error) == "GTEx Portal API Error 404: Test error"

    def test_str_without_status_code(self):
        """Test string representation without status code."""
        error = GTExAPIError("Test error")
        assert str(error) == "GTEx Portal API Error: Test error"

    def test_inheritance_from_exception(self):
        """Test that GTExAPIError inherits from Exception."""
        error = GTExAPIError("Test error")
        assert isinstance(error, Exception)


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = ValidationError("Invalid input")
        assert error.message == "Invalid input"
        assert error.field is None
        assert isinstance(error, GTExAPIError)

    def test_init_with_field(self):
        """Test initialization with field parameter."""
        error = ValidationError("Invalid value", field="gene_id")
        assert error.message == "Invalid value"
        assert error.field == "gene_id"

    def test_str_representation(self):
        """Test string representation."""
        error = ValidationError("Invalid input", field="test_field")
        assert str(error) == "Invalid input"

    def test_inheritance_from_gtex_api_error(self):
        """Test that ValidationError inherits from GTExAPIError."""
        error = ValidationError("Test error")
        assert isinstance(error, GTExAPIError)


class TestRateLimitError:
    """Tests for RateLimitError exception."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = RateLimitError("Rate limit exceeded")
        assert error.message == "Rate limit exceeded"
        assert error.status_code == 429
        assert error.retry_after is None
        assert isinstance(error, GTExAPIError)

    def test_init_with_retry_after(self):
        """Test initialization with retry_after parameter."""
        error = RateLimitError("Rate limit exceeded", retry_after=60.0)
        assert error.message == "Rate limit exceeded"
        assert error.retry_after == 60.0
        assert error.status_code == 429

    def test_inheritance_from_gtex_api_error(self):
        """Test that RateLimitError inherits from GTExAPIError."""
        error = RateLimitError("Test error")
        assert isinstance(error, GTExAPIError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_init_with_message_only(self):
        """Test initialization with message only."""
        error = ConfigurationError("Invalid configuration")
        assert error.message == "Invalid configuration"
        assert error.config_key is None
        assert isinstance(error, GTExAPIError)

    def test_init_with_config_key(self):
        """Test initialization with config_key parameter."""
        error = ConfigurationError("Invalid value", config_key="api_key")
        assert error.message == "Invalid value"
        assert error.config_key == "api_key"

    def test_inheritance_from_gtex_api_error(self):
        """Test that ConfigurationError inherits from GTExAPIError."""
        error = ConfigurationError("Test error")
        assert isinstance(error, GTExAPIError)


class TestCacheError:
    """Tests for CacheError exception."""

    def test_init(self):
        """Test initialization of CacheError."""
        error = CacheError("Cache operation failed")
        assert error.message == "Cache operation failed"
        assert isinstance(error, GTExAPIError)

    def test_inheritance_from_gtex_api_error(self):
        """Test that CacheError inherits from GTExAPIError."""
        error = CacheError("Test error")
        assert isinstance(error, GTExAPIError)


class TestServiceUnavailableError:
    """Tests for ServiceUnavailableError exception."""

    def test_init_with_default_message(self):
        """Test initialization with default message."""
        error = ServiceUnavailableError()
        assert error.message == "GTEx Portal service is temporarily unavailable"
        assert error.status_code == 503
        assert isinstance(error, GTExAPIError)

    def test_init_with_custom_message(self):
        """Test initialization with custom message."""
        custom_message = "Service down for maintenance"
        error = ServiceUnavailableError(custom_message)
        assert error.message == custom_message
        assert error.status_code == 503

    def test_inheritance_from_gtex_api_error(self):
        """Test that ServiceUnavailableError inherits from GTExAPIError."""
        error = ServiceUnavailableError()
        assert isinstance(error, GTExAPIError)


class TestExceptionIntegration:
    """Integration tests for exception functionality."""

    def test_all_exceptions_inherit_from_gtex_api_error(self):
        """Test that all custom exceptions inherit from GTExAPIError."""
        exceptions = [
            ValidationError("test"),
            RateLimitError("test"),
            ConfigurationError("test"),
            CacheError("test"),
            ServiceUnavailableError("test"),
        ]
        
        for exception in exceptions:
            assert isinstance(exception, GTExAPIError)
            assert isinstance(exception, Exception)

    def test_exception_raising_and_catching(self):
        """Test raising and catching custom exceptions."""
        # Test GTExAPIError
        with pytest.raises(GTExAPIError) as exc_info:
            raise GTExAPIError("Test error", status_code=400)
        assert exc_info.value.status_code == 400

        # Test ValidationError
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid field", field="test_field")
        assert exc_info.value.field == "test_field"

        # Test RateLimitError
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError("Rate limit exceeded", retry_after=30.0)
        assert exc_info.value.retry_after == 30.0

        # Test ConfigurationError  
        with pytest.raises(ConfigurationError) as exc_info:
            raise ConfigurationError("Bad config", config_key="api_url")
        assert exc_info.value.config_key == "api_url"

        # Test CacheError
        with pytest.raises(CacheError):
            raise CacheError("Cache failed")

        # Test ServiceUnavailableError
        with pytest.raises(ServiceUnavailableError) as exc_info:
            raise ServiceUnavailableError()
        assert exc_info.value.status_code == 503

    def test_exception_hierarchy_catching(self):
        """Test catching specific exceptions via base class."""
        # All custom exceptions should be catchable as GTExAPIError
        test_exceptions = [
            ValidationError("test"),
            RateLimitError("test"),
            ConfigurationError("test"),
            CacheError("test"),
            ServiceUnavailableError("test"),
        ]

        for exception in test_exceptions:
            with pytest.raises(GTExAPIError):
                raise exception