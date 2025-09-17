"""Server management for GTEx-Link."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import uvicorn

from .app import app, mcp_app

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


class ServerManager:
    """Server manager for HTTP and MCP modes."""

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
        mode: str = "http",
        reload: bool = False,
    ) -> None:
        """Start server in specified mode.

        Args:
            host: Server host
            port: Server port
            mode: Server mode (http, stdio, streamable-http)
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
