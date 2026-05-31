"""MCP tool profile selection.

A profile is a named subset of MCP tools to expose. `full` enables everything;
`lite` exposes only the common-path tools.
"""

from __future__ import annotations

from enum import StrEnum


class MCPToolProfile(StrEnum):
    """MCP tool profile identifiers."""

    FULL = "full"
    LITE = "lite"


LITE_TOOLS: frozenset[str] = frozenset(
    {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
    }
)


def normalize_mcp_profile(value: MCPToolProfile | str) -> MCPToolProfile:
    """Coerce a string or enum into an MCPToolProfile.

    Raises:
        ValueError: if `value` is not a known profile.
    """
    if isinstance(value, MCPToolProfile):
        return value
    try:
        return MCPToolProfile(value)
    except ValueError as exc:
        valid = ", ".join(p.value for p in MCPToolProfile)
        raise ValueError(f"Unknown MCP profile {value!r}; valid: {valid}") from exc


def is_tool_in_profile(tool_name: str, profile: MCPToolProfile) -> bool:
    """Return True if `tool_name` should be exposed under `profile`."""
    if profile is MCPToolProfile.FULL:
        return True
    # MCPToolProfile.LITE — exhaustive over the enum, so no trailing branch.
    return tool_name in LITE_TOOLS
