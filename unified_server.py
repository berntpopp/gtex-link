#!/usr/bin/env python3
"""Unified server entry point for GTEx-Link (FastAPI + MCP)."""

import asyncio
import os
import sys


async def main() -> None:
    """Run the unified server."""
    try:
        # Set environment for unified mode
        os.environ.setdefault("GTEX_LINK_TRANSPORT_MODE", "mcp-unified")

        # Import here to avoid import issues
        from gtex_link.config import settings
        from gtex_link.server_manager import UnifiedServerManager

        # Create server manager and start in unified mode
        manager = UnifiedServerManager()
        await manager.start_server(
            host=settings.host,
            port=settings.port,
            mode="mcp-unified",
            reload=settings.reload,
        )

    except Exception as e:
        print(f"ERROR: Failed to start unified server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
