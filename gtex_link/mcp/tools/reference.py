"""Reference-category MCP tools (gene search, gene info, transcript info)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from pydantic import Field

from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from gtex_link.mcp.envelope import McpErrorContext, McpToolError, run_mcp_tool
from gtex_link.mcp.next_commands import after_gene_search
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.mcp.shaping import (
    SEARCH_GENES_LIMIT_MAX,
    SEARCH_GENES_MAX_OBJECTS,
    fence_gene_response,
)
from gtex_link.mcp.untrusted_content import DEFAULT_MAX_OBJECTS
from gtex_link.models import GeneRequest, TranscriptRequest
from gtex_link.models.gtex import GencodeVersionLiteral, GenomeBuildLiteral
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

# `GeneRequest.gene_id` caps `get_gene_information` at max_length=50
# (models/requests.py) -- comfortably inside the module default; named here
# only so the ceiling used by each tool is explicit at the call site.
_GET_GENE_INFORMATION_MAX_OBJECTS = DEFAULT_MAX_OBJECTS


def register_reference_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register reference-category tools on a FastMCP instance."""
    if is_tool_in_profile("search_genes", profile):

        @mcp.tool(
            name="search_genes",
            title="Search GTEx Genes",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"reference", "search"},
            output_schema=None,
            description=(
                "Search the GTEx Portal gene catalog by gene symbol or partial "
                "match. Returns a paginated list of genes with GENCODE IDs, "
                "symbols, chromosome, and basic metadata. Use this when the "
                "user provides a gene name or partial symbol and you need to "
                "disambiguate. Pair with `get_gene_information` for full detail."
            ),
        )
        async def search_genes(
            query: Annotated[
                str,
                Field(
                    description=(
                        "Gene symbol or partial symbol to match against the GTEx "
                        "catalog (e.g. 'BRCA' matches BRCA1, BRCA2)."
                    ),
                    examples=["BRCA1", "TP53"],
                ),
            ],
            offset: Annotated[
                int, Field(ge=0, description="Zero-based row offset for pagination (fleet canon).")
            ] = 0,
            limit: Annotated[
                int,
                Field(
                    ge=1,
                    le=SEARCH_GENES_LIMIT_MAX,
                    description="Maximum genes to return per page (1-1000).",
                ),
            ] = 20,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=offset // limit if limit else 0,
                    page_size=limit,
                )
                gencode_ids = [gene.gencode_id for gene in result.data]
                payload = fence_gene_response(result, max_objects=SEARCH_GENES_MAX_OBJECTS)
                if gencode_ids:
                    payload["_meta"] = {"next_commands": after_gene_search(gencode_ids)}
                return payload

            success = False
            try:
                payload = await run_mcp_tool(
                    "search_genes", call, context=McpErrorContext("search_genes")
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="search_genes", success=success)

    if is_tool_in_profile("get_gene_information", profile):

        @mcp.tool(
            name="get_gene_information",
            title="Get Gene Information",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"reference"},
            output_schema=None,
            description=(
                "Retrieve detailed gene information from GTEx Portal for one "
                "or more GENCODE IDs or gene symbols. Returns chromosome, "
                "coordinates, gene type, Entrez ID, and description. Use when "
                "you already know the gene identifier."
            ),
        )
        async def get_gene_information(
            gene_id: Annotated[
                list[str],
                Field(
                    description=(
                        "One or more gene symbols or GENCODE IDs; symbols are "
                        "auto-resolved (e.g. UMOD or ENSG00000169344.15)."
                    ),
                    examples=[["BRCA1", "TP53"]],
                ),
            ],
            gencode_version: Annotated[
                GencodeVersionLiteral | None,
                Field(
                    description=(
                        "GENCODE annotation release to resolve against; omit for "
                        "the server default (v26)."
                    )
                ),
            ] = None,
            genome_build: Annotated[
                GenomeBuildLiteral | None,
                Field(description="Genome assembly build; omit for the server default."),
            ] = None,
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
                if not result.data:
                    raise McpToolError(
                        error_code="not_found",
                        message=(
                            f"No gene found for: {', '.join(gene_id)}. Provide a valid "
                            "gene symbol (e.g. UMOD) or GENCODE ID (e.g. "
                            "ENSG00000169344.15)."
                        ),
                    )
                return fence_gene_response(result, max_objects=_GET_GENE_INFORMATION_MAX_OBJECTS)

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
            output_schema=None,
            description=(
                "Retrieve transcript annotations for a single GENCODE ID from "
                "GTEx Portal. Returns transcript identifiers, coordinates, "
                "and gene linkage. Use for transcript-level analysis or when "
                "the user asks about isoforms."
            ),
        )
        async def get_transcript_information(
            gencode_id: Annotated[
                str,
                Field(
                    description=(
                        "A single VERSIONED GENCODE ID (e.g. ENSG00000169344.15). "
                        "This tool does NOT auto-resolve gene symbols -- resolve a "
                        "symbol via get_gene_information or search_genes first."
                    ),
                    examples=["ENSG00000169344.15"],
                ),
            ],
            gencode_version: Annotated[
                GencodeVersionLiteral | None,
                Field(description="GENCODE annotation release; omit for the server default."),
            ] = None,
            genome_build: Annotated[
                GenomeBuildLiteral | None,
                Field(description="Genome assembly build; omit for the server default."),
            ] = None,
            offset: Annotated[
                int, Field(ge=0, description="Zero-based row offset for pagination.")
            ] = 0,
            limit: Annotated[
                int, Field(ge=1, le=1000, description="Maximum transcript rows per page.")
            ] = 250,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "gencodeId": gencode_id,
                    "page": offset // limit if limit else 0,
                    "itemsPerPage": limit,
                }
                if gencode_version is not None:
                    payload["gencodeVersion"] = gencode_version
                if genome_build is not None:
                    payload["genomeBuild"] = genome_build
                request = TranscriptRequest.model_validate(payload)
                result = await service.get_transcripts(request)
                if not result.data:
                    raise McpToolError(
                        error_code="not_found",
                        message=(
                            f"No transcripts found for {gencode_id}. Provide a versioned "
                            "GENCODE ID (e.g. ENSG00000169344.15); resolve a symbol via "
                            "get_gene_information or search_genes first."
                        ),
                    )
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
