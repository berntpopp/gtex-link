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
    return FastMCP.from_fastapi(
        app=app,
        name="gtex-link",
        mcp_names=mcp_custom_names,
        route_maps=mcp_route_maps,
    )


def create_unified_app() -> FastAPI:
    """Create unified FastAPI app with MCP capabilities.

    This creates a FastAPI app that serves both REST API endpoints
    and provides MCP integration information.
    """
    # Create base FastAPI app
    base_app = create_app()

    # Override root endpoint to include MCP information
    @base_app.get("/", response_model=None)
    async def unified_root() -> dict[str, Any]:
        """Root endpoint for unified server with MCP info."""
        return {
            "name": "GTEx-Link",
            "version": "0.1.0",
            "description": (
                "High-performance MCP/API server for GTEx Portal genetic expression database"
            ),
            "docs": "/docs",
            "health": "/api/health",
            "mcp_info": {
                "available": True,
                "transport": "http",
                "endpoint": settings.mcp_path,
                "note": "MCP server running on separate transport - use dedicated MCP client",
            },
            "mode": "unified",
        }

    return base_app


# Create application instances
app = create_app()

# Create MCP app conditionally to avoid schema generation issues
try:
    mcp_app: FastMCP[Any] | None = create_mcp_app()
except Exception as e:
    import warnings

    warnings.warn(f"MCP app creation failed: {e}", UserWarning)
    mcp_app = None
