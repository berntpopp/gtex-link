"""Argument-, output-, and not-found fencing at the MCP dispatch boundary.

Three concerns are fenced here so no caller-supplied value (or the forbidden code
points it may carry) reaches the caller or a log sink:

1. **Argument / output validation** (``_OutputValidationMiddleware``): FastMCP
   validates tool arguments (pydantic) BEFORE the tool body runs, so an invalid or
   unknown argument raises ``fastmcp.exceptions.ValidationError`` outside
   ``run_mcp_tool``'s envelope; it is converted to a FIXED ``invalid_input`` frame.

2. **FastMCP-core not-found reflection** (the layered guard): FastMCP core reflects
   the caller's OWN requested tool NAME / resource URI back to the caller and logs
   BEFORE this middleware runs -- an unknown ``Unknown tool: '<name>'`` (raised or
   returned) and an ``Unknown resource: '<uri>'`` / malformed-URI pydantic echo.
   The guard closes this with a *union* of reference-fleet layers:

   - Layer 1 -- registry preflight in ``on_call_tool``: ``get_tool`` returns ``None``
     for an unknown tool, so we return a FIXED, name-free ``not_found`` envelope
     BEFORE core dispatch.
   - Layer 2 -- ``on_read_resource``: any read failure re-raises a FIXED, URI-free
     ``ResourceError`` (never the requested URI / error detail).
   - Layer 3 -- ``install_protocol_error_handler``: an OUTERMOST wrap of the raw
     tool/resource/prompt request handlers that replaces any non-structured
     ``isError`` tool result, and catches dispatch exceptions (incl. the
     malformed-URI ``-32602`` raised before ``on_read_resource`` fires), with FIXED
     input-free messages.

3. **Log hygiene** (Layer 5 -- ``_ValidationLogScrubFilter`` /
   ``install_validation_log_filter``): FastMCP core and the MCP SDK reflect the
   caller-supplied tool NAME / resource URI (with any control/zero-width/bidi/NUL
   code points) into their OWN log records BEFORE this middleware runs, on several
   loggers and at several levels that ``mask_error_details`` does not touch:

   - ``fastmcp.server.server`` -- ``Invalid arguments for tool`` / ``Error calling
     tool`` / ``Error reading resource`` (WARNING; caller input in ``args``);
   - ``fastmcp.server.mixins.mcp_operations`` -- ``Handler called: call_tool
     <name>`` / ``read_resource <uri>`` (DEBUG; pre-middleware);
   - ``mcp.server.lowlevel.server`` -- ``Tool cache miss for <name>`` (DEBUG);
   - the ROOT logger (bare ``logging.warning``/``logging.debug`` in
     ``mcp.shared.session._receive_loop``) -- ``Failed to validate request`` /
     ``Message that failed validation`` (WARNING/DEBUG), which reflects a malformed
     or forbidden-code-point resource URI rejected during request deserialization
     BEFORE any typed request reaches the Layer-3 handler wrapper.

   A single scrub filter, attached to every source logger AND its handlers (incl.
   the ``fastmcp`` logger's non-propagating Rich handlers), replaces any matching
   record's whole payload with a fixed constant and clears ``args`` / ``exc_info``
   / ``exc_text`` / ``stack_info`` at ALL levels, so caller input never reaches a
   log/telemetry sink.

(No OpenTelemetry span redaction is installed: ``opentelemetry-sdk`` is not a
dependency, so spans are non-recording and the exception-attribute surface is
inert. Do not add the SDK dependency for this.)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, cast

import mcp.types
from fastmcp.exceptions import ResourceError
from fastmcp.exceptions import ValidationError as FastMCPValidationError
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.tools.tool import ToolResult

from gtex_link.mcp.envelope import build_arg_error_envelope, build_unknown_tool_envelope
from gtex_link.mcp.untrusted_content import sanitize_message

if TYPE_CHECKING:
    from fastmcp import FastMCP

_logger = logging.getLogger("gtex_link.mcp.output_validation")

#: FIXED, input-free public messages for the not-found reflection surfaces. They
#: never contain the requested name/URI (nor a `_meta` echo of it).
_UNKNOWN_RESOURCE_MESSAGE = "The requested resource is not available."
_UNKNOWN_PROMPT_MESSAGE = "The requested prompt is not available."

# Layer 5 -- validation-log scrub (panelapp/autopvs1 pattern).
#
# Each marker is a substring of the ``record.msg`` of a FastMCP-core or MCP-SDK log
# line that reflects the caller-supplied name/URI -- either f-string-interpolated
# INTO ``record.msg`` (the SDK session records) or carried in ``record.args`` with
# a stable format string (the FastMCP records). Matching the substring covers both
# forms because the filter replaces ``record.msg`` AND clears ``record.args``.
_SCRUB_MARKERS: tuple[str, ...] = (
    "Handler called: call_tool",
    "Handler called: read_resource",
    "Handler called: get_prompt",
    "Invalid arguments for tool",
    "Error calling tool",
    "Error reading resource",
    "Tool cache miss for",
    "Failed to validate request",
    "Failed to validate notification",
    "Message that failed validation",
)

# The SOURCE loggers on which those records are CREATED (a filter runs only on the
# originating logger during ``Logger.handle`` -- ancestor filters are skipped
# during propagation). ``""`` is the root logger, where ``mcp.shared.session``
# emits its request/notification-validation failures via bare ``logging.warning``
# / ``logging.debug``. ``fastmcp`` / ``mcp`` are included so the filter also lands
# on their (possibly non-propagating Rich) handlers.
_SCRUB_LOGGERS: tuple[str, ...] = (
    "",
    "fastmcp",
    "fastmcp.server.server",
    "fastmcp.server.mixins.mcp_operations",
    "mcp",
    "mcp.server.lowlevel.server",
    "mcp.shared.session",
)

_SCRUBBED_MESSAGE = "MCP request rejected (details omitted)."


class _ValidationLogScrubFilter(logging.Filter):
    """Scrub log records that would echo a caller-supplied tool name / URI.

    Replaces the record payload with a FIXED constant (clearing ``args`` /
    ``exc_info`` / ``exc_text`` / ``stack_info``) so the caller-chosen name/URI --
    and any control/zero-width/bidi/NUL code points it carries -- can never reach a
    log or telemetry sink, at ANY level. Always returns ``True``: the now
    input-free record is still emitted for operational visibility.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.msg if isinstance(record.msg, str) else ""
        if any(marker in msg for marker in _SCRUB_MARKERS):
            record.msg = _SCRUBBED_MESSAGE
            record.args = ()
            record.exc_info = None
            record.exc_text = None
            record.stack_info = None
        return True


