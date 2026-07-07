"""FastAPI application factory for GTEx-Link."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
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
    docs_enabled = not settings.disable_docs
    app = FastAPI(
        title="GTEx-Link",
        description=("High-performance MCP/API server for GTEx Portal genetic expression database"),
        version=__version__,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        lifespan=lifespan,
    )

    # Add CORS middleware. Reject the insecure allow_credentials + '*' origin
    # combination at startup: this backend is unauthenticated (no cookies/session),
    # so credentialed CORS is meaningless and a wildcard origin with credentials is
    # a footgun. Fail fast rather than silently misconfigure.
    if settings.cors_allow_credentials and "*" in settings.cors_origins:
        msg = (
            "Insecure CORS: allow_credentials=True with a wildcard '*' origin is "
            "forbidden. This backend is unauthenticated and holds no cookies or "
            "session; set cors_allow_credentials=False or use explicit origins."
        )
        raise RuntimeError(msg)
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
            "version": __version__,
            "description": (
                "High-performance MCP/API server for GTEx Portal genetic expression database"
            ),
            "docs": "/docs" if not settings.disable_docs else None,
            "health": "/api/health",
            "metrics": "/metrics",
            "mcp_endpoint": settings.mcp_path,
        }

    # MCP Transport Standard v1 health endpoint (probe-compatible)
    @app.get("/health")
    async def health() -> dict[str, Any]:
        """Lightweight health endpoint required by MCP Transport Standard v1."""
        return {
            "status": "ok",
            "version": __version__,
            "transport": "streamable-http-stateless",
        }

    return app


# Create FastAPI application instance
app = create_app()
