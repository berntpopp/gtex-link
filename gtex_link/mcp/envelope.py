"""Shared MCP envelope boundary for GTEx-Link tools.

Tools return a Python dict; `run_mcp_tool` injects `success`/`_meta` on the
happy path and converts any exception into a structured error envelope dict
(returned, never raised) so the LLM sees a structured failure instead of an
opaque masked message. Patterned after ../gnomad-link/.../mcp/errors.py, kept
minimal here (PR1); PR2 adds retryable/recovery_action/field_errors and PR3
adds _meta.next_commands.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION

logger = logging.getLogger(__name__)

_BASE_META: dict[str, Any] = {
    "unsafe_for_clinical_use": True,
    "gtex_release": GTEX_DATA_RELEASE,
    "recommended_citation": RECOMMENDED_CITATION,
}


@dataclass
class McpErrorContext:
    """Per-call context so envelopes can name the failing tool."""

    tool_name: str
    dataset_id: str | None = None


class McpToolError(Exception):
    """Raised inside a tool body to emit a specific error code/message."""

    def __init__(self, *, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _provenance_meta(context: McpErrorContext | None = None) -> dict[str, Any]:
    meta = dict(_BASE_META)
    if context is not None and context.dataset_id:
        meta["dataset_id"] = context.dataset_id
    return meta


def _safe_message(exc: BaseException) -> str:
    return (str(exc) or exc.__class__.__name__)[:240]


def _classify(exc: BaseException) -> tuple[str, str, bool]:
    """Return (error_code, client_safe_message, retryable)."""
    if isinstance(exc, McpToolError):
        return (
            exc.error_code,
            exc.message,
            exc.error_code in {"rate_limited", "upstream_unavailable"},
        )
    if isinstance(exc, RateLimitError):
        return "rate_limited", "GTEx Portal rate limit exceeded. Try again shortly.", True
    if isinstance(exc, ServiceUnavailableError):
        return (
            "upstream_unavailable",
            "GTEx Portal is temporarily unavailable. Try again later.",
            True,
        )
    if isinstance(exc, PydanticValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"]) or "input"
        return "invalid_input", f"Invalid input -- `{loc}`: {first['msg']}", False
    if isinstance(exc, ValidationError):
        field = f"`{exc.field}`: " if exc.field else ""
        return "invalid_input", f"Invalid input -- {field}{exc.message}", False
    if isinstance(exc, GTExAPIError):
        return (
            "upstream_unavailable",
            "GTEx Portal returned an error. Verify the request inputs.",
            True,
        )
    return "internal_error", "An internal error occurred. The request was not completed.", False


def _recovery_action(error_code: str, retryable: bool) -> str:
    if retryable:
        return "retry_backoff"
    if error_code in {"invalid_input", "validation_failed"}:
        return "reformulate_input"
    return "switch_tool"


def _field_errors(exc: BaseException) -> list[dict[str, str]] | None:
    if not isinstance(exc, PydanticValidationError):
        return None
    return [
        {"field": ".".join(str(p) for p in e["loc"]) or "input", "reason": e["msg"]}
        for e in exc.errors()
    ]


def _error_envelope(exc: BaseException, context: McpErrorContext) -> dict[str, Any]:
    error_code, message, retryable = _classify(exc)
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "recovery_action": _recovery_action(error_code, retryable),
        "_meta": {"tool": context.tool_name, **_provenance_meta(context)},
    }
    field_errors = _field_errors(exc)
    if field_errors is not None:
        envelope["field_errors"] = field_errors
    return envelope


async def run_mcp_tool(
    tool_name: str,
    call: Callable[[], Awaitable[dict[str, Any]]],
    *,
    context: McpErrorContext | None = None,
) -> dict[str, Any]:
    """Execute a tool body, returning the result dict or a structured error dict."""
    ctx = context or McpErrorContext(tool_name=tool_name)
    try:
        result = await call()
        if isinstance(result, dict):
            result.setdefault("success", True)
            existing_meta: dict[str, Any] = result.get("_meta") or {}
            result["_meta"] = {**existing_meta, **_provenance_meta(ctx)}
        return result
    except Exception as exc:  # broad catch is the error-boundary contract
        envelope = _error_envelope(exc, ctx)
        logger.warning(
            "mcp_tool_error tool=%s code=%s exc=%s",
            tool_name,
            envelope["error_code"],
            exc.__class__.__name__,
        )
        return envelope
