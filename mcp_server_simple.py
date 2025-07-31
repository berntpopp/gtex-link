#!/usr/bin/env python3
"""Simple MCP server entry point for GTEx-Link using direct MCP SDK."""

import asyncio
import os
import sys
from typing import Any, Sequence

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402
from mcp.types import TextContent, Tool  # noqa: E402

# Import GTEx services
from gtex_link.api.client import GTExClient  # noqa: E402
from gtex_link.config import settings  # noqa: E402
from gtex_link.logging_config import configure_logging  # noqa: E402
from gtex_link.models import (  # noqa: E402
    MedianGeneExpressionRequest,
    TopExpressedGenesRequest,
)
from gtex_link.models.gtex import TissueSiteDetailId  # noqa: E402
from gtex_link.services.gtex_service import GTExService  # noqa: E402


# Initialize logger
logger = configure_logging()

# Initialize GTEx service
gtex_client = GTExClient(config=settings.api, logger=logger)
gtex_service = GTExService(client=gtex_client, cache_config=settings.cache, logger=logger)

# Create MCP server
server = Server("gtex-link")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available GTEx tools."""
    return [
        Tool(
            name="search_gtex_genes",
            description="Search for genes in the GTEx Portal database",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gene symbol or identifier to search for (e.g., BRCA1, TP53)",
                    },
                    "gencode_version": {
                        "type": "string",
                        "description": "GENCODE version (optional)",
                        "default": None,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results per page (1-250)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 250,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_median_expression_levels",
            description="Get median gene expression levels across GTEx tissues",
            inputSchema={
                "type": "object",
                "properties": {
                    "gencode_id": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of versioned GENCODE IDs (e.g., ENSG00000012048.22)",
                    },
                    "tissue_site_detail_id": {
                        "type": "string",
                        "description": "Specific tissue to filter by (optional)",
                        "default": "",
                    },
                },
                "required": ["gencode_id"],
            },
        ),
        Tool(
            name="get_top_expressed_genes_by_tissue",
            description="Get top expressed genes for a specific tissue",
            inputSchema={
                "type": "object",
                "properties": {
                    "tissue_site_detail_id": {
                        "type": "string",
                        "description": "Tissue site detail ID (e.g., Whole_Blood, Brain_Cortex)",
                    },
                    "filter_mt_gene": {
                        "type": "boolean",
                        "description": "Filter mitochondrial genes",
                        "default": True,
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results per page (1-250)",
                        "default": 50,
                        "minimum": 1,
                        "maximum": 250,
                    },
                },
                "required": ["tissue_site_detail_id"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> Sequence[TextContent]:
    """Handle tool calls."""
    try:
        if name == "search_gtex_genes":
            query = arguments["query"]
            gencode_version = arguments.get("gencode_version")
            page_size = arguments.get("page_size", 50)

            result = await gtex_service.search_genes(
                query=query, gencode_version=gencode_version, page_size=page_size
            )

            # Format results
            genes = []
            for gene in result.data:
                genes.append(
                    {
                        "gene_symbol": gene.gene_symbol,
                        "gencode_id": gene.gencode_id,
                        "description": gene.description,
                        "chromosome": gene.chromosome,
                        "start": gene.start,
                        "end": gene.end,
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(genes)} genes:\n\n"
                    + "\n".join(
                        [
                            f"• {g['gene_symbol']} ({g['gencode_id']}): {g['description']}"
                            for g in genes
                        ]
                    ),
                )
            ]

        elif name == "get_median_expression_levels":
            gencode_ids = arguments["gencode_id"]
            tissue_filter = arguments.get("tissue_site_detail_id", "")

            request = MedianGeneExpressionRequest(
                gencode_id=gencode_ids,
                tissue_site_detail_id=tissue_filter or TissueSiteDetailId.ALL,
            )

            result = await gtex_service.get_median_gene_expression(request)

            # Format results
            expressions = []
            for expr in result.data:
                expressions.append(
                    {
                        "gene_symbol": expr.gene_symbol,
                        "tissue": expr.tissue_site_detail_id,
                        "median_tpm": expr.median,
                        "num_samples": expr.num_samples,
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Found {len(expressions)} expression records:\n\n"
                    + "\n".join(
                        [
                            f"• {e['gene_symbol']} in {e['tissue']}: "
                            f"{e['median_tpm']:.2f} TPM ({e['num_samples']} samples)"
                            for e in expressions[:10]
                        ]
                    ),  # Limit to first 10
                )
            ]

        elif name == "get_top_expressed_genes_by_tissue":
            tissue = arguments["tissue_site_detail_id"]
            filter_mt = arguments.get("filter_mt_gene", True)
            page_size = arguments.get("page_size", 50)

            request = TopExpressedGenesRequest(
                tissue_site_detail_id=tissue, filter_mt_gene=filter_mt, items_per_page=page_size
            )

            result = await gtex_service.get_top_expressed_genes(request)

            # Format results
            genes = []
            for gene in result.data:
                genes.append(
                    {
                        "gene_symbol": gene.gene_symbol,
                        "median_tpm": gene.median,
                        "tissue": gene.tissue_site_detail_id,
                    }
                )

            return [
                TextContent(
                    type="text",
                    text=f"Top {len(genes)} expressed genes in {tissue}:\n\n"
                    + "\n".join(
                        [
                            f"{i + 1}. {g['gene_symbol']}: {g['median_tpm']:.2f} TPM"
                            for i, g in enumerate(genes)
                        ]
                    ),
                )
            ]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.exception(f"Error in tool {name}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Run the MCP server."""
    print("Starting GTEx-Link MCP server (simple)...", file=sys.stderr)

    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped by user", file=sys.stderr)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