def install_validation_log_filter() -> None:
    """Idempotently attach the scrub filter to each source logger AND its handlers.

    A logger-level filter neutralizes records emitted directly on that logger; the
    handler-level attachment additionally scrubs records that reach a logger's own
    (non-propagating) handlers by propagation -- notably FastMCP's ``RichHandler``s
    on the ``fastmcp`` logger. Call after the FastMCP facade is built so those
    handlers already exist.
    """
    for name in _SCRUB_LOGGERS:
        target = logging.getLogger(name)
        if not any(isinstance(f, _ValidationLogScrubFilter) for f in target.filters):
            target.addFilter(_ValidationLogScrubFilter())
        for handler in target.handlers:
            if not any(isinstance(f, _ValidationLogScrubFilter) for f in handler.filters):
                handler.addFilter(_ValidationLogScrubFilter())


class _OutputValidationMiddleware(Middleware):
    """Fence the arg/output error paths AND the FastMCP-core not-found reflection.

    fastmcp 3.x exposes a class-based middleware API: ``on_call_tool`` wraps tool
    dispatch (argument validation + tool body) and ``on_read_resource`` wraps a
    resource read; exceptions raised by the chained call propagate here.
    """

    async def on_call_tool(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        tool_name = getattr(getattr(context, "message", None), "name", None)
        fctx = getattr(context, "fastmcp_context", None)
        # Layer 1 -- registry preflight. get_tool returns None for an unknown or
        # disabled tool; core would then raise/echo "Unknown tool: '<name>'"
        # (with the caller-supplied name + any code points/prose) BEFORE our
        # envelope. Return a FIXED, name-free not_found frame before dispatch.
        if fctx is not None and tool_name is not None:
            try:
                tool_obj = await fctx.fastmcp.get_tool(tool_name)
            except Exception:
                tool_obj = None
            if tool_obj is None:
                _logger.warning("mcp_unknown_tool")
                return self._unknown_tool_result()
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

    async def on_read_resource(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Layer 2 -- never echo a caller-supplied resource URI on a failed read.

        FastMCP's default resource-not-found / malformed-URI error embeds the
        requested URI (caller-controlled; may carry prose / forbidden code
        points). Replace any read failure with a FIXED, URI-free ``ResourceError``.
        """
        try:
            return await call_next(context)
        except Exception:
            _logger.warning("mcp_unknown_resource")
            raise ResourceError(_UNKNOWN_RESOURCE_MESSAGE) from None

    @staticmethod
    def _unknown_tool_result() -> ToolResult:
        """A ToolResult carrying the FIXED, name-free not_found envelope."""
        envelope = build_unknown_tool_envelope()
        return ToolResult(
            content=[mcp.types.TextContent(type="text", text=json.dumps(envelope))],
            structured_content=envelope,
            is_error=True,
        )


class ProtocolError(Exception):
    """A dispatch-level failure re-raised with a FIXED, input-free message."""


def _is_structured_envelope(call_result: mcp.types.CallToolResult) -> bool:
    """True if an isError result carries one of OUR JSON envelopes (has error_code).

    Distinguishes a structured gtex-link error (already input-free) from a RAW
    FastMCP dispatch error whose plain-text message echoes the caller-supplied
    tool name ("Unknown tool: '<name>'").
    """
    if not call_result.content:
        return False
    text = getattr(call_result.content[0], "text", None)
    if not isinstance(text, str):
        return False
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return False
    return isinstance(obj, dict) and "error_code" in obj


def _fixed_tool_not_found_result() -> mcp.types.ServerResult:
    """A fixed, input-free CallToolResult for an unknown/failed tool dispatch."""
    envelope = build_unknown_tool_envelope()
    return mcp.types.ServerResult(
        mcp.types.CallToolResult(
            content=[mcp.types.TextContent(type="text", text=json.dumps(envelope))],
            isError=True,
            structuredContent=envelope,
        )
    )


def install_protocol_error_handler(mcp_server: FastMCP) -> None:
    """Layer 3 -- wrap the raw tool/resource/prompt request handlers as a backstop.

    FastMCP core reflects the caller-supplied name/URI verbatim when it is unknown
    or malformed, which bypasses the structured envelope path. This OUTERMOST wrap
    replaces any non-structured ``isError`` tool result and catches dispatch
    exceptions (including the malformed-URI ``-32602`` raised before
    ``on_read_resource`` fires) with FIXED, input-free messages.

    Must be installed AFTER :func:`install_output_validation_error_handler` so it is
    the outermost wrapper on the request handlers.
    """
    handlers = mcp_server._mcp_server.request_handlers

    call_tool = handlers.get(mcp.types.CallToolRequest)
    if call_tool is not None:

        async def wrapped_call_tool(
            request: mcp.types.CallToolRequest,
            *,
            _orig: Any = call_tool,
        ) -> mcp.types.ServerResult:
            try:
                result = cast(mcp.types.ServerResult, await _orig(request))
            except Exception:
                # A registered tool never raises here (run_mcp_tool returns an
                # envelope); any exception is a dispatch-level failure whose
                # message would echo the caller name -- mask it.
                return _fixed_tool_not_found_result()
            # FastMCP returns an isError CallToolResult with a raw plain-text
            # message ("Unknown tool: '<name>'") for an unknown tool; replace any
            # isError result that is NOT one of our structured envelopes.
            root = getattr(result, "root", None)
            if (
                isinstance(root, mcp.types.CallToolResult)
                and root.isError
                and not _is_structured_envelope(root)
            ):
                return _fixed_tool_not_found_result()
            return result

        handlers[mcp.types.CallToolRequest] = wrapped_call_tool

    for request_type, message in (
        (mcp.types.ReadResourceRequest, _UNKNOWN_RESOURCE_MESSAGE),
        (mcp.types.GetPromptRequest, _UNKNOWN_PROMPT_MESSAGE),
    ):
        orig = handlers.get(request_type)
        if orig is None:
            continue

        async def wrapped(
            request: Any,
            *,
            _orig: Any = orig,
            _message: str = message,
        ) -> Any:
            try:
                return await _orig(request)
            except Exception:
                # Re-raise with a FIXED, input-free message so no requested
                # name/URI (or its code points) reaches the JSON-RPC error frame.
                raise ProtocolError(_message) from None

        handlers[request_type] = wrapped


def install_output_validation_error_handler(mcp: FastMCP) -> None:
    """Install the arg/output/not-found fence + Layer 5 validation-log scrub.

    Registers the class-based ``on_call_tool`` / ``on_read_resource`` middleware
    (arg-validation envelope + Layer 1 tool preflight + Layer 2 resource guard) and
    attaches the Layer 5 scrub filter to every framework source logger (and their
    handlers, incl. FastMCP's non-propagating Rich handlers) so no caller-supplied
    name/URI reaches a log sink. Both installs are idempotent (the loggers are
    process-global; each ``create_gtex_mcp`` must not stack filters).

    The Layer 3 protocol backstop is installed separately by
    :func:`install_protocol_error_handler` (called after this, as the outermost
    wrapper).
    """
    install_validation_log_filter()

    # Registered via add_middleware; the class-based hook API is on_call_tool.
    if not hasattr(mcp, "add_middleware"):
        _logger.warning("FastMCP instance lacks add_middleware; output validation skipped")
        return

    mcp.add_middleware(_OutputValidationMiddleware())
