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
