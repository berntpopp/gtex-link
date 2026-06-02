"""Tests for ChatGPT-compatible search/fetch MCP tools."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.tools.search_fetch import register_search_fetch_tools


@pytest.mark.asyncio
async def test_search_fetch_registered_under_full_profile() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_search_fetch_tools(mcp, profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search" in names
    assert "fetch" in names


@pytest.mark.asyncio
async def test_search_fetch_registered_under_lite_profile() -> None:
    mcp: FastMCP = FastMCP(name="test")
    register_search_fetch_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    # search/fetch are always in lite
    assert "search" in names
    assert "fetch" in names


@pytest.mark.asyncio
async def test_tools_are_annotated_read_only() -> None:
    from gtex_link.mcp.facade import create_gtex_mcp

    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tools = {t.name: t for t in await mcp.list_tools()}
    median = tools["get_median_expression_levels"]
    assert median.annotations is not None
    assert median.annotations.readOnlyHint is True
    assert median.annotations.openWorldHint is True
