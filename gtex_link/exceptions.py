"""Custom exceptions for GTEx-Link."""

from __future__ import annotations

from typing import Any


class GTExAPIError(Exception):
    """Base exception for GTEx Portal API errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize GTEx API error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_data: Raw response data if available
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}

    def __str__(self) -> str:
        """Return string representation of error."""
        if self.status_code:
            return f"GTEx Portal API Error {self.status_code}: {self.message}"
        return f"GTEx Portal API Error: {self.message}"


class ValidationError(GTExAPIError):
    """Exception raised for input validation errors."""

    def __init__(self, message: str, field: str | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Error message
            field: Field name that failed validation
        """
        super().__init__(message)
        self.field = field

    def __str__(self) -> str:
        """Return string representation of validation error."""
        return self.message


class RateLimitError(GTExAPIError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        """Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ConfigurationError(GTExAPIError):
    """Exception raised for configuration errors."""

    def __init__(self, message: str, config_key: str | None = None) -> None:
        """Initialize configuration error.

        Args:
            message: Error message
            config_key: Configuration key that caused the error
        """
        super().__init__(message)
        self.config_key = config_key


class CacheError(GTExAPIError):
    """Exception raised for cache-related errors."""


class ServiceUnavailableError(GTExAPIError):
    """Exception raised when the GTEx Portal service is unavailable."""

    def __init__(
        self,
        message: str = "GTEx Portal service is temporarily unavailable",
    ) -> None:
        """Initialize service unavailable error.

        Args:
            message: Error message
        """
        super().__init__(message, status_code=503)
