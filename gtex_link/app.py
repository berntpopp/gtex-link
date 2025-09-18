"""Main FastAPI application with FastMCP integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from .api.routes import expression_router, health_router, reference_router
from .config import settings
from .logging_config import configure_logging, log_server_startup
from .services.gtex_service import GTExService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger = configure_logging()
    log_server_startup(logger, "startup", settings.host, settings.port)

    yield

    logger.info("Application shutting down")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="GTEx-Link",
        description=("High-performance MCP/API server for GTEx Portal genetic expression database"),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Include routers
    app.include_router(reference_router)
    app.include_router(expression_router)
    app.include_router(health_router)

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with service information."""
        return {
            "name": "GTEx-Link",
            "version": "0.1.0",
            "description": (
                "High-performance MCP/API server for GTEx Portal genetic expression database"
            ),
            "docs": "/docs",
            "health": "/api/health",
            "mcp_endpoint": settings.mcp_path,
        }

    return app


def create_mcp_app() -> FastMCP:
    """Create FastMCP server from FastAPI app."""
    app = create_app()

    # MCP tool name mappings for GTEx functions (user-friendly names)
    mcp_custom_names = {
        "search_genes": "search_gtex_genes",
        "get_genes": "get_gene_information",
        "get_transcripts": "get_transcript_information",
        "get_median_gene_expression": "get_median_expression_levels",
        "get_gene_expression": "get_individual_expression_data",
        "get_top_expressed_genes": "get_top_expressed_genes_by_tissue",
    }

    # Route mappings for MCP tools (exclude utility endpoints)
    mcp_route_maps = [
        # Exclude health and monitoring endpoints
        RouteMap(pattern=r"^/api/health.*$", mcp_type=MCPType.EXCLUDE),
        # Exclude root and docs endpoints
        RouteMap(pattern=r"^/$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/docs$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openapi.json$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/redoc$", mcp_type=MCPType.EXCLUDE),
    ]

    # Create FastMCP instance with proper configuration
    mcp = FastMCP.from_fastapi(
        app=app,
        name="gtex-link",
        mcp_names=mcp_custom_names,
        route_maps=mcp_route_maps,
    )

    # Add ChatGPT-compatible search and fetch tools
    _add_chatgpt_tools(mcp)

    return mcp


def _add_chatgpt_tools(mcp: FastMCP) -> None:
    """Add ChatGPT-compatible search and fetch tools."""
    import json

    from .api.client import GTExClient
    from .config import DEFAULT_API_CONFIG, DEFAULT_CACHE_CONFIG
    from .models import GeneRequest, MedianGeneExpressionRequest

    # Initialize services for the tools
    api_client = GTExClient(config=DEFAULT_API_CONFIG)
    gtex_service = GTExService(client=api_client, cache_config=DEFAULT_CACHE_CONFIG)

    @mcp.tool(
        name="search",
        description="Search the GTEx Portal genetic expression database for genes, transcripts, and expression data.",
    )
    async def search(query: str) -> str:
        """Search for genes and genetic data in GTEx Portal database.

        Returns search results with id, title, and url for each result.
        """
        try:
            # Search genes using the existing GTEx service
            result = await gtex_service.search_genes(
                query=query,
                gencode_version=None,
                genome_build=None,
                page=0,
                page_size=20,  # Limit to first 20 results
            )

            # Transform results to ChatGPT-compatible format
            search_results = []
            if result.data:
                for gene in result.data:
                    search_results.append(
                        {
                            "id": f"gene:{gene.gencodeId}",
                            "title": f"{gene.geneSymbol} - {gene.description or 'Gene'}",
                            "url": f"https://gtexportal.org/home/gene/{gene.geneSymbol}",
                        }
                    )

            # Return JSON-encoded results as required by ChatGPT
            return json.dumps({"results": search_results})

        except Exception:
            # Return empty results on error
            return json.dumps({"results": []})

    @mcp.tool(
        name="fetch",
        description="Retrieve full details for a specific gene or genetic element from GTEx Portal database.",
    )
    async def fetch(id: str) -> str:
        """Fetch detailed information about a specific gene or genetic element.

        Returns full document content with id, title, text, url, and metadata.
        """
        try:
            # Parse the ID to determine resource type
            if id.startswith("gene:"):
                gencode_id = id.replace("gene:", "")

                # Get detailed gene information
                gene_request = GeneRequest(geneId=[gencode_id], page=0, itemsPerPage=1)
                gene_result = await gtex_service.get_genes(gene_request)

                if gene_result.data and len(gene_result.data) > 0:
                    gene = gene_result.data[0]

                    # Get expression data for this gene
                    try:
                        expression_request = MedianGeneExpressionRequest(
                            gencodeId=[gencode_id],
                            tissueSiteDetailId="",  # All tissues
                            datasetId="gtex_v8",
                            page=0,
                            itemsPerPage=50,
                        )
                        expression_result = await gtex_service.get_median_gene_expression(
                            expression_request
                        )
                    except Exception:
                        expression_result = None

                    # Build comprehensive text content
                    text_parts = [
                        f"Gene Symbol: {gene.geneSymbol}",
                        f"GENCODE ID: {gene.gencodeId}",
                        f"Description: {gene.description or 'Not available'}",
                        f"Chromosome: {gene.chromosome}",
                        f"Position: {gene.start:,}-{gene.end:,}",
                        f"Strand: {gene.strand}",
                        f"Gene Type: {gene.geneType}",
                        f"Gene Status: {gene.geneStatus}",
                    ]

                    if gene.entrezGeneId:
                        text_parts.append(f"Entrez Gene ID: {gene.entrezGeneId}")

                    # Add expression data if available
                    if expression_result and expression_result.data:
                        text_parts.append("\nExpression Data (median TPM by tissue):")
                        for exp in expression_result.data[:10]:  # Top 10 tissues
                            text_parts.append(f"  {exp.tissueSiteDetailId}: {exp.median:.2f} TPM")

                        if len(expression_result.data) > 10:
                            text_parts.append(
                                f"  ... and {len(expression_result.data) - 10} more tissues"
                            )

                    # Prepare the document response
                    document = {
                        "id": id,
                        "title": f"{gene.geneSymbol} - {gene.description or 'Gene'}",
                        "text": "\n".join(text_parts),
                        "url": f"https://gtexportal.org/home/gene/{gene.geneSymbol}",
                        "metadata": {
                            "source": "GTEx Portal v8",
                            "type": "gene",
                            "chromosome": gene.chromosome,
                            "gene_type": gene.geneType,
                            "entrez_id": gene.entrezGeneId,
                        },
                    }

                    return json.dumps(document)

            # If we can't find or parse the resource, return error document
            return json.dumps(
                {
                    "id": id,
                    "title": "Resource Not Found",
                    "text": f"The requested resource with ID '{id}' could not be found in the GTEx Portal database.",
                    "url": "https://gtexportal.org/",
                    "metadata": {"source": "GTEx Portal", "type": "error"},
                }
            )

        except Exception as e:
            # Return error document on exception
            return json.dumps(
                {
                    "id": id,
                    "title": "Error Retrieving Resource",
                    "text": f"An error occurred while retrieving the resource: {str(e)}",
                    "url": "https://gtexportal.org/",
                    "metadata": {"source": "GTEx Portal", "type": "error", "error": str(e)},
                }
            )


# Create application instances
app = create_app()

# Create MCP app conditionally to avoid schema generation issues
try:
    mcp_app: FastMCP[Any] | None = create_mcp_app()
except Exception as e:
    import warnings

    warnings.warn(f"MCP app creation failed: {e}", UserWarning)
    mcp_app = None
