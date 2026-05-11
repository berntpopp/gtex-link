"""Tests for MCP tool profiles."""

from __future__ import annotations

import pytest

from gtex_link.mcp.profiles import (
    LITE_TOOLS,
    MCPToolProfile,
    is_tool_in_profile,
    normalize_mcp_profile,
)


def test_normalize_accepts_canonical_strings() -> None:
    assert normalize_mcp_profile("full") == MCPToolProfile.FULL
    assert normalize_mcp_profile("lite") == MCPToolProfile.LITE


def test_normalize_accepts_enum() -> None:
    assert normalize_mcp_profile(MCPToolProfile.FULL) == MCPToolProfile.FULL


def test_normalize_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        normalize_mcp_profile("expert")


def test_lite_tool_set_is_explicit() -> None:
    expected = {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
    }
    assert expected == LITE_TOOLS


def test_full_profile_includes_everything() -> None:
    assert is_tool_in_profile("get_top_expressed_genes_by_tissue", MCPToolProfile.FULL)


def test_lite_profile_excludes_advanced_tools() -> None:
    assert not is_tool_in_profile("get_top_expressed_genes_by_tissue", MCPToolProfile.LITE)
    assert is_tool_in_profile("search_gtex_genes", MCPToolProfile.LITE)
