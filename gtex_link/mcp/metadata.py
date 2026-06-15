"""Capabilities discovery surface for GTEx-Link (parity with sibling -link servers)."""

from __future__ import annotations

import functools
import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from gtex_link.mcp.envelope import McpToolError
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION
from gtex_link.models.gtex import TissueSiteDetailId
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

_ALL_TOOLS = (
    "search",
    "fetch",
    "search_genes",
    "get_gene_information",
    "get_transcript_information",
    "get_median_expression_levels",
    "get_individual_expression_data",
    "get_top_expressed_genes_by_tissue",
    "get_server_capabilities",
)


def _server_version() -> str:
    try:
        return version("gtex-link")
    except PackageNotFoundError:
        return "0.0.0"


def valid_tissues() -> list[str]:
    """The advertised tissue vocabulary: real tissues only, no '' sentinel."""
    return [t.value for t in TissueSiteDetailId if t.value]


def ensure_valid_tissue(tissue: str | None) -> None:
    """Raise a short `invalid_input` McpToolError if *tissue* is unknown.

    Pre-validating here keeps the enormous pydantic enum dump (the full 54-tissue
    list, twice) out of the client-facing error. `None` means "all tissues" and
    passes. Shared by every tool that accepts a tissue filter.
    """
    if tissue is None:
        return
    allowed = valid_tissues()
    if tissue not in allowed:
        sample = ", ".join(allowed[:8])
        raise McpToolError(
            error_code="invalid_input",
            message=(
                f"Unknown tissue_site_detail_id {tissue!r}. "
                f"Valid values include: {sample}, ... ({len(allowed)} total; "
                "see get_server_capabilities.tissues)."
            ),
        )


@functools.cache
def _surface() -> dict[str, Any]:
    surface: dict[str, Any] = {
        "server": "gtex-link",
        "server_version": _server_version(),
        "mcp_protocol_version": "2025-11-25",
        "gtex_release": GTEX_DATA_RELEASE,
        "research_use_only": True,
        "datasets": ["gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"],
        "tissues": valid_tissues(),
        "tools": list(_ALL_TOOLS),
        "recommended_workflows": [
            "natural language -> search -> fetch",
            "gene symbol -> search_genes -> get_gene_information -> get_median_expression_levels",
            "tissue -> get_top_expressed_genes_by_tissue",
        ],
        "response_modes": {
            "compact": "default; per-tissue tissue/median/n only",
            "full": "adds ontologyId per tissue",
            "include_spread": "opt-in min/max/quartiles/IQR (one extra upstream call)",
        },
        "error_codes": [
            "not_found",
            "invalid_input",
            "validation_failed",
            "rate_limited",
            "upstream_unavailable",
            "internal_error",
        ],
        "parameter_conventions": {
            "gene_id": "symbols or GENCODE IDs; symbols auto-resolved",
            "tissue_site_detail_id": (
                "one of `tissues`, or a list of them (median tool only) for a "
                "multi-tissue comparison; omit for all tissues"
            ),
            "sort": "desc (default) | asc | none",
            "top_n": "limit tissues per gene for the peak-expression question",
            "offset": "zero-based row offset for pagination (fleet canon)",
            "limit": "page size for pagination (fleet canon)",
        },
        "token_cost_hints": {
            "search": "~1-3kB",
            "get_median_expression_levels": "compact ~1-4kB; full/include_spread larger",
            "get_individual_expression_data": (
                "high volume; one row per gene-tissue (limit paginates genes, "
                "not samples) -- filter by tissue to bound size"
            ),
            "get_server_capabilities": "<3kB",
        },
        "limitations": [
            "Rate-limited to 5 req/s (token bucket).",
            "numSamples is the per-tissue RNA-seq denominator (gene-independent).",
            "Spread requires per-sample arrays (opt-in); no precomputed quartile endpoint.",
            (
                "get_individual_expression_data returns unlabeled per-sample TPM "
                "vectors (no sample/donor IDs) in upstream order, one row per "
                "gene-tissue."
            ),
            (
                "Gene IDs resolve against gtex_v8 (GENCODE v26); other datasets use "
                "a different GENCODE version, so versioned IDs may not match."
            ),
            "Research use only; not for clinical decision support.",
        ],
        "concurrency": {"rate_limit_per_second": 5},
        "response_fields": {
            "headline": "one-line plain-English answer at the top of median results",
            "next_commands": "_meta.next_commands: ready-to-call {tool, arguments} next steps",
            "recommended_citation": "_meta.recommended_citation: paste verbatim",
        },
        "resources": {
            "gtex://capabilities": "this document",
            "gtex://usage": "compact usage notes",
            "gtex://reference": "error taxonomy + field glossary",
            "gtex://research-use": "research-use-only notice",
            "gtex://citations": "GTEx citation",
        },
        "citation": RECOMMENDED_CITATION,
    }
    digest = hashlib.sha256(
        json.dumps(surface, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    surface["capabilities_version"] = digest
    return surface


def capabilities_version() -> str:
    """16-char content hash of the capabilities surface for cache invalidation."""
    return str(_surface()["capabilities_version"])


def build_capabilities() -> dict[str, Any]:
    """Return the full capabilities document (cached)."""
    return dict(_surface())


def register_metadata_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register the get_server_capabilities discovery tool."""
    if not is_tool_in_profile("get_server_capabilities", profile):
        return

    @mcp.tool(
        name="get_server_capabilities",
        title="Get Server Capabilities",
        tags={"meta", "discovery"},
        description=(
            "Return supported tools, datasets, the tissue vocabulary, recommended "
            "workflows, response modes, error codes, and limits. Compare "
            "`capabilities_version` to skip re-fetching when unchanged."
        ),
    )
    async def get_server_capabilities() -> dict[str, Any]:
        record_mcp_tool_call(tool="get_server_capabilities", success=True)
        return build_capabilities()
