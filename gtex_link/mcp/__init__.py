"""MCP facade for GTEx-Link.

This package replaces the previous auto-generation via FastMCP.from_fastapi
with an explicit facade. Construction entry point: `create_gtex_mcp`.
"""

# NOTE: The `create_gtex_mcp` re-export is added when `facade.py` lands in a
# later sub-task of Phase 3. Eagerly importing it here before the facade
# module exists would block submodule tests (e.g. `gtex_link.mcp.profiles`)
# from running, so the re-export is deferred.

__all__: list[str] = []
