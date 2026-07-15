"""Expression-category MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import Field

from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from gtex_link.mcp.envelope import McpErrorContext, McpToolError, run_mcp_tool
from gtex_link.mcp.metadata import ensure_known_dataset, ensure_valid_tissue
from gtex_link.mcp.next_commands import after_median, after_top
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.schema_relax import relax_output_schema
from gtex_link.mcp.search_match import gencode_version_for_dataset, resolve_gene_ids
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.mcp.shaping import group_median
from gtex_link.mcp.tissue_stats import compute_spread, sample_count_map
from gtex_link.models import (
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    TopExpressedGenesRequest,
)
from gtex_link.models.mcp_results import MedianExpressionResult
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

# 18 genes * 54 tissues = 972 rows, within the upstream 1000-row page cap, so a
# single fetch returns every requested gene's tissues without splitting any gene.
MAX_MEDIAN_GENES = 18


def _no_median_rows(dataset_id: str) -> str:
    """Loud, actionable message for an empty median result (never silent success)."""
    return (
        f"No median expression rows for the requested gene(s) in dataset "
        f"{dataset_id!r}. Gene IDs were resolved to this dataset's GENCODE release, "
        "so confirm the gene is measured in this dataset (some genes are annotation- "
        "or dataset-specific)."
    )


def _no_individual_rows(dataset_id: str, genes: list[str]) -> str:
    """Loud, actionable message for an empty individual-sample result."""
    joined = ", ".join(genes)
    return (
        f"No individual-sample expression rows for {joined} in dataset "
        f"{dataset_id!r}. Gene IDs were resolved to this dataset's GENCODE release, "
        "so confirm the gene is measured here and (if filtered) that the tissue has "
        "samples for it."
    )


def register_expression_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register expression-category tools on a FastMCP instance."""
    if is_tool_in_profile("get_median_expression_levels", profile):

        @mcp.tool(
            name="get_median_expression_levels",
            title="Get Median Expression Levels",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"expression"},
            output_schema=relax_output_schema(
                MedianExpressionResult.model_json_schema(by_alias=True)
            ),
            description=(
                "Get median GTEx Portal expression (TPM) per tissue for one or "
                "more genes (GENCODE IDs or symbols; symbols are auto-resolved). "
                "Results are grouped per gene with invariant fields hoisted. "
                "`tissue_site_detail_id` accepts a single tissue OR a list of "
                "tissues to compare a few tissues in one compact call; omit for "
                "all tissues. Use `sort` + `top_n` to answer 'where is this "
                "expressed most?' in one call; `response_mode='full'` adds "
                "ontologyId; `include_spread=true` adds per-tissue "
                "min/max/quartiles/IQR (one extra upstream call)."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | list[str] | None = None,
            dataset_id: str = "gtex_v8",
            sort: Literal["desc", "asc", "none"] = "desc",
            top_n: Annotated[int | None, Field(ge=1)] = None,
            response_mode: Literal["compact", "full"] = "compact",
            include_spread: bool = False,
            offset: int = 0,
            limit: int = 50,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                # Reject an unknown dataset BEFORE resolving gene ids: resolution is
                # itself an upstream call against the dataset's GENCODE release.
                ensure_known_dataset(dataset_id)
                service = get_gtex_service()
                resolved = await resolve_gene_ids(
                    service, gencode_id, gencode_version=gencode_version_for_dataset(dataset_id)
                )
                if len(resolved) > MAX_MEDIAN_GENES:
                    raise McpToolError(
                        error_code="invalid_input",
                        message=(
                            f"Too many genes ({len(resolved)}); request at most "
                            f"{MAX_MEDIAN_GENES} genes per call so each gene's tissues "
                            "are returned intact (upstream 1000-row page cap)."
                        ),
                    )
                # A single tissue is pushed down to the upstream filter; a list is
                # filtered client-side (the upstream endpoint takes one tissue), so
                # fetch all tissues and restrict in group_median.
                upstream_tissue: str | None = None
                tissues_filter: set[str] | None = None
                if isinstance(tissue_site_detail_id, list):
                    for tissue in tissue_site_detail_id:
                        ensure_valid_tissue(tissue)
                    tissues_filter = set(tissue_site_detail_id)
                elif tissue_site_detail_id is not None:
                    ensure_valid_tissue(tissue_site_detail_id)
                    upstream_tissue = tissue_site_detail_id
                req: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": 0,
                    "itemsPerPage": min(max(60 * len(resolved), 100), 1000),
                }
                if upstream_tissue is not None:
                    req["tissueSiteDetailId"] = upstream_tissue
                result = await service.get_median_gene_expression(
                    MedianGeneExpressionRequest.model_validate(req)
                )
                if not result.data:
                    raise McpToolError(error_code="not_found", message=_no_median_rows(dataset_id))
                counts = await sample_count_map(service, dataset_id)

                spread_by_key: dict[tuple[str, str], dict[str, Any] | None] = {}
                if include_spread and result.data:
                    spread_req: dict[str, object] = {
                        "gencodeId": resolved,
                        "datasetId": dataset_id,
                        "page": 0,
                        "itemsPerPage": 1000,
                    }
                    if upstream_tissue is not None:
                        spread_req["tissueSiteDetailId"] = upstream_tissue
                    expr = await service.get_gene_expression(
                        GeneExpressionRequest.model_validate(spread_req)
                    )
                    spread_by_key = {
                        (r.gencode_id, r.tissue_site_detail_id): compute_spread(r.data)
                        for r in expr.data
                    }

                shaped = group_median(
                    list(result.data),
                    counts=counts,
                    sort=sort,
                    top_n=top_n,
                    response_mode=response_mode,
                    spread_by_key=spread_by_key,
                    page=offset // limit if limit else 0,
                    page_size=limit,
                    tissues_filter=tissues_filter,
                )
                # exclude_none drops the always-null ontologyId/spread keys in
                # compact mode (honoring the documented "tissue/median/n only").
                payload = shaped.model_dump(by_alias=True, exclude_none=True)
                top_tissue = (
                    payload["genes"][0]["tissues"][0]["tissue"]
                    if payload["genes"] and payload["genes"][0]["tissues"]
                    else None
                )
                payload["_meta"] = {"next_commands": after_median(top_tissue)}
                return payload

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_median_expression_levels",
                    call,
                    context=McpErrorContext("get_median_expression_levels", dataset_id=dataset_id),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_median_expression_levels", success=success)

    if is_tool_in_profile("get_individual_expression_data", profile):

        @mcp.tool(
            name="get_individual_expression_data",
            title="Get Individual Expression Data",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"expression"},
            description=(
                "Get individual-sample GTEx Portal expression data (TPM) for one "
                "or more genes (GENCODE IDs or symbols; symbols are auto-resolved), "
                "optionally filtered by tissue and dataset. Returns one row per "
                "gene-tissue; each row's `data` is an unlabeled per-sample TPM "
                "vector (no sample/donor IDs, upstream order) with `n` = sample "
                "count. NOTE: `limit` paginates the gene-tissue ROWS, not "
                "samples -- filter by tissue to bound size. Use for "
                "variance/distribution analyses where per-sample data is needed."
            ),
        )
        async def get_individual_expression_data(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            offset: int = 0,
            limit: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                ensure_known_dataset(dataset_id)  # before any upstream gene resolution
                service = get_gtex_service()
                ensure_valid_tissue(tissue_site_detail_id)
                resolved = await resolve_gene_ids(
                    service, gencode_id, gencode_version=gencode_version_for_dataset(dataset_id)
                )
                payload: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": offset // limit if limit else 0,
                    "itemsPerPage": limit,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = GeneExpressionRequest.model_validate(payload)
                result = await service.get_gene_expression(request)
                if not result.data:
                    raise McpToolError(
                        error_code="not_found",
                        message=_no_individual_rows(dataset_id, resolved),
                    )
                dumped = result.model_dump(by_alias=True)
                # Surface the per-row sample count and tame float noise; the raw
                # vector carries no sample IDs, so `n` is the only labelled stat.
                for row in dumped.get("data", []):
                    values = row.get("data") or []
                    row["data"] = [round(v, 4) for v in values]
                    row["n"] = len(values)
                return dumped

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_individual_expression_data",
                    call,
                    context=McpErrorContext(
                        "get_individual_expression_data", dataset_id=dataset_id
                    ),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_individual_expression_data", success=success)

    if is_tool_in_profile("get_top_expressed_genes_by_tissue", profile):

        @mcp.tool(
            name="get_top_expressed_genes_by_tissue",
            title="Get Top Expressed Genes By Tissue",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"expression"},
            description=(
                "Get the top expressed genes for a given tissue from GTEx "
                "Portal. Use when answering 'what's expressed in this "
                "tissue?' rather than 'where is this gene expressed?'. "
                "Returns genes ranked by median expression."
            ),
        )
        async def get_top_expressed_genes_by_tissue(
            tissue_site_detail_id: str,
            dataset_id: str = "gtex_v8",
            filter_mt_gene: bool = True,
            offset: int = 0,
            limit: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                ensure_known_dataset(dataset_id)
                ensure_valid_tissue(tissue_site_detail_id)
                service = get_gtex_service()
                request = TopExpressedGenesRequest.model_validate(
                    {
                        "tissueSiteDetailId": tissue_site_detail_id,
                        "datasetId": dataset_id,
                        "filterMtGene": filter_mt_gene,
                        "page": offset // limit if limit else 0,
                        "itemsPerPage": limit,
                    }
                )
                result = await service.get_top_expressed_genes(request)
                dumped = result.model_dump(by_alias=True)
                rows = dumped.get("data", [])
                for row in rows:
                    if row.get("median") is not None:
                        row["median"] = round(row["median"], 4)
                if rows:
                    dumped["_meta"] = {"next_commands": after_top(rows[0]["gencodeId"])}
                return dumped

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_top_expressed_genes_by_tissue",
                    call,
                    context=McpErrorContext(
                        "get_top_expressed_genes_by_tissue", dataset_id=dataset_id
                    ),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_top_expressed_genes_by_tissue", success=success)
