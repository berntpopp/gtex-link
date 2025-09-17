#!/usr/bin/env python3
"""MCP HTTP server entry point for GTEx-Link."""

import os
import sys


def main() -> None:
    """Run the MCP server with Streamable HTTP transport."""
    try:
        # Set environment variables for HTTP mode
        os.environ.setdefault("GTEX_LINK_TRANSPORT_MODE", "streamable-http")

        # Import here to avoid import issues
        from gtex_link.app import mcp_app
        from gtex_link.config import settings

        if mcp_app is None:
            print("ERROR: MCP app failed to initialize", file=sys.stderr)
            sys.exit(1)

        print(
            f"Starting GTEx-Link MCP server with Streamable HTTP transport on "
            f"{settings.host}:{settings.mcp_port}{settings.mcp_path}...",
            file=sys.stderr,
        )

        # Use FastMCP's built-in HTTP transport
        mcp_app.run(
            transport="streamable-http",
            host=settings.host,
            port=settings.mcp_port,
            path=settings.mcp_path,
        )

    except RuntimeError as e:
        if "Already running asyncio in this thread" in str(e):
            print(
                "ERROR: Asyncio conflict detected. Trying alternative approach...",
                file=sys.stderr,
            )
            # Try using anyio directly
            try:
                import anyio

                anyio.run(mcp_app.run_async)
            except Exception as e2:
                print(f"Alternative approach failed: {e2}", file=sys.stderr)
                sys.exit(1)
        else:
            raise
    except Exception as e:
        print(f"ERROR: Failed to start MCP HTTP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
