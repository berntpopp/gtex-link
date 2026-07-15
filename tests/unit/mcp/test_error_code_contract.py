"""The advertised error taxonomy must equal the one the envelope can emit.

GeneFoundry README Standard v1: a documented fact that no machine checks will
rot. This one had already rotted in both directions before the guard existed --
`output_limit_exceeded` was reachable but unadvertised (so a client wrote no
branch for a recoverable failure), and `validation_failed` was advertised but
never produced by `_classify`.

The emittable set is *derived*, never hand-listed: `_classify` is exercised with
a real instance of every exception it dispatches on, the two fixed envelope
builders are called, and the package source is scanned for `McpToolError`
codes raised inside tool bodies. Add a new code anywhere and this fails until
`get_server_capabilities` advertises it.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    UpstreamPolicyError,
    ValidationError,
)
from gtex_link.mcp.envelope import (
    _classify,
    build_arg_error_envelope,
    build_unknown_tool_envelope,
)
from gtex_link.mcp.metadata import build_capabilities
from gtex_link.mcp.resources import GTEX_REFERENCE_NOTES
from gtex_link.mcp.untrusted_content import UntrustedTextLimitError

PACKAGE = Path(__file__).resolve().parents[3] / "gtex_link"
_RAISED_CODE_RE = re.compile(r'error_code="([a-z_]+)"')


class _Model(BaseModel):
    value: int


def _pydantic_error() -> PydanticValidationError:
    with pytest.raises(PydanticValidationError) as exc_info:
        _Model(value="not-an-int")  # type: ignore[arg-type]
    return exc_info.value


def _classified_codes() -> set[str]:
    """Every code `_classify` can return, by dispatching a real exception at it."""
    exceptions: list[BaseException] = [
        RateLimitError("rate limited"),
        ServiceUnavailableError("unavailable"),
        UpstreamPolicyError("blocked"),
        GTExAPIError("upstream boom"),
        ValidationError("bad", field="gene_id"),
        UntrustedTextLimitError("too big"),
        _pydantic_error(),
        RuntimeError("unclassified"),  # the internal fallback
    ]
    return {_classify(exc)[0] for exc in exceptions}


def _tool_raised_codes() -> set[str]:
    """`McpToolError(error_code=...)` literals raised anywhere in the package."""
    codes: set[str] = set()
    for path in PACKAGE.rglob("*.py"):
        codes.update(_RAISED_CODE_RE.findall(path.read_text(encoding="utf-8")))
    return codes


def emittable_codes() -> set[str]:
    return (
        _classified_codes()
        | _tool_raised_codes()
        | {build_unknown_tool_envelope()["error_code"]}
        | {build_arg_error_envelope("get_gene_information")["error_code"]}
    )


def test_capabilities_advertises_exactly_the_emittable_error_codes() -> None:
    advertised = set(build_capabilities()["error_codes"])
    emittable = emittable_codes()

    unadvertised = emittable - advertised
    assert not unadvertised, (
        f"error codes the server can emit but does not advertise: {sorted(unadvertised)}. "
        "A client reading get_server_capabilities writes no branch for these."
    )
    phantom = advertised - emittable
    assert not phantom, (
        f"error codes advertised but never emitted: {sorted(phantom)}. "
        "Advertising a dead code is a false claim about the contract."
    )


def test_every_advertised_code_is_in_the_fleet_closed_enum() -> None:
    """Response-Envelope Standard v1: error_code is a closed enum, harmonized fleet-wide."""
    closed_enum = {
        "invalid_input",
        "not_found",
        "ambiguous_query",
        "upstream_unavailable",
        "rate_limited",
        "internal",
    }
    advertised = set(build_capabilities()["error_codes"])
    outside = advertised - closed_enum
    assert not outside, f"codes outside the fleet closed enum: {sorted(outside)}"
    # And the emittable set must also stay inside the closed enum.
    assert not (emittable_codes() - closed_enum)


def test_reference_resource_lists_the_same_codes() -> None:
    """`gtex://reference` is a client-facing copy of the taxonomy; keep it in step."""
    for code in build_capabilities()["error_codes"]:
        assert code in GTEX_REFERENCE_NOTES, f"{code} missing from gtex://reference"
