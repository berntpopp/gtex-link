# Post-Sync Python Stack and Agent Modernization Design

> Historical record — **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

## Context

GTEx-Link was synced with `origin/main` on 2026-05-25. The remote branch already
contains the main foundation modernization and observability work:

- `hatchling` build backend and Python `>=3.12`.
- `uv.lock` and `[dependency-groups].dev`.
- `Makefile` with `uv`-based install, lock, lint, typecheck, test, Docker, and
  MCP targets.
- Root `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`.
- GitHub workflow files and Dependabot config.
- `asgi-correlation-id` and `prometheus-client` wired through
  `gtex_link/observability/`.
- Existing phase plans under `docs/superpowers/plans/`, including Phase 3 for
  MCP facade and transport unification.

This spec replaces the pre-sync modernization scope. It focuses only on the
remaining deltas needed to bring the current codebase closer to
`../pubtator-link` and `../genereviews-link` without duplicating completed work.

## Goals

- Keep the completed Phase 1 and Phase 2 modernization from `origin/main`.
- Tighten remaining stack and agent workflow gaps against the sibling projects.
- Preserve existing compatibility for `gtex-mcp` while adding the sibling-style
  `gtex-link-mcp` script alias.
- Update stale README commands so they match the current `Makefile`.
- Add file-size discipline (`make lint-loc`) without an initial allowlist,
  because current source files are all below 600 lines.
- Carry forward the approved Phase 3 direction: explicit MCP facade and unified
  transport through `server.py --transport`.

## Non-Goals

- Re-implement Phase 1 foundation work that already landed.
- Re-implement Phase 2 observability work that already landed.
- Remove `asgi-correlation-id`; it is now wired into runtime middleware and
  logging context.
- Add new GTEx domain endpoints or change REST route behavior.
- Add Postgres, embeddings, corpus ingestion, RAG, or benchmark suites.
- Rewrite GitHub workflows in this pass; workflow files already exist.

## Current Baseline

The synced repository currently has:

- `pyproject.toml` on `hatchling`, Python `>=3.12`, modern bounded deps, and
  `uv.lock`.
- Runtime deps include `asgi-correlation-id` and `prometheus-client`, both used
  by `gtex_link/observability/`.
- `python-multipart` is absent.
- `Makefile` exists but does not yet include `lint-loc`.
- `AGENTS.md` exists but does not yet document file-size discipline.
- `.gitattributes` is already strengthened for LF-sensitive file types.
- `.python-version`, `.editorconfig`, `scripts/check_file_size.py`, and
  `.loc-allowlist` are absent.
- `mcp_server_simple.py` is absent.
- `mcp_http_server.py` still exists and is covered by the existing Phase 3
  plan for removal.
- `README.md` contains stale commands such as `make dev-setup`, `make server`,
  `make check-all`, and `make mcp`, which do not exist in the current
  `Makefile`.

## Packaging and Tooling Delta

Keep the current dependency baseline, including `asgi-correlation-id` and
`prometheus-client`.

Update `pyproject.toml` only for residual parity:

- Add `gtex-link-mcp = "mcp_server:main"` while retaining
  `gtex-mcp = "mcp_server:main"`.
- Expand mypy missing-import overrides to match actual framework dependencies
  used by the package:
  - `async_lru.*`
  - `structlog.*`
  - `mcp.*`
  - `fastmcp.*`
  - `fastapi.*`
  - `pydantic.*`
  - `pydantic_settings.*`
  - `httpx.*`
  - `uvicorn.*`
  - `asgi_correlation_id.*`
  - `prometheus_client.*`
- Remove mandatory coverage flags from default pytest `addopts` so `make test`
  is a fast test command like the sibling projects.
- Move the coverage gate to `[tool.coverage.report]` with `fail_under = 90`,
  preserving the synced repository's documented gate while avoiding coverage
  cost on every pytest run.
- Remove global `filterwarnings = ["error", ...]` from pytest config; warnings
  should be handled as targeted cleanup, not as incidental blockers during
  dependency modernization.

## Makefile and Repository Hygiene Delta

Add file-size discipline matching the sibling projects:

- Add `scripts/check_file_size.py`.
- Add `lint-loc` to `.PHONY`.
- Add `make lint-loc` target.
- Include `lint-loc` in `make ci-local`.
- Do not create `.loc-allowlist` initially. Current largest non-test source
  file is `gtex_link/api/client.py` at 499 lines, below the 600-line cap.

Add missing root ergonomics:

- `.python-version` with `3.12`.
- `.editorconfig` matching the sibling repositories.

## Agent Documentation Delta

Update `AGENTS.md`:

- Add `make lint-loc` to focused commands.
- State that `make ci-local` includes file-size enforcement.
- Add the 600-line source module cap for `gtex_link/`, `server.py`,
  `mcp_server.py`, and `mcp_http_server.py` while it remains.
- Keep the existing `GEMINI.md` and `CLAUDE.md` pointers lean.

## README Delta

Update README install, usage, MCP, development, testing, and code quality
sections to use current commands:

- `make install`
- `make dev`
- `make mcp-serve`
- `make mcp-serve-http`
- `make ci-local`
- `make test`, `make test-fast`, `make test-cov`
- `make format`, `make lint`, `make typecheck`
- `uv run gtex-link ...`
- `uv run gtex-link-mcp`
- `uv run gtex-mcp` as a compatibility alias

Remove or replace stale references to `make dev-setup`, `make server`,
`make check-all`, and `make mcp`.

## MCP and Transport Direction

Do not duplicate the existing Phase 3 plan. The active architecture direction
remains:

- Create an explicit `gtex_link/mcp/` facade.
- Make `app.py` a pure FastAPI factory.
- Use `server.py --transport {unified,http,stdio}`.
- Keep `mcp_server.py` as a thin stdio compatibility entrypoint.
- Delete `mcp_http_server.py` once unified transport lands.

The residual stack plan may harden `mcp_server.py` for stdout safety only if it
does not conflict with Phase 3. Full facade implementation belongs to the Phase
3 execution plan.

## Verification

Run after implementation:

1. `uv lock`
2. `make format-check`
3. `make lint`
4. `make lint-loc`
5. `make typecheck`
6. `make test`
7. `make ci-local`

If any check fails due to pre-existing unrelated debt, the handoff must include
the exact command and failure.
