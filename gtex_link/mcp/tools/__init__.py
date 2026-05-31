"""MCP tool registration modules grouped by category."""

from gtex_link.mcp.tools.expression import register_expression_tools
from gtex_link.mcp.tools.reference import register_reference_tools
from gtex_link.mcp.tools.search_fetch import register_search_fetch_tools

__all__ = [
    "register_expression_tools",
    "register_reference_tools",
    "register_search_fetch_tools",
]
