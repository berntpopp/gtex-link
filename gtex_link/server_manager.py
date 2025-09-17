"""Server management for GTEx-Link."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import uvicorn

from .app import app, mcp_app

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


class UnifiedServerManager:
    """Unified server manager for HTTP and MCP modes."""

    def __init__(self, logger: FilteringBoundLogger | None = None) -> None:
        """Initialize server manager.

        Args:
            logger: Optional logger instance
        """
        self.logger = logger

    async def start_server(
        self,
        host: str = "127.0.0.1",
        port: int = 8000,
        mode: str = "unified",
        reload: bool = False,
    ) -> None:
        """Start server in specified mode.

        Args:
            host: Server host
            port: Server port
            mode: Server mode (http, stdio, unified)
            reload: Enable auto-reload
        """
        if self.logger:
            self.logger.info("Starting server", mode=mode, host=host, port=port)

        if mode == "stdio":
            # Set environment variable for MCP/STDIO mode
            os.environ["TRANSPORT"] = "stdio"

            # Start MCP server in stdio mode
            if mcp_app is not None:
                await mcp_app.run()  # type: ignore[func-returns-value]
            else:
                raise RuntimeError("MCP app not available - cannot start in stdio mode")
            return

        elif mode == "http":
            # Start HTTP server only
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                reload=reload,
                log_config=None,  # Use our custom logging
            )
            server = uvicorn.Server(config)
            await server.serve()

        elif mode == "streamable-http":
            # Start MCP server with Streamable HTTP transport
            await self._start_streamable_http_mcp(host, port)

        elif mode == "mcp-unified":
            # Start unified server with FastAPI + MCP on same port
            await self._start_mcp_unified_server(host, port, reload)

        elif mode == "unified":
            # Check if we're in stdio mode via environment
            if os.environ.get("TRANSPORT") == "stdio":
                if mcp_app is not None:
                    await mcp_app.run()  # type: ignore[func-returns-value]
                else:
                    raise RuntimeError("MCP app not available - cannot start in unified/stdio mode")
                return
            else:
                # Start HTTP server
                config = uvicorn.Config(
                    app=app,
                    host=host,
                    port=port,
                    reload=reload,
                    log_config=None,  # Use our custom logging
                )
                server = uvicorn.Server(config)
                await server.serve()
        else:
            msg = f"Unknown server mode: {mode}"
            raise ValueError(msg)

    async def _start_streamable_http_mcp(self, host: str, port: int) -> None:
        """Start MCP server with Streamable HTTP transport."""
        if mcp_app is not None:
            if self.logger:
                self.logger.info(
                    "Starting MCP server with Streamable HTTP transport",
                    host=host,
                    port=port,
                    endpoint="/mcp",
                )

            try:
                await mcp_app.run(transport="streamable-http", host=host, port=port, path="/mcp")  # type: ignore[func-returns-value]
            except Exception as e:
                if self.logger:
                    self.logger.error("Failed to start MCP HTTP server", error=str(e))
                raise RuntimeError(f"MCP HTTP server failed to start: {e}") from e
        else:
            raise RuntimeError("MCP app not available - cannot start in streamable-http mode")

    async def _start_mcp_unified_server(self, host: str, port: int, reload: bool) -> None:
        """Start unified server with FastAPI + MCP on same port."""
        from .app import create_unified_app

        if self.logger:
            self.logger.info(
                "Starting unified server with FastAPI + MCP",
                host=host,
                port=port,
                mode="mcp-unified",
            )

        try:
            unified_app = create_unified_app()

            config = uvicorn.Config(
                app=unified_app,
                host=host,
                port=port,
                reload=reload,
                log_config=None,  # Use our custom logging
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            if self.logger:
                self.logger.error("Failed to start unified server", error=str(e))
            raise RuntimeError(f"Unified server failed to start: {e}") from e
