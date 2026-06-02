"""ChatGPT-compatible search and fetch MCP tools.

These mirror the OpenAI deep-research / Apps SDK shape -- `search(query) ->
{results: [...]}` and `fetch(id) -> {id, title, text, url, metadata}` -- so a
single MCP server is consumable by ChatGPT (reads `text`) and Claude (reads
structuredContent). `search` recall is identifier-only (GTEx geneSearch matches
gene_id), so a natural-language query is tokenized and each candidate token is
resolved against the catalog, then unioned and ranked by match quality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_PORTAL_URL
from gtex_link.mcp.search_match import (
    _RANK_ORDER,
    MAX_QUERY_TOKENS,
    classify_match,
    recall_terms,
)
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, MedianGeneExpressionRequest
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

_FETCH_TISSUE_LIMIT = 10


def register_search_fetch_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register the ChatGPT-compatible `search` and `fetch` tools."""
    if is_tool_in_profile("search", profile):

        @mcp.tool(
            name="search",
            title="Search",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"search"},
            description=(
                "Search the GTEx Portal genetic expression database for genes. "
                "Accepts a natural-language query (e.g. 'UMOD kidney "
                "expression'); gene-like terms are matched against the catalog. "
                "Returns result documents with id, title, and URL."
            ),
        )
        async def search(query: str) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                tokens = recall_terms(query)[:MAX_QUERY_TOKENS] or [query.strip()]
                # token -> (rank, gene) keeping the best rank seen per gencode_id
                best: dict[str, tuple[int, Any]] = {}
                for token in tokens:
                    result = await service.search_genes(
                        query=token,
                        gencode_version=None,
                        genome_build=None,
                        page=0,
                        page_size=20,
                    )
                    for gene in result.data:
                        quality = classify_match(
                            token, symbol=gene.gene_symbol, gencode_id=gene.gencode_id
                        )
                        rank = _RANK_ORDER[quality]
                        prior = best.get(gene.gencode_id)
                        if prior is None or rank < prior[0]:
                            best[gene.gencode_id] = (rank, gene)
                ordered = sorted(best.values(), key=lambda rg: (rg[0], rg[1].gene_symbol))
                items = [
                    {
                        "id": f"gene:{gene.gencode_id}",
                        "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                        "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                    }
                    for _rank, gene in ordered
                ]
                return {"results": items}

            success = False
            try:
                payload = await run_mcp_tool("search", call, context=McpErrorContext("search"))
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="search", success=success)

    if is_tool_in_profile("fetch", profile):

        @mcp.tool(
            name="fetch",
            title="Fetch",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"search"},
            description=(
                "Retrieve full details for a gene from the GTEx Portal database. "
                "Use the `id` returned by `search` (`gene:<GENCODE_ID>`); a bare "
                "GENCODE ID is also accepted. Expression is listed highest-median "
                "tissue first."
            ),
        )
        async def fetch(id: str) -> dict[str, Any]:
            success = False
            try:
                service = get_gtex_service()
                gencode_id = id[len("gene:") :] if id.startswith("gene:") else id
                if not gencode_id:
                    return _error_doc(
                        id, "Unsupported resource type", f"Unsupported resource id: {id!r}"
                    )

                gene_request = GeneRequest.model_validate(
                    {"geneId": [gencode_id], "page": 0, "itemsPerPage": 1}
                )
                gene_result = await service.get_genes(gene_request)
                if not gene_result.data:
                    return _error_doc(id, "Resource not found", f"No gene found for {gencode_id!r}")
                gene = gene_result.data[0]

                expression_text = await _expression_lines(service, gene.gencode_id)
                lines = [
                    f"Gene Symbol: {gene.gene_symbol}",
                    f"GENCODE ID: {gene.gencode_id}",
                    f"Description: {gene.description or 'Not available'}",
                    f"Chromosome: {gene.chromosome}",
                    f"Position: {gene.start:,}-{gene.end:,}",
                    f"Strand: {gene.strand}",
                    f"Gene Type: {gene.gene_type}",
                ]
                if gene.entrez_gene_id:
                    lines.append(f"Entrez Gene ID: {gene.entrez_gene_id}")
                lines.extend(expression_text)

                success = True
                return {
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
            except Exception:
                return _error_doc(id, "Error", "An error occurred fetching this resource.")
            finally:
                record_mcp_tool_call(tool="fetch", success=success)


def _error_doc(resource_id: str, title: str, text: str) -> dict[str, Any]:
    return {
        "id": resource_id,
        "title": title,
        "text": text,
        "url": GTEX_PORTAL_URL,
        "metadata": {"source": "GTEx Portal", "type": "error"},
    }


async def _expression_lines(service: Any, gencode_id: str) -> list[str]:
    """Return median-TPM lines sorted highest-first; empty list on any failure."""
    try:
        request = MedianGeneExpressionRequest.model_validate(
            {
                "gencodeId": [gencode_id],
                "tissueSiteDetailId": "",
                "datasetId": "gtex_v8",
                "page": 0,
                "itemsPerPage": 60,
            }
        )
        result = await service.get_median_gene_expression(request)
    except Exception:
        return []
    if not result.data:
        return []
    ranked = sorted(result.data, key=lambda exp: exp.median, reverse=True)
    lines = ["\nExpression Data (median TPM by tissue, highest first):"]
    for exp in ranked[:_FETCH_TISSUE_LIMIT]:
        lines.append(f"  {exp.tissue_site_detail_id}: {exp.median:.2f} TPM")
    if len(ranked) > _FETCH_TISSUE_LIMIT:
        cutoff = ranked[_FETCH_TISSUE_LIMIT].median
        lines.append(
            f"  ... and {len(ranked) - _FETCH_TISSUE_LIMIT} more tissues at <= {cutoff:.2f} TPM"
        )
    return lines
