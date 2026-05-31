"""Expression-category MCP tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.errors import map_to_mcp_error_message
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import (
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    TopExpressedGenesRequest,
)
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_expression_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register expression-category tools on a FastMCP instance."""
    if is_tool_in_profile("get_median_expression_levels", profile):

        @mcp.tool(
            name="get_median_expression_levels",
            description=(
                "Get median GTEx Portal expression (TPM) per tissue for one or "
                "more GENCODE IDs. Returns per-tissue medians for dataset "
                "`gtex_v8` by default. Use this when comparing expression of "
                "a known gene across tissues; pair with "
                "`get_top_expressed_genes_by_tissue` for the reverse question."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "gencodeId": gencode_id,
                    "datasetId": dataset_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = MedianGeneExpressionRequest.model_validate(payload)
                result = await service.get_median_gene_expression(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="get_median_expression_levels", success=success)

    if is_tool_in_profile("get_individual_expression_data", profile):

        @mcp.tool(
            name="get_individual_expression_data",
            description=(
                "Get individual-sample GTEx Portal expression data (TPM) for "
                "one or more GENCODE IDs, optionally filtered by tissue and "
                "dataset. High volume -- limit `page_size` accordingly. Use "
                "for variance/distribution analyses where per-sample data is "
                "needed."
            ),
        )
        async def get_individual_expression_data(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "gencodeId": gencode_id,
                    "datasetId": dataset_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = GeneExpressionRequest.model_validate(payload)
                result = await service.get_gene_expression(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="get_individual_expression_data", success=success)

    if is_tool_in_profile("get_top_expressed_genes_by_tissue", profile):

        @mcp.tool(
            name="get_top_expressed_genes_by_tissue",
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
        ) -> str:
            success = False
            try:
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
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="get_top_expressed_genes_by_tissue", success=success)
