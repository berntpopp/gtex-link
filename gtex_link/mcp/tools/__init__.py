"""MCP tool registration modules grouped by category."""

# NOTE: Re-exports for `register_expression_tools`, `register_reference_tools`,
# and `register_search_fetch_tools` are added when their modules land in later
# sub-tasks of Phase 3. Importing them eagerly here would block mypy and any
# test that touches the `gtex_link.mcp.tools` package before they exist.

__all__: list[str] = []
