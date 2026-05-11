# CLAUDE.md

@AGENTS.md

Claude Code entrypoint:

- Use `AGENTS.md` for shared instructions.
- Run `make ci-local` before final handoff.
- Repo-local skills in `.claude/skills/` apply to matching tasks:
  - `fastapi-route-change` - adding or modifying FastAPI routes
  - `mcp-tool-change` - adding or renaming MCP tools
  - `ci-failure-triage` - reproducing and root-causing CI failures
  - `release-readiness` - pre-release checklist
  - `gtex-api-endpoint-add` - wiring a new upstream GTEx Portal endpoint
