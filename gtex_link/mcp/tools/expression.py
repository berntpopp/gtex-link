"""Expression-category MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from gtex_link.mcp.envelope import McpErrorContext, McpToolError, run_mcp_tool
from gtex_link.mcp.next_commands import after_median
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.schema_relax import relax_output_schema
from gtex_link.mcp.search_match import resolve_gene_ids
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
                "Results are grouped per gene with invariant fields hoisted. Use "
                "`sort` + `top_n` to answer 'where is this expressed most?' in one "
                "call; `response_mode='full'` adds ontologyId; `include_spread=true` "
                "adds per-tissue min/max/quartiles/IQR (one extra upstream call)."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            sort: Literal["desc", "asc", "none"] = "desc",
            top_n: int | None = None,
            response_mode: Literal["compact", "full"] = "compact",
            include_spread: bool = False,
            page: int = 0,
            page_size: int = 50,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                resolved = await resolve_gene_ids(service, gencode_id)
                if len(resolved) > MAX_MEDIAN_GENES:
                    raise McpToolError(
                        error_code="invalid_input",
                        message=(
                            f"Too many genes ({len(resolved)}); request at most "
                            f"{MAX_MEDIAN_GENES} genes per call so each gene's tissues "
                            "are returned intact (upstream 1000-row page cap)."
                        ),
                    )
                req: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": 0,
                    "itemsPerPage": min(max(60 * len(resolved), 100), 1000),
                }
                if tissue_site_detail_id is not None:
                    req["tissueSiteDetailId"] = tissue_site_detail_id
                result = await service.get_median_gene_expression(
                    MedianGeneExpressionRequest.model_validate(req)
                )
                counts = await sample_count_map(service, dataset_id)

                spread_by_key: dict[tuple[str, str], dict[str, Any] | None] = {}
                if include_spread and result.data:
                    spread_req: dict[str, object] = {
                        "gencodeId": resolved,
                        "datasetId": dataset_id,
                        "page": 0,
                        "itemsPerPage": 1000,
                    }
                    if tissue_site_detail_id is not None:
                        spread_req["tissueSiteDetailId"] = tissue_site_detail_id
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
                    page=page,
                    page_size=page_size,
                )
                payload = shaped.model_dump(by_alias=True)
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
                "optionally filtered by tissue and dataset. High volume -- limit "
                "`page_size` accordingly. Use for variance/distribution analyses "
                "where per-sample data is needed."
            ),
        )
        async def get_individual_expression_data(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                resolved = await resolve_gene_ids(service, gencode_id)
                payload: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = GeneExpressionRequest.model_validate(payload)
                result = await service.get_gene_expression(request)
                return result.model_dump(by_alias=True)

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
            page: int = 0,
            page_size: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                request = TopExpressedGenesRequest.model_validate(
                    {
                        "tissueSiteDetailId": tissue_site_detail_id,
                        "datasetId": dataset_id,
                        "filterMtGene": filter_mt_gene,
                        "page": page,
                        "itemsPerPage": page_size,
                    }
                )
                result = await service.get_top_expressed_genes(request)
                return result.model_dump(by_alias=True)

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
