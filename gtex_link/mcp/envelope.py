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
    UpstreamPolicyError,
    ValidationError,
)
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION
from gtex_link.mcp.untrusted_content import UntrustedTextLimitError, sanitize_message
from gtex_link.models.gtex import DATASET_GENCODE_VERSION

logger = logging.getLogger(__name__)

_BASE_META: dict[str, Any] = {
    "unsafe_for_clinical_use": True,
    # The server DEFAULT release; a dataset-scoped call overrides it below with the
    # release actually queried.
    "gtex_release": GTEX_DATA_RELEASE,
    "recommended_citation": RECOMMENDED_CITATION,
}

# Allowlist: only a dataset_id that IS a known dataset may drive provenance, and the
# values emitted are THIS MODULE's literals (re-materialized from the mapping), never
# the caller's string. `gtex_release` therefore can never become an echo of arbitrary
# caller text -- see `_provenance_meta`.
_DATASET_PROVENANCE: dict[str, tuple[str, str]] = {
    dataset: (dataset, gencode) for dataset, gencode in DATASET_GENCODE_VERSION.items()
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
    """Provenance `_meta`: name the release the returned data ACTUALLY came from.

    The expression tools span three datasets annotated against different GENCODE
    releases (gtex_v8/gtex_snrnaseq_pilot -> v26, gtex_v10 -> v39), so a fixed
    `gtex_release` stamp would lie about a `dataset_id="gtex_v10"` call and
    re-introduce the very release/GENCODE-mismatch hazard this server removes.
    A dataset-scoped call therefore reports its own release plus the GENCODE
    version its gene IDs were resolved against; tools that take no `dataset_id`
    keep reporting the server default.

    SECURITY: `dataset_id` is caller-supplied and this runs on the ERROR path too
    (an unknown dataset_id is rejected with `invalid_input`, and that error envelope
    also carries `_meta`). `_meta.dataset_id` echoes the SANITIZED caller value, but
    the RELEASE fields never echo anything: only a KNOWN dataset -- a key of
    `DATASET_GENCODE_VERSION` -- may derive them, and the strings emitted come from
    that mapping, not from the caller. An unknown dataset_id keeps the server
    default and gets no `gencode_version`.
    """
    meta = dict(_BASE_META)
    if context is not None and context.dataset_id:
        # dataset_id is a caller-supplied argument copied verbatim into the
        # caller-visible _meta; strip forbidden control/zero-width/bidi/NUL code
        # points so it cannot smuggle them through the provenance frame.
        meta["dataset_id"] = sanitize_message(context.dataset_id)
        # Match on the RAW value, never the sanitized one: a string that only becomes
        # a known dataset AFTER sanitation (e.g. "gtex_v10" + a zero-width joiner) is
        # one the request layer REJECTS, so it must not drive provenance. Consequence,
        # by design: on an error envelope the sanitized `dataset_id` can read
        # "gtex_v10" while `gtex_release` stays at the default. That disagreement is
        # safe -- an error envelope carries no rows, so no data is mislabelled --
        # whereas deriving a release from a value the validator rejected would not be.
        known = _DATASET_PROVENANCE.get(context.dataset_id)
        if known is not None:
            meta["gtex_release"], meta["gencode_version"] = known
    return meta


def _safe_message(exc: BaseException) -> str:
    # Strip forbidden control/zero-width/bidi/NUL code points (and length-cap)
    # from any exception text before it can reach a caller-visible surface.
    return sanitize_message(str(exc) or exc.__class__.__name__)


def _classify(exc: BaseException) -> tuple[str, str, bool]:
    """Return (error_code, client_safe_message, retryable)."""
    if isinstance(exc, McpToolError):
        return (
            exc.error_code,
            exc.message,
            exc.error_code in {"rate_limited", "upstream_unavailable"},
        )
    # Response-Envelope v1.1: a fenced untrusted-text response exceeded a size
    # ceiling. The caller must narrow the request, so this maps onto the closed
    # enum's `invalid_input` (recovery = reformulate_input), not a transient code.
    # Checked before the generic `ValidationError` branch (UntrustedTextLimitError
    # subclasses ValueError, not gtex_link's ValidationError, but keep it first).
    if isinstance(exc, UntrustedTextLimitError):
        return (
            "invalid_input",
            "The response exceeded the untrusted-content size limit. Narrow the "
            "request (fewer genes or a more specific query) and retry.",
            False,
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
    # A redirect/size POLICY violation (F-17) is deterministic, not transient:
    # classify NON-RETRYABLE with a fixed, host-free message. Checked BEFORE the
    # generic GTExAPIError branch (which UpstreamPolicyError subclasses) so it
    # never falls through to the retryable `upstream_unavailable` mapping.
    if isinstance(exc, UpstreamPolicyError):
        return (
            "internal",
            "The request was blocked by an outbound URL/size policy and was not completed.",
            False,
        )
    if isinstance(exc, GTExAPIError):
        return (
            "upstream_unavailable",
            "GTEx Portal returned an error. Verify the request inputs.",
            True,
        )
    return "internal", "An internal error occurred. The request was not completed.", False


def _recovery_action(error_code: str, retryable: bool) -> str:
    if retryable:
        return "retry_backoff"
    if error_code in {"invalid_input", "not_found", "ambiguous_query"}:
        return "reformulate_input"
    return "switch_tool"


def _field_errors(exc: BaseException) -> list[dict[str, str]] | None:
    if not isinstance(exc, PydanticValidationError):
        return None
    return [
        {
            "field": ".".join(str(p) for p in e["loc"]) or "input",
            # pydantic echoes the offending input value into the reason, so a
            # caller-supplied string can carry forbidden code points here too.
            "reason": sanitize_message(e["msg"]),
        }
        for e in exc.errors()
    ]


def _error_envelope(exc: BaseException, context: McpErrorContext) -> dict[str, Any]:
    error_code, message, retryable = _classify(exc)
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        # Defense in depth: no forbidden control/zero-width/bidi/NUL code points
        # reach the caller, whatever error path (classified message, McpToolError,
        # or a caller-influenced identifier interpolated into a message) produced it.
        "message": sanitize_message(message),
        "retryable": retryable,
        "recovery_action": _recovery_action(error_code, retryable),
        "_meta": {"tool": context.tool_name, **_provenance_meta(context)},
    }
    field_errors = _field_errors(exc)
    if field_errors is not None:
        envelope["field_errors"] = field_errors
    return envelope


def build_unknown_tool_envelope() -> dict[str, Any]:
    """Fixed, name-free error frame for an unknown / unavailable tool.

    FastMCP core reflects the caller-supplied tool NAME verbatim -- it raises
    ``NotFoundError("Unknown tool: '<name>'")`` on the direct dispatch path and
    returns that string in an ``isError`` ``TextContent`` via the client transport
    -- BEFORE ``run_mcp_tool``'s envelope can run. Return the standard envelope
    shape with a FIXED ``not_found`` message and NO echoed name, so the requested
    name (and any control/zero-width/bidi/NUL code points or injection prose it
    carries) can never reach the caller. The requested name is deliberately NOT
    echoed into ``_meta`` (no ``tool`` key), matching the fleet not-found guard.
    """
    return {
        "success": False,
        "error_code": "not_found",
        "message": (
            "The requested tool is not available. Call get_server_capabilities "
            "for the supported tools."
        ),
        "retryable": False,
        "recovery_action": "switch_tool",
        "_meta": {**_provenance_meta()},
    }


def build_arg_error_envelope(
    tool_name: str | None,
    *,
    valid_params: list[str] | None = None,
    unknown_args: list[str] | None = None,
) -> dict[str, Any]:
    """Fixed, actionable error frame for an argument-validation failure.

    FastMCP validates tool arguments during dispatch, BEFORE ``run_mcp_tool``
    runs, and would otherwise surface the raw pydantic message (which echoes the
    caller's input VALUE) to the model. This returns the standard envelope with a
    FIXED ``invalid_input`` message that NEVER echoes an argument value, but --
    unlike the old body-free frame -- it DOES name the tool's own parameters so
    the model can self-correct (MCP 2025-11-25 SEP-1303; issue #76 D4/#4):

    * ``valid_params`` are the tool's declared parameter names (server-defined,
      always safe) -- surfaced in the prose and in an ``allowed_values`` field.
    * ``unknown_args`` are the caller-supplied argument KEYS the tool does not
      accept, already sanitized by the caller (control/zero-width/bidi/NUL code
      points stripped); named so a no-parameter tool's error is still actionable.
    """
    ctx = McpErrorContext(tool_name=tool_name or "unknown")
    unknown_args = unknown_args or []
    parts = ["Invalid arguments for this tool."]
    if unknown_args:
        parts.append(f"Unexpected argument(s): {', '.join(unknown_args)}.")
    if valid_params is not None:
        if valid_params:
            parts.append(f"This tool's parameters are: {', '.join(valid_params)}.")
        elif not unknown_args:
            parts.append("This tool accepts no arguments.")
    parts.append("Check the parameter types and any documented limits, then retry.")
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": "invalid_input",
        "message": sanitize_message(" ".join(parts)),
        "retryable": False,
        "recovery_action": _recovery_action("invalid_input", retryable=False),
        "_meta": {"tool": ctx.tool_name, **_provenance_meta(ctx)},
    }
    if valid_params:
        envelope["allowed_values"] = list(valid_params)
    if unknown_args:
        envelope["field_errors"] = [
            {"field": name, "reason": "unexpected argument"} for name in unknown_args
        ]
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
