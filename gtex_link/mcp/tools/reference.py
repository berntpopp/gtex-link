"""Reference-category MCP tools (gene search, gene info, transcript info)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool
from gtex_link.mcp.next_commands import after_gene_search
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, TranscriptRequest
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_reference_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register reference-category tools on a FastMCP instance."""
    if is_tool_in_profile("search_gtex_genes", profile):

        @mcp.tool(
            name="search_gtex_genes",
            title="Search GTEx Genes",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"reference", "search"},
            description=(
                "Search the GTEx Portal gene catalog by gene symbol or partial "
                "match. Returns a paginated list of genes with GENCODE IDs, "
                "symbols, chromosome, and basic metadata. Use this when the "
                "user provides a gene name or partial symbol and you need to "
                "disambiguate. Pair with `get_gene_information` for full detail."
            ),
        )
        async def search_gtex_genes(
            query: str,
            page: int = 0,
            page_size: int = 20,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=page,
                    page_size=page_size,
                )
                payload = result.model_dump(by_alias=True)
                gencode_ids = [g["gencodeId"] for g in payload["data"]]
                if gencode_ids:
                    payload["_meta"] = {"next_commands": after_gene_search(gencode_ids)}
                return payload

            success = False
            try:
                payload = await run_mcp_tool(
                    "search_gtex_genes", call, context=McpErrorContext("search_gtex_genes")
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="search_gtex_genes", success=success)

    if is_tool_in_profile("get_gene_information", profile):

        @mcp.tool(
            name="get_gene_information",
            title="Get Gene Information",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"reference"},
            description=(
                "Retrieve detailed gene information from GTEx Portal for one "
                "or more GENCODE IDs or gene symbols. Returns chromosome, "
                "coordinates, gene type, Entrez ID, and description. Use when "
                "you already know the gene identifier."
            ),
        )
        async def get_gene_information(
            gene_id: list[str],
            gencode_version: str | None = None,
            genome_build: str | None = None,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "geneId": gene_id,
                    "page": 0,
                    "itemsPerPage": len(gene_id),
                }
                if gencode_version is not None:
                    payload["gencodeVersion"] = gencode_version
                if genome_build is not None:
                    payload["genomeBuild"] = genome_build
                request = GeneRequest.model_validate(payload)
                result = await service.get_genes(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_gene_information", call, context=McpErrorContext("get_gene_information")
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_gene_information", success=success)

    if is_tool_in_profile("get_transcript_information", profile):

        @mcp.tool(
            name="get_transcript_information",
            title="Get Transcript Information",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"reference"},
            description=(
                "Retrieve transcript annotations for a single GENCODE ID from "
                "GTEx Portal. Returns transcript identifiers, coordinates, "
                "and gene linkage. Use for transcript-level analysis or when "
                "the user asks about isoforms."
            ),
        )
        async def get_transcript_information(
            gencode_id: str,
            gencode_version: str | None = None,
            genome_build: str | None = None,
            page: int = 0,
            page_size: int = 250,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "gencodeId": gencode_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if gencode_version is not None:
                    payload["gencodeVersion"] = gencode_version
                if genome_build is not None:
                    payload["genomeBuild"] = genome_build
                request = TranscriptRequest.model_validate(payload)
                result = await service.get_transcripts(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_transcript_information",
                    call,
                    context=McpErrorContext("get_transcript_information"),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_transcript_information", success=success)
