"""Output validation handler -- guards against malformed MCP tool outputs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from gtex_link.mcp.untrusted_content import sanitize_message

if TYPE_CHECKING:
    from fastmcp import FastMCP

_logger = logging.getLogger("gtex_link.mcp.output_validation")


class _OutputValidationMiddleware(Middleware):
    """Log and re-raise errors raised while a tool is being dispatched.

    fastmcp 3.x exposes a class-based middleware API: hooks like
    `on_call_tool` are invoked around tool dispatch, and exceptions raised by
    the chained call propagate up. We do not swallow the exception -- fastmcp's
    `mask_error_details=True` translates it to a safe client message.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        try:
            return await call_next(context)
        except Exception as exc:
            tool_name = getattr(getattr(context, "message", None), "name", None)
            _logger.error(
                "MCP output validation failed",
                extra={
                    "tool": tool_name,
                    "error_type": type(exc).__name__,
                    # Sanitize before logging: the exception text can carry a
                    # caller-influenced upstream value with forbidden code points
                    # (no raw control/zero-width/bidi/NUL in the log sink).
                    "error": sanitize_message(str(exc)),
                },
            )
            raise


def install_output_validation_error_handler(mcp: FastMCP) -> None:
    """Install a handler that logs and re-raises output validation failures.

    fastmcp 3.x supports registering tool-call middleware; this hook wraps the
    tool dispatch path and surfaces structured logs when output validation
    fails. The handler does NOT swallow the exception -- fastmcp's
    `mask_error_details=True` translates it to a safe client message.
    """
    # Registered via add_middleware; the class-based hook API is on_call_tool.
    if not hasattr(mcp, "add_middleware"):
        _logger.warning("FastMCP instance lacks add_middleware; output validation skipped")
        return

    mcp.add_middleware(_OutputValidationMiddleware())
