#!/usr/bin/env python3
"""MCP server entry point for GTEx-Link."""

import os
import sys


def main() -> None:
    """Run the MCP server."""
    try:
        # Set environment variables before importing
        os.environ.setdefault("GTEX_LINK_TRANSPORT_MODE", "stdio")

        # Import here to avoid import issues
        from gtex_link.app import mcp_app

        if mcp_app is None:
            print("ERROR: MCP app failed to initialize", file=sys.stderr)
            sys.exit(1)

        print("Starting GTEx-Link MCP server...", file=sys.stderr)

        # Use the direct run method - FastMCP should handle this correctly
        mcp_app.run()

    except RuntimeError as e:
        if "Already running asyncio in this thread" in str(e):
            print(
                "ERROR: Asyncio conflict detected. Trying alternative approach...", file=sys.stderr
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
        print(f"ERROR: Failed to start MCP server: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
