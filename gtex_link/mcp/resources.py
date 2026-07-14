"""Static string resources used in MCP tool descriptions and instructions."""

from __future__ import annotations

RESEARCH_USE_NOTICE = (
    "Research use only; not for clinical decision support, diagnosis, "
    "treatment, or patient management."
)

GTEX_SERVER_INSTRUCTIONS = (
    "GTEx-Link exposes GTEx Portal v8 expression data. "
    "For ChatGPT-compatible workflows use `search` (natural language ok) then "
    "`fetch`. For programmatic access: `search_genes` -> "
    "`get_gene_information` -> `get_median_expression_levels` or "
    "`get_top_expressed_genes_by_tissue`. Gene IDs accept symbols or GENCODE "
    "IDs; symbols are auto-resolved. Tool results are structured JSON with a "
    "`success` flag and `_meta`; errors carry an `error_code`. "
    f"{RESEARCH_USE_NOTICE}"
)

GTEX_PORTAL_URL = "https://gtexportal.org"

# Default GTEx data release surfaced in provenance _meta and capabilities.
GTEX_DATA_RELEASE = "gtex_v8"

RECOMMENDED_CITATION = (
    "GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects "
    "across human tissues. Science. 2020;369(6509):1318-1330. "
    "doi:10.1126/science.aaz1776"
)

GTEX_USAGE_NOTES = (
    "Resolve a gene with `search` (natural language) or `search_genes`, "
    "then `get_median_expression_levels` (use sort+top_n for the peak tissue) "
    "or `get_top_expressed_genes_by_tissue`. response_mode=compact is the "
    "default; pass response_mode=full or include_spread=true to widen. Follow "
    "`_meta.next_commands` to advance without guessing the next tool."
)

GTEX_REFERENCE_NOTES = (
    "Error codes: not_found, invalid_input, rate_limited, upstream_unavailable, "
    "output_limit_exceeded, internal_error. Errors carry retryable + "
    "recovery_action (retry_backoff | reformulate_input | switch_tool) and, for "
    "validation failures, field_errors. numSamples is the per-tissue RNA-seq "
    "sample denominator (gene-independent). Spread (min/max/quartiles/IQR) is "
    "opt-in via include_spread. Rate limit: 5 req/s (token bucket)."
)
