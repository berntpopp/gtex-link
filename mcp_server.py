"""MCP server entry point for GTEx-Link."""

import asyncio
import os

from gtex_link.app import mcp_app


async def main() -> None:
    """Run the MCP server."""
    # Set environment variable to ensure stdio mode
    os.environ["TRANSPORT"] = "stdio"

    # Run the MCP server
    await mcp_app.run()


if __name__ == "__main__":
    asyncio.run(main())
