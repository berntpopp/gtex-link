"""Map internal exceptions to safe MCP error messages.

Combined with `FastMCP(mask_error_details=True)`, this prevents upstream
HTTP detail or stack-trace contents from leaking to MCP clients.
"""

from __future__ import annotations

# NOTE: superseded by gtex_link.mcp.envelope._classify for tool error handling.
# Retained only for any non-tool callers; new code should not import this.

from pydantic import ValidationError as PydanticValidationError

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


def map_to_mcp_error_message(exc: Exception) -> str:
    """Return a client-safe error message for an exception."""
    if isinstance(exc, RateLimitError):
        return "GTEx Portal rate limit exceeded. Try again shortly."
    if isinstance(exc, ServiceUnavailableError):
        return "GTEx Portal is temporarily unavailable. Try again later."
    if isinstance(exc, PydanticValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"]) or "input"
        return f"Invalid input -- `{loc}`: {first['msg']}"
    if isinstance(exc, ValidationError):
        field = f"`{exc.field}`: " if exc.field else ""
        return f"Invalid input -- {field}{exc.message}"
    if isinstance(exc, GTExAPIError):
        return "GTEx Portal returned an error. Verify the request inputs."
    return "An internal error occurred. The request was not completed."
