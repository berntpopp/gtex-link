"""Unified server manager for HTTP and unified (HTTP+MCP) transports.

Streamable HTTP only — there is no stdio transport.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING, Any

import uvicorn

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from structlog.typing import FilteringBoundLogger


def create_http_app(extra_lifespan: Any = None) -> FastAPI:
    """Create the REST host behind the strict outer request guard."""
    from fastmcp.server.http import HostOriginGuardMiddleware

    from gtex_link.app import create_app
    from gtex_link.config import settings

    application = create_app()
    if extra_lifespan is not None:
        original_lifespan = application.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(original_lifespan(app))
                await stack.enter_async_context(extra_lifespan(app))
                yield

        application.router.lifespan_context = combined_lifespan
    application.add_middleware(
        HostOriginGuardMiddleware,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
        mode="strict",
    )
    return application


def create_unified_app() -> FastAPI:
    """Create the guarded REST host and mount the native-guarded MCP app."""
    from gtex_link.config import settings
    from gtex_link.mcp.facade import create_gtex_mcp

    mcp = create_gtex_mcp()
    mcp_asgi = mcp.http_app(
        path=settings.mcp_path,
        stateless_http=True,
        json_response=True,
        host_origin_protection=True,
        allowed_hosts=settings.allowed_hosts,
        allowed_origins=settings.allowed_origins,
    )
    application = create_http_app(extra_lifespan=mcp_asgi.router.lifespan_context)
    application.mount("/", mcp_asgi)
    return application


class UnifiedServerManager:
    """Orchestrate startup of GTEx-Link over Streamable HTTP transports."""

    def __init__(self, logger: FilteringBoundLogger | None = None) -> None:
        """Build a manager.

        Args:
            logger: Optional structlog logger for lifecycle events.
        """
        self.logger = logger
        self._uvicorn_server: uvicorn.Server | None = None

    # --- Transports -----------------------------------------------------

    async def start_unified_server(self, host: str, port: int) -> None:
        """Start FastAPI + MCP (streamable-http transport) on the same port.

        fastmcp 3.x integration note:
            The plan body referenced `mcp.mount_to_fastapi(app, path="/mcp")`,
            which does not exist on fastmcp 3.x. The supported pattern is
            `mcp.http_app(path=...)` which returns a `StarletteWithLifespan`
            ASGI app. We mount that sub-app onto the FastAPI host and combine
            both lifespans so the MCP session manager starts and stops
            cleanly. See https://gofastmcp.com/integrations/fastapi for the
            recommended integration approach.
        """
        if self.logger:
            self.logger.info(
                "Starting unified server",
                host=host,
                port=port,
                mcp_path="/mcp",
            )

        fastapi_app = create_unified_app()

        config = uvicorn.Config(
            app=fastapi_app,
            host=host,
            port=port,
            log_config=None,
            lifespan="on",
        )
        self._uvicorn_server = uvicorn.Server(config)
        await self._uvicorn_server.serve()

    async def start_http_only_server(self, host: str, port: int) -> None:
        """Start FastAPI only (no MCP)."""
        if self.logger:
            self.logger.info("Starting HTTP-only server", host=host, port=port)
        config = uvicorn.Config(
            app=create_http_app(),
            host=host,
            port=port,
            log_config=None,
            lifespan="on",
        )
        self._uvicorn_server = uvicorn.Server(config)
        await self._uvicorn_server.serve()

    # --- Lifecycle ------------------------------------------------------

    async def shutdown(self) -> None:
        """Gracefully stop any running server."""
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
        if self.logger:
            self.logger.info("Shutdown complete")
