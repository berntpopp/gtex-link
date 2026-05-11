"""Tests for expression-category MCP tools."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.tools.expression import register_expression_tools


@pytest.mark.asyncio
async def test_expression_tools_registered_under_full_profile() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_expression_tools(mcp, profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert {
        "get_median_expression_levels",
        "get_individual_expression_data",
        "get_top_expressed_genes_by_tissue",
    } <= names


@pytest.mark.asyncio
async def test_lite_profile_only_exposes_median_expression() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_expression_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "get_median_expression_levels" in names
    assert "get_top_expressed_genes_by_tissue" not in names
    assert "get_individual_expression_data" not in names
