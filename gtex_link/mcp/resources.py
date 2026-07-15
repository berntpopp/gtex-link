"""Static string resources used in MCP tool descriptions and instructions."""

from __future__ import annotations

RESEARCH_USE_NOTICE = (
    "Research use only; not for clinical decision support, diagnosis, "
    "treatment, or patient management."
)

# The server's own self-description: the first thing every connecting client reads.
# Keep it TRUE -- it must name the real dataset surface (three datasets, not just v8)
# and must not promise a `_meta` frame that `fetch` does not have.
GTEX_SERVER_INSTRUCTIONS = (
    "GTEx-Link exposes GTEx Portal expression data across three datasets: "
    "`gtex_v8` (the default), `gtex_v10`, and `gtex_snrnaseq_pilot`. The "
    "expression tools take a `dataset_id`; each dataset is annotated against its "
    "own GENCODE release, and gene IDs are resolved to the one you ask for. "
    "For ChatGPT-compatible workflows use `search` (natural language ok) then "
    "`fetch`. For programmatic access: `search_genes` -> "
    "`get_gene_information` -> `get_median_expression_levels` or "
    "`get_top_expressed_genes_by_tissue`. Gene IDs accept symbols or GENCODE "
    "IDs; symbols are auto-resolved. Tool results are structured JSON with a "
    "`success` flag and a `_meta` frame whose `gtex_release` names the release "
    "actually queried; errors carry an `error_code`. The exceptions are `fetch` "
    "(flat search-document shape: id/title/text/url/metadata) and "
    "`get_server_capabilities`, which carry no `_meta`. "
    f"{RESEARCH_USE_NOTICE}"
)

GTEX_PORTAL_URL = "https://gtexportal.org"

# The server's DEFAULT GTEx data release: the `dataset_id` default on every tool that
# takes one, and the `gtex_release` reported in capabilities and in provenance _meta
# for tools that take no `dataset_id`. A dataset-scoped call reports the release it
# actually queried instead -- see `envelope._provenance_meta`.
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
    "`_meta.next_commands` (emitted by search_genes, get_median_expression_levels "
    "and get_top_expressed_genes_by_tissue) to advance without guessing the next tool."
)

GTEX_REFERENCE_NOTES = (
    "Error codes: not_found, invalid_input, rate_limited, upstream_unavailable, "
    "internal. Errors carry retryable + "
    "recovery_action (retry_backoff | reformulate_input | switch_tool) and, for "
    "validation failures, field_errors. numSamples is the per-tissue RNA-seq "
    "sample denominator (gene-independent). Spread (min/max/quartiles/IQR) is "
    "opt-in via include_spread. Rate limit: 5 req/s (token bucket)."
)
