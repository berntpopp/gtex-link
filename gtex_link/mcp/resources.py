"""Static string resources used in MCP tool descriptions and instructions."""

from __future__ import annotations

RESEARCH_USE_NOTICE = (
    "Research use only; not for clinical decision support, diagnosis, "
    "treatment, or patient management."
)

GTEX_SERVER_INSTRUCTIONS = (
    "GTEx-Link exposes GTEx Portal v8 expression data. "
    "For ChatGPT-compatible workflows use `search` (natural language ok) then "
    "`fetch`. For programmatic access: `search_gtex_genes` -> "
    "`get_gene_information` -> `get_median_expression_levels` or "
    "`get_top_expressed_genes_by_tissue`. Gene IDs accept symbols or GENCODE "
    "IDs; symbols are auto-resolved. Tool results are structured JSON with a "
    "`success` flag and `_meta`; errors carry an `error_code`. "
    f"{RESEARCH_USE_NOTICE}"
)

GTEX_PORTAL_URL = "https://gtexportal.org"

# Default GTEx data release surfaced in provenance _meta and capabilities.
GTEX_DATA_RELEASE = "gtex_v8"
