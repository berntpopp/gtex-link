"""FastAPI application factory for GTEx-Link."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
        version="0.2.0",
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

    # Correlation ID and metrics middleware
    from gtex_link.observability import (
        install_correlation_middleware,
        install_metrics_middleware,
        install_metrics_route,
    )

    install_correlation_middleware(app)
    install_metrics_middleware(app)

    # Include routers
    app.include_router(reference_router)
    app.include_router(expression_router)
    app.include_router(health_router)

    # Mount /metrics endpoint
    install_metrics_route(app)

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint with service information."""
        return {
            "name": "GTEx-Link",
            "version": "0.2.0",
            "description": (
                "High-performance MCP/API server for GTEx Portal genetic expression database"
            ),
            "docs": "/docs",
            "health": "/api/health",
            "metrics": "/metrics",
            "mcp_endpoint": settings.mcp_path,
        }

    return app


# Create FastAPI application instance
app = create_app()
