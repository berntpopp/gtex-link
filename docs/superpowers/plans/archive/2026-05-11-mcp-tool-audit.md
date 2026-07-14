# MCP tool audit — 2026-05-11

> **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

Tools exposed by the current `FastMCP.from_fastapi` build, prior to Phase 3 facade migration.

Inspection: `await mcp_app.list_tools()` on fastmcp 3.x against `gtex_link.app.mcp_app`.

## Tools registered today (9 total)

| Tool | Source | Decision | Notes |
|---|---|---|---|
| `search` | Explicit (`_add_chatgpt_tools` in `app.py`) | preserve | ChatGPT-compatible search; ported to `gtex_link/mcp/tools/search_fetch.py` |
| `fetch` | Explicit (`_add_chatgpt_tools` in `app.py`) | preserve | ChatGPT-compatible fetch; ported to `gtex_link/mcp/tools/search_fetch.py` |
| `search_gtex_genes` | Auto from `/api/reference/geneSearch` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/reference.py` |
| `get_gene_information` | Auto from `/api/reference/gene` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/reference.py` |
| `get_transcript_information` | Auto from `/api/reference/transcript` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/reference.py` |
| `get_median_expression_levels` | Auto from `/api/expression/medianGeneExpression` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/expression.py` |
| `get_individual_expression_data` | Auto from `/api/expression/geneExpression` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/expression.py` |
| `get_top_expressed_genes_by_tissue` | Auto from `/api/expression/topExpressedGene` via `mcp_custom_names` | preserve | Re-registered in `gtex_link/mcp/tools/expression.py` |
| `version_info_api_version_get` | **Auto-generated, NOT in `mcp_custom_names`** | **drop** | Wraps `GET /api/version` (static `{"version": "0.1.0", "api_version": "v1", ...}`). No diagnostic value as an MCP tool — clients can hit `/api/version` directly. **Must be listed in CHANGELOG "Removed" block.** |

## Summary

- 8 tools preserved 1:1 by the new facade.
- 1 tool removed (`version_info_api_version_get`) — auto-generated wrapper for a static version endpoint, never intentionally exposed. Documented as a breaking change in `CHANGELOG.md`.

## fastmcp 3.x inspection notes

- Public API surface confirmed: `await mcp.list_tools() -> list[Tool]`, `add_middleware(...)`, `add_tool(...)`, `tool(...)` decorator. There is no `mount_to_fastapi` method on the bare `FastMCP` class — that method was on older versions or via a different helper. Phase 3 Task 15 (`server_manager.py`) must use the current 3.x mounting API instead.
- `mask_error_details` is stored as the private `_mask_error_details` attribute on fastmcp 3.x — the facade test should not assert on the public name.
