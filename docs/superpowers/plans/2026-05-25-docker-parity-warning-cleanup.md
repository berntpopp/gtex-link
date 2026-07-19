# Docker Parity and Warning Cleanup Implementation Plan

> Historical record — **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring GTEx-Link Docker configuration closer to the sibling repositories while using non-standard host ports for local development and removing pytest warning debt.

**Architecture:** Keep current GTEx-Link runtime entrypoints and MCP compatibility scripts. Modernize Docker build/deployment hygiene, make host port publication configurable with GTEx-specific defaults, and fix warning root causes in imports and tests.

**Tech Stack:** Python 3.12, uv, Docker Compose v2, FastAPI, FastMCP, pytest, Ruff, mypy.

---

## File Structure

**Create:**
- `docker/gunicorn_conf.py` - optional production Gunicorn configuration matching sibling repo conventions.

**Modify:**
- `docker/Dockerfile` - modern multi-stage uv build with non-root runtime user and minimal copy surface.
- `docker/docker-compose.yml` - remove obsolete Compose version and publish API on `${GTEX_LINK_HOST_PORT:-8020}`.
- `docker/docker-compose.mcp.yml` - publish MCP on `${GTEX_LINK_MCP_HOST_PORT:-8021}`.
- `docker/docker-compose.prod.yml` - add production hardening and reset host ports for overlay/NPM use.
- `docker/docker-compose.npm.yml` - keep dual API/MCP services, add hardening and configurable NPM network.
- `.dockerignore` - align build-context hygiene with sibling projects.
- `docker/README.md` - document Docker usage and non-standard host ports.
- `Makefile` - update Docker config validation target if compose layering changes.
- `gtex_link/app.py` - switch FastMCP import to non-deprecated provider path.
- `tests/unit/test_caching.py` - rename Pydantic helper model so pytest does not collect it.
- `tests/unit/test_cli.py` - avoid leaking unawaited coroutines when `asyncio.run` is patched.
- `tests/conftest.py` and/or `tests/unit/test_gtex_service.py` - use synchronous logger mocks and concrete client return values for logger coverage.

## Task 1: Prove Current Failures

- [ ] Run `uv run pytest tests -q -W error` and confirm warning failures.
- [ ] Run a Compose config assertion proving API host port is not `${GTEX_LINK_HOST_PORT:-8020}` and MCP host port is not `${GTEX_LINK_MCP_HOST_PORT:-8021}`.

## Task 2: Clean Pytest Warning Root Causes

- [ ] Update FastMCP import to `fastmcp.server.providers.openapi`.
- [ ] Rename `TestModel` helper in caching tests.
- [ ] Patch CLI tests so `asyncio.run` closes coroutine arguments and returns the expected sentinel values.
- [ ] Replace swallowed service logger coverage calls with concrete mocked client responses.
- [ ] Verify `uv run pytest tests -q -W error`.
- [ ] Commit as `test: eliminate pytest warning debt`.

## Task 3: Modernize Docker Parity and Ports

- [ ] Modernize `docker/Dockerfile` while preserving existing entrypoints.
- [ ] Add `docker/gunicorn_conf.py`.
- [ ] Remove obsolete Compose `version`.
- [ ] Set default API host port to `${GTEX_LINK_HOST_PORT:-8020}:8000`.
- [ ] Set default MCP host port to `${GTEX_LINK_MCP_HOST_PORT:-8021}:8001`.
- [ ] Harden production/NPM overlays with non-root, read-only, tmpfs, cap drops, pids limit, init, and log rotation where supported.
- [ ] Refresh `.dockerignore`, `docker/README.md`, and Docker Make targets.
- [ ] Verify `docker compose ... config` for base, prod, MCP, and NPM stacks.
- [ ] Commit as `chore: modernize docker deployment parity`.

## Task 4: Final Verification

- [ ] Run `uv lock`.
- [ ] Run `make format-check`.
- [ ] Run `make lint`.
- [ ] Run `make lint-loc`.
- [ ] Run `make typecheck`.
- [ ] Run `make test`.
- [ ] Run `make ci-local`.
- [ ] Run Docker config checks.
