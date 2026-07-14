# AGENTS.md

Shared repository instructions for agentic coding tools working in GTEx-Link.

## Project

GTEx-Link is a Python FastAPI and MCP server that exposes the GTEx Portal v2
biomedical expression database. It serves a REST API and a Model Context
Protocol surface for AI assistants.

Primary areas:

- `gtex_link/` - Python package, FastAPI routes, services, client, MCP code
- `tests/` - unit and integration tests
- `docker/` - Dockerfile and Compose deployment files
- `docs/` - `configuration.md`, `deployment.md`, `architecture.md`, `data.md`,
  `conventions.md`; GTEx Portal endpoint documentation (`docs/README.md`,
  `docs/api_v2_*.md`); design specs/plans (`docs/superpowers/`)
- `.claude/skills/` - repo-local Claude Code workflows for recurring tasks

The README follows the GeneFoundry README Standard v1 (canonical text lives in
`genefoundry-router/docs/README-STANDARD-v1.md`). It is a front door, not a
manual: keep runbooks, env tables, and architecture deep-dives in `docs/`.
`make lint-readme` and `tests/unit/test_readme_tools.py` enforce this — the
latter fails if a tool is added without updating the README's `## Tools` table.

## Source Of Truth

- Use this file for shared repo-wide agent guidance.
- Keep `CLAUDE.md` lean and Claude-specific; it should reference this file.
- Keep `GEMINI.md` lean and Gemini-specific; it should reference this file.
- Use repo-local `.claude/skills/` workflows when a task matches their scope.
- Prefer `Makefile` targets over ad hoc commands.
- Use `uv.lock` as the dependency lock source of truth.

## Working Rules

- Do not revert or overwrite changes you did not make unless explicitly asked.
- Keep edits scoped to the task and avoid unrelated refactors.
- Prefer existing code patterns over new abstractions.
- Put tests under `tests/`; do not create alternate test roots.
- Use ASCII unless a file already requires non-ASCII content.
- For MCP work, keep public hosted tools research-use scoped and avoid
  exposing destructive cache operations.

## Commands

Required check before claiming completion:

- `make ci-local`

Useful focused commands:

- `make install`
- `make lock`
- `make format`
- `make lint`
- `make lint-fix`
- `make lint-loc`
- `make lint-readme`
- `make typecheck`
- `make typecheck-fast`
- `make test`
- `make test-fast`
- `make test-unit`
- `make test-integration`
- `make test-cov`
- `make precommit`
- `make dev`
- `make mcp-serve`
- `make docker-build`
- `make docker-up`
- `make docker-down`

First-time setup installs the git hooks once:

```bash
make install
uv run pre-commit install
```

## Coding Standards

- Use `uv` for dependency management; do not use direct `pip` installs.
- Use modern Python typing: `list[str]`, `dict[str, int]`, `str | None`.
- Format and lint Python with Ruff.
- Type check with mypy targeting Python 3.12 (strict mode).
- Keep FastAPI route behavior covered by route tests and service behavior
  covered by unit tests.
- Use `respx` to mock outbound httpx calls in tests.

## File Size Discipline

Hard cap: **600 lines per Python module** in `gtex_link/`. Enforced by
`make lint-loc`, which is wired into `make ci-local`. Tests are exempt.

Why: large modules concentrate complexity, slow static analysis, and make
LLM-assisted changes riskier. When a file approaches 500 lines, plan a cohesive
split before adding more behavior.

How:

- New files MUST stay under 600 lines.
- No current source file needs an allowlist.
- If a future file must be grandfathered, add `.loc-allowlist` with
  `<repo-relative path>:<ceiling LOC>` and document the split plan.
- Prefer cohesive splits by responsibility, not random partitioning.

## Testing Notes

- `make test` is the fast default.
- `make test-fast` runs in parallel via pytest-xdist.
- `make test-cov` runs coverage; gate is 90%.
- `make ci-local` runs formatting, linting, file-size checks, type checking, and tests.
- Treat failing checks as real issues unless you have clear evidence otherwise.

## GTEx Domain Notes

- Public API: `https://gtexportal.org/api/v2/` (no auth required).
- Rate-limited to 5 req/s by default; respect the token-bucket limiter.
- Use GENCODE IDs over gene symbols when possible.
- Standard test data: genes BRCA1/BRCA2/TP53/CFH/APOE; tissues
  Muscle_Skeletal/Whole_Blood/Brain_Cortex/Liver; dataset `gtex_v8`.
- Endpoint catalog: `docs/README.md` and `docs/api_v2_*.md`.
