"""Capabilities discovery surface for GTEx-Link (parity with sibling -link servers)."""

from __future__ import annotations

import functools
import hashlib
import json
from typing import TYPE_CHECKING, Any

from gtex_link.mcp.envelope import McpToolError
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION
from gtex_link.models.gtex import DATASET_GENCODE_VERSION, TissueSiteDetailId
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
    from gtex_link import __version__

    return __version__


def valid_tissues() -> list[str]:
    """The advertised tissue vocabulary: real tissues only, no '' sentinel."""
    return [t.value for t in TissueSiteDetailId if t.value]


def ensure_valid_tissue(tissue: str | None) -> None:
    """Raise a short `invalid_input` McpToolError if *tissue* is unknown.

    Pre-validating here keeps the enormous pydantic enum dump (the full tissue
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


def ensure_known_dataset(dataset_id: str) -> None:
    """Raise `invalid_input` unless *dataset_id* is a dataset this server serves.

    Call this FIRST in every dataset-scoped tool, before any gene resolution or
    upstream request. An unknown dataset must never reach the wire: gene ids are
    resolved against the dataset's GENCODE release, so an unrecognized dataset
    would otherwise be queried against the wrong annotation and only be rejected
    afterwards by request validation.

    The caller's `dataset_id` is deliberately NOT echoed into the message -- it is
    untrusted text, and the valid values alone are the actionable part.
    """
    if dataset_id not in DATASET_GENCODE_VERSION:
        raise McpToolError(
            error_code="invalid_input",
            message=(
                f"Unknown dataset_id. Valid values: {', '.join(DATASET_GENCODE_VERSION)} "
                "(see get_server_capabilities.datasets)."
            ),
        )


@functools.cache
def _surface() -> dict[str, Any]:
    surface: dict[str, Any] = {
        "server": "gtex-link",
        "server_version": _server_version(),
        "mcp_protocol_version": "2025-11-25",
        # The server DEFAULT release (the `dataset_id` default), NOT a claim that this
        # is the only release served -- see `datasets`. Per-call provenance
        # (`_meta.gtex_release`) follows the `dataset_id` actually requested; see
        # `response_fields` below.
        "gtex_release": GTEX_DATA_RELEASE,
        "default_dataset_id": GTEX_DATA_RELEASE,
        "research_use_only": True,
        "datasets": ["gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"],
        "dataset_gencode_versions": dict(DATASET_GENCODE_VERSION),
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
        # The advertised taxonomy must equal what the envelope can actually emit,
        # and every code is a member of the Response-Envelope Standard v1 closed
        # enum (invalid_input, not_found, ambiguous_query, upstream_unavailable,
        # rate_limited, internal). ambiguous_query is in the standard but this
        # server never emits it, so it is not advertised. Pinned both ways by
        # tests/unit/mcp/test_error_code_contract.py.
        "error_codes": [
            "not_found",
            "invalid_input",
            "rate_limited",
            "upstream_unavailable",
            "internal",
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
                "Each dataset uses a different GENCODE release (see "
                "dataset_gencode_versions: gtex_v8->v26, gtex_v10->v39). Gene IDs are "
                "resolved to the requested dataset's release automatically; a gene "
                "absent from a release still returns no rows."
            ),
            "Research use only; not for clinical decision support.",
        ],
        "concurrency": {"rate_limit_per_second": 5},
        "response_fields": {
            "headline": "one-line plain-English answer at the top of median results",
            "next_commands": (
                "_meta.next_commands: ready-to-call {tool, arguments} next steps, on the "
                "tools with an obvious next step (search_genes, "
                "get_median_expression_levels, get_top_expressed_genes_by_tissue)"
            ),
            "recommended_citation": "_meta.recommended_citation: paste verbatim",
            "gtex_release": (
                "_meta.gtex_release: the release the response's data came from -- it "
                "FOLLOWS the requested dataset_id; tools that take no dataset_id "
                "report default_dataset_id. NOTE: `fetch` (flat Apps-SDK document: "
                "id/title/text/url/metadata) and `get_server_capabilities` (this "
                "document) carry no _meta at all"
            ),
            "gencode_version": (
                "_meta.gencode_version: the GENCODE release the gene IDs were resolved "
                "against (dataset-scoped calls only; see dataset_gencode_versions)"
            ),
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
        output_schema=None,
        description=(
            "Return supported tools, datasets, the tissue vocabulary, recommended "
            "workflows, response modes, error codes, and limits. Compare "
            "`capabilities_version` to skip re-fetching when unchanged."
        ),
    )
    async def get_server_capabilities() -> dict[str, Any]:
        record_mcp_tool_call(tool="get_server_capabilities", success=True)
        return build_capabilities()
