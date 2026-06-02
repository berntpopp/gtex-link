"""Tests for the MCP facade."""

from __future__ import annotations

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile


@pytest.mark.asyncio
async def test_facade_builds_and_lists_all_full_tools() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_transcript_information",
        "get_median_expression_levels",
        "get_individual_expression_data",
        "get_top_expressed_genes_by_tissue",
        "get_server_capabilities",
    }


@pytest.mark.asyncio
async def test_facade_lite_profile_subset() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
        "get_server_capabilities",
    }


@pytest.mark.asyncio
async def test_facade_accepts_string_profile() -> None:
    mcp = create_gtex_mcp(profile="lite")
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search" in names
    assert "get_top_expressed_genes_by_tissue" not in names


@pytest.mark.asyncio
async def test_facade_has_mask_error_details_on() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    assert getattr(mcp, "_mask_error_details", None) is True


@pytest.mark.asyncio
async def test_capabilities_tool_and_resources_registered() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tool_names = {t.name for t in await mcp.list_tools()}
    assert "get_server_capabilities" in tool_names

    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "gtex://capabilities" in uris
    assert "gtex://reference" in uris
