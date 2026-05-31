"""MCP facade for GTEx-Link.

This package replaces the previous auto-generation via FastMCP.from_fastapi
with an explicit facade. Construction entry point: `create_gtex_mcp`.
"""

from gtex_link.mcp.facade import create_gtex_mcp

__all__ = ["create_gtex_mcp"]
