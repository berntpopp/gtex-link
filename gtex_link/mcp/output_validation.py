"""Argument- and output-validation fencing at the MCP dispatch boundary."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

import mcp.types
from fastmcp.exceptions import ValidationError as FastMCPValidationError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from gtex_link.mcp.envelope import build_arg_error_envelope
from gtex_link.mcp.untrusted_content import sanitize_message

if TYPE_CHECKING:
    from fastmcp import FastMCP

_logger = logging.getLogger("gtex_link.mcp.output_validation")

# FastMCP logs the raw pydantic argument-validation detail -- which echoes the
# caller's input value (and any forbidden code points in it) -- at WARNING on
# this logger, outside our envelope. Sanitize that record at the source.
_FASTMCP_SERVER_LOGGER = "fastmcp.server.server"


class _SanitizeArgValidationLog(logging.Filter):
    """Drop the raw validation detail from FastMCP's arg-validation warning.

    The record template is ``"Invalid arguments for tool %r: %s"`` where the
    trailing ``%s`` is the pydantic error list echoing the caller's input; keep
    only the (server-controlled) tool name so the log stays useful without
    leaking the caller-supplied payload.
    """

    _PREFIX = "Invalid arguments for tool"

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str) and record.msg.startswith(self._PREFIX):
            name = record.args[0] if isinstance(record.args, tuple) and record.args else "?"
            record.msg = "Invalid arguments for tool %r (validation detail suppressed)"
            record.args = (name,)
        return True


class _OutputValidationMiddleware(Middleware):
    """Fence the two error paths that bypass ``run_mcp_tool``'s envelope.

    fastmcp 3.x exposes a class-based middleware API: ``on_call_tool`` wraps tool
    dispatch (argument validation + tool body), and exceptions raised by the
    chained call propagate here.

    - Argument-validation failures raise ``fastmcp.exceptions.ValidationError``
      BEFORE the tool body runs, so ``run_mcp_tool`` never sanitizes them and the
      raw pydantic message (which echoes the caller's input) would reach the model
      in TextContent. We convert them into a FIXED, body-free ``invalid_input``
      envelope (same shape as the classified error path).
    - Any other exception (e.g. an output-validation failure) is logged with a
      sanitized message and re-raised; fastmcp's ``mask_error_details=True`` then
      masks the caller-facing message.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", None)
        try:
            return await call_next(context)
        except FastMCPValidationError:
            _logger.warning("MCP argument validation failed for tool=%s", tool_name)
            envelope = build_arg_error_envelope(tool_name)
            return ToolResult(
                content=[mcp.types.TextContent(type="text", text=json.dumps(envelope))],
                structured_content=envelope,
                is_error=True,
            )
        except Exception as exc:
            _logger.error(
                "MCP output validation failed",
                extra={
                    "tool": tool_name,
                    "error_type": type(exc).__name__,
                    # Sanitize before logging: the exception text can carry a
                    # caller-influenced value with forbidden code points (no raw
                    # control/zero-width/bidi/NUL in the log sink).
                    "error": sanitize_message(str(exc)),
                },
            )
            raise


def install_output_validation_error_handler(mcp: FastMCP) -> None:
    """Install the arg/output validation fence + FastMCP arg-log sanitizer.

    Registers the class-based ``on_call_tool`` middleware and attaches a
    sanitizing filter to FastMCP's own server logger so the raw argument-
    validation detail is never emitted. The logger filter is idempotent (the
    logger is process-global; each ``create_gtex_mcp`` must not stack filters).
    """
    server_logger = logging.getLogger(_FASTMCP_SERVER_LOGGER)
    if not any(isinstance(f, _SanitizeArgValidationLog) for f in server_logger.filters):
        server_logger.addFilter(_SanitizeArgValidationLog())

    # Registered via add_middleware; the class-based hook API is on_call_tool.
    if not hasattr(mcp, "add_middleware"):
        _logger.warning("FastMCP instance lacks add_middleware; output validation skipped")
        return

    mcp.add_middleware(_OutputValidationMiddleware())
