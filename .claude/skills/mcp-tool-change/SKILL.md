---
name: mcp-tool-change
description: Use when adding, renaming, or removing an MCP tool in gtex-link. Walks through facade registration, profiles, descriptions, tests.
---

# MCP tool change

Use this skill when changing the MCP tool surface (additions, renames, removals, description rewrites).

## Checklist

1. **Decide tool category.** Reference (`gene`, `transcript`, `feature`), expression (`median`, `top`, `individual`), or ChatGPT search/fetch.
2. **Register in the right file.**
   - Reference: `gtex_link/mcp/tools/reference.py`
   - Expression: `gtex_link/mcp/tools/expression.py`
   - ChatGPT: `gtex_link/mcp/tools/search_fetch.py`
3. **Tune the description.** Write for an AI client picking a tool — what does it do, when to use it, what does the input/output look like, what does it NOT do.
4. **Profile assignment.** Open `gtex_link/mcp/profiles.py` and decide if the tool belongs in `full`, `lite`, or both.
5. **Output validation.** Confirm `output_validation.py` will catch malformed outputs.
6. **Error mapping.** If the tool can raise a new exception class, add a mapping in `gtex_link/mcp/errors.py`.
7. **Tests.**
   - Add tests under `tests/test_mcp/` covering the tool's behavior, profile presence, and error masking.
   - Run `make test -k <tool_name>`.
8. **Preserved names.** Existing tool names are part of the public contract; renaming requires a `CHANGELOG.md` entry and a migration note.
9. **CI.** Run `make ci-local`.
