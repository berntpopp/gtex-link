"""Main FastAPI application with FastMCP integration."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap

from .api.routes import association_router, expression_router, health_router, reference_router
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
    app.include_router(association_router)
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

    # MCP tool name mappings for GTEx functions

    # Route mappings for MCP tools (exclude utility endpoints)
    [
        # Exclude health and monitoring endpoints
        RouteMap(pattern=r"^/api/health.*$", mcp_type=MCPType.EXCLUDE),
        # Exclude root and docs endpoints
        RouteMap(pattern=r"^/$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/docs$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openapi.json$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/redoc$", mcp_type=MCPType.EXCLUDE),
    ]

    # Create FastMCP instance with basic configuration
    return FastMCP(app)


# Create default app instance
app = create_app()

# Create MCP app instance
mcp_app = create_mcp_app()
