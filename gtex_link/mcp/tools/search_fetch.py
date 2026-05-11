"""ChatGPT-compatible search and fetch MCP tools.

These mirror the OpenAI Apps SDK shape -- `search(query) -> {results: [...]}`
and `fetch(id) -> {id, title, text, url, metadata}` -- so a single MCP server
can be consumed by both ChatGPT and Claude Desktop.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.errors import map_to_mcp_error_message
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_PORTAL_URL
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, MedianGeneExpressionRequest
from gtex_link.models.gtex import DatasetId, TissueSiteDetailId
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_search_fetch_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register the ChatGPT-compatible `search` and `fetch` tools."""
    if is_tool_in_profile("search", profile):

        @mcp.tool(
            name="search",
            description=(
                "Search the GTEx Portal genetic expression database for "
                "genes, transcripts, and expression data. Returns a list of "
                "result documents with id, title, and URL."
            ),
        )
        async def search(query: str) -> str:
            success = False
            try:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=0,
                    page_size=20,
                )
                items: list[dict[str, str]] = []
                if result.data:
                    for gene in result.data:
                        items.append(
                            {
                                "id": f"gene:{gene.gencode_id}",
                                "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                                "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                            }
                        )
                success = True
                return json.dumps({"results": items})
            except Exception:
                return json.dumps({"results": []})
            finally:
                record_mcp_tool_call(tool="search", success=success)

    if is_tool_in_profile("fetch", profile):

        @mcp.tool(
            name="fetch",
            description=(
                "Retrieve full details for a specific gene or genetic element "
                "from the GTEx Portal database. Use the `id` returned by "
                "`search` (format: `gene:<GENCODE_ID>`)."
            ),
        )
        async def fetch(id: str) -> str:
            success = False
            try:
                service = get_gtex_service()
                if not id.startswith("gene:"):
                    return json.dumps(
                        {
                            "id": id,
                            "title": "Unsupported resource type",
                            "text": f"Unsupported resource id format: {id!r}",
                            "url": GTEX_PORTAL_URL,
                            "metadata": {"source": "GTEx Portal", "type": "error"},
                        }
                    )

                gencode_id = id[len("gene:") :]
                gene_request = GeneRequest.model_validate(
                    {
                        "geneId": [gencode_id],
                        "page": 0,
                        "itemsPerPage": 1,
                    }
                )
                gene_result = await service.get_genes(gene_request)
                if not gene_result.data:
                    return json.dumps(
                        {
                            "id": id,
                            "title": "Resource not found",
                            "text": f"No gene found for {gencode_id!r}",
                            "url": GTEX_PORTAL_URL,
                            "metadata": {"source": "GTEx Portal", "type": "error"},
                        }
                    )
                gene = gene_result.data[0]

                expression_text: list[str] = []
                try:
                    expression_request = MedianGeneExpressionRequest(
                        gencodeId=[gencode_id],
                        tissueSiteDetailId=TissueSiteDetailId.ALL,
                        datasetId=DatasetId.GTEX_V8,
                        page=0,
                        itemsPerPage=50,
                    )
                    expression_result = await service.get_median_gene_expression(expression_request)
                    if expression_result.data:
                        expression_text.append("\nExpression Data (median TPM by tissue):")
                        for exp in expression_result.data[:10]:
                            expression_text.append(
                                f"  {exp.tissue_site_detail_id}: {exp.median:.2f} TPM"
                            )
                        if len(expression_result.data) > 10:
                            expression_text.append(
                                f"  ... and {len(expression_result.data) - 10} more tissues"
                            )
                except Exception:
                    expression_text = []

                lines = [
                    f"Gene Symbol: {gene.gene_symbol}",
                    f"GENCODE ID: {gene.gencode_id}",
                    f"Description: {gene.description or 'Not available'}",
                    f"Chromosome: {gene.chromosome}",
                    f"Position: {gene.start:,}-{gene.end:,}",
                    f"Strand: {gene.strand}",
                    f"Gene Type: {gene.gene_type}",
                    f"Gene Status: {gene.gene_status}",
                ]
                if gene.entrez_gene_id:
                    lines.append(f"Entrez Gene ID: {gene.entrez_gene_id}")
                lines.extend(expression_text)

                document = {
                    "id": id,
                    "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                    "text": "\n".join(lines),
                    "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                    "metadata": {
                        "source": "GTEx Portal v8",
                        "type": "gene",
                        "chromosome": gene.chromosome,
                        "gene_type": gene.gene_type,
                        "entrez_id": gene.entrez_gene_id,
                    },
                }
                success = True
                return json.dumps(document)
            except Exception as exc:
                return json.dumps(
                    {
                        "id": id,
                        "title": "Error",
                        "text": map_to_mcp_error_message(exc),
                        "url": GTEX_PORTAL_URL,
                        "metadata": {"source": "GTEx Portal", "type": "error"},
                    }
                )
            finally:
                record_mcp_tool_call(tool="fetch", success=success)
