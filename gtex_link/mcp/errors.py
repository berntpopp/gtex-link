"""Map internal exceptions to safe MCP error messages.

Combined with `FastMCP(mask_error_details=True)`, this prevents upstream
HTTP detail or stack-trace contents from leaking to MCP clients.
"""

from __future__ import annotations

# NOTE: superseded by gtex_link.mcp.envelope._classify for tool error handling.
# Retained only for any non-tool callers; new code should not import this.
from gtex_link.mcp.envelope import _classify


def map_to_mcp_error_message(exc: Exception) -> str:
    """Return a client-safe error message for an exception (one taxonomy: `_classify`)."""
    return _classify(exc)[1]
