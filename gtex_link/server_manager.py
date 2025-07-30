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
            await mcp_app.run()

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

        elif mode == "unified":
            # Check if we're in stdio mode via environment
            if os.environ.get("TRANSPORT") == "stdio":
                await mcp_app.run()
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
