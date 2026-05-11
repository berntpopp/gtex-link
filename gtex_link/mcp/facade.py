"""MCP facade for GTEx-Link."""

from __future__ import annotations

from fastmcp import FastMCP

from gtex_link.config import settings
from gtex_link.mcp.output_validation import install_output_validation_error_handler
from gtex_link.mcp.profiles import MCPToolProfile, normalize_mcp_profile
from gtex_link.mcp.resources import GTEX_SERVER_INSTRUCTIONS
from gtex_link.mcp.tools import (
    register_expression_tools,
    register_reference_tools,
    register_search_fetch_tools,
)


def create_gtex_mcp(profile: MCPToolProfile | str | None = None) -> FastMCP:
    """Build a FastMCP instance for GTEx-Link.

    Args:
        profile: `MCPToolProfile.FULL` (default), `MCPToolProfile.LITE`, or
            their string equivalents. If `None`, falls back to
            `settings.mcp_profile`.

    Returns:
        A configured `FastMCP` with all matching tools registered.
    """
    if profile is None:
        profile = settings.mcp_profile
    selected = normalize_mcp_profile(profile)

    mcp = FastMCP(
        name="gtex-link",
        instructions=GTEX_SERVER_INSTRUCTIONS,
        mask_error_details=True,
    )

    register_search_fetch_tools(mcp, profile=selected)
    register_reference_tools(mcp, profile=selected)
    register_expression_tools(mcp, profile=selected)

    install_output_validation_error_handler(mcp)
    return mcp
