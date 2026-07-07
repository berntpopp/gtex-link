"""Unified server manager for HTTP and unified (HTTP+MCP) transports.

Streamable HTTP only — there is no stdio transport.
"""

from __future__ import annotations

from contextlib import AsyncExitStack, asynccontextmanager
from typing import TYPE_CHECKING

import uvicorn

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fastapi import FastAPI
    from structlog.typing import FilteringBoundLogger


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

        from gtex_link.app import app as fastapi_app
        from gtex_link.config import settings
        from gtex_link.mcp.facade import create_gtex_mcp

        mcp = create_gtex_mcp()
        # host_origin_protection defaults to True since fastmcp 3.4.3, which 421s
        # every request whose Host is not localhost -- including legitimate proxied
        # traffic from the genefoundry-router. The reverse proxy (NPM) already
        # validates the Host via server_name + TLS SNI, so disable the redundant
        # app-layer guard here to keep the public /mcp reachable.
        mcp_asgi = mcp.http_app(
            path=settings.mcp_path,
            stateless_http=True,
            json_response=True,
            host_origin_protection=False,
        )

        # Compose the FastAPI lifespan with the MCP ASGI app's lifespan so
        # the streamable-http session manager is initialised when uvicorn
        # starts the combined app.
        original_lifespan = fastapi_app.router.lifespan_context

        @asynccontextmanager
        async def combined_lifespan(app: FastAPI) -> AsyncIterator[None]:
            async with AsyncExitStack() as stack:
                await stack.enter_async_context(original_lifespan(app))
                await stack.enter_async_context(mcp_asgi.router.lifespan_context(app))
                yield

        fastapi_app.router.lifespan_context = combined_lifespan
        # Mount the MCP ASGI sub-app at the project root: the MCP path
        # itself ("/mcp") is already baked into the StarletteWithLifespan
        # routes returned by `http_app(path=...)`.
        fastapi_app.mount("/", mcp_asgi)

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
        from gtex_link.app import app as fastapi_app

        config = uvicorn.Config(
            app=fastapi_app,
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
