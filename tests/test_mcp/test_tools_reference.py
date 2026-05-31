"""Tests for reference-category MCP tools."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.tools.reference import register_reference_tools


@pytest.mark.asyncio
async def test_search_gtex_genes_registered() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_reference_tools(mcp, profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search_gtex_genes" in names
    assert "get_gene_information" in names
    assert "get_transcript_information" in names


@pytest.mark.asyncio
async def test_lite_profile_includes_only_lite_reference_tools() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_reference_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search_gtex_genes" in names
    assert "get_gene_information" in names
    assert "get_transcript_information" not in names
