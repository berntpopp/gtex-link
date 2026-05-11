# Changelog

All notable changes to GTEx-Link are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Phase 1 — Foundation)

- `AGENTS.md` as shared source of truth for agentic tools.
- `GEMINI.md` and slimmed `CLAUDE.md` as thin pointers.
- `docs/architecture.md` and `docs/conventions.md` absorbing former CLAUDE.md content.
- `.github/workflows/ci.yml` running `make ci-local` and coverage.
- `.github/workflows/security.yml` with CodeQL and dependency review.
- `.github/workflows/docker.yml` validating compose configs and building images.
- `.github/workflows/release.yml` for tag-triggered validation.
- `.github/dependabot.yml` weekly updates for uv/actions/docker.
- `.github/pull_request_template.md`.
- Five `.claude/skills/` workflows: `fastapi-route-change`, `mcp-tool-change`, `ci-failure-triage`, `release-readiness`, `gtex-api-endpoint-add`.
- `Makefile` `ci-local`, `typecheck-fast`, `format-check`, `lint-ci`, `test-fast`, `test-cov` targets.
- Dev deps: `pytest-xdist`, `respx`.
- Runtime deps: `asgi-correlation-id`, `prometheus-client` (wired up in Phase 2).

### Changed

- Build backend: setuptools → hatchling.
- Python minimum version: 3.10 → 3.12.
- Dependency floors raised to current stable:
  - fastapi 0.110 → 0.115+
  - fastmcp 0.2 → 3.2+
  - pydantic 2.7 → 2.11+
  - pytest 8 → 9+
  - ruff 0.4 → 0.8+
  - mypy 1.10 → 1.14+
  - pre-commit 3.7 → 4.0+
  - structlog 24.1 → 24.4+
  - rich 13 → 15+
  - typer 0.12 → 0.25+
  - mcp 1.0 → 1.27+
  - gunicorn 22 → 25+
- `CLAUDE.md` shrunk from 16K to a thin pointer at `AGENTS.md`.
- `Makefile` rewritten; consolidated docker targets to a canonical set.

### Removed

- Dev/runtime deps: `bandit`, `python-multipart`, `mkdocs`, `mkdocs-material`, `mkdocstrings`, `opentelemetry-*`.
- Tracked `.env` file (replaced by `.env.example`).
- Generated artifacts in repo (`coverage.xml`, `htmlcov/`, `gtex_link.egg-info/`).
- Root-level stale `PLAN.md` (relocated to `docs/superpowers/plans/archive/`).

### Added (Phase 2 — Observability & tests)

- `gtex_link/observability/` package: correlation IDs (asgi-correlation-id), Prometheus collectors, `/metrics` endpoint.
- ASGI middleware: `CorrelationIdMiddleware`, `MetricsMiddleware`.
- Structlog processors: `bind_correlation_id_processor` and `_add_static_fields` injecting `correlation_id`, `service=gtex-link`, `version` into every log event.
- Outbound `X-Request-ID` propagation in `GTExClient` (inbound correlation ID echoed on upstream calls).
- Prometheus collectors: HTTP request count/duration, upstream request count/duration, cache hits/misses, rate-limit waits, MCP tool calls (populated in Phase 3).
- `respx_mock` fixture and `GTEX_BASE` constant in `tests/conftest.py`.
- `tests/test_observability/` covering correlation echo, generated ID, `/metrics` endpoint, request counter, upstream call helper, cache hit/miss helper.
- `.gitattributes` pins `.py`/`.toml`/`.yml`/`.md`/`.json`/`.sh`/`Makefile`/`Dockerfile` to LF in the working tree so `ruff format --check` is stable on Windows checkouts.

### Changed (Phase 2)

- Package and FastAPI version bumped to `0.2.0` (matches pyproject.toml).
- Route, client, and edge-case HTTP-mocking tests migrated from `unittest.mock.patch("httpx.AsyncClient.request", ...)` to `respx` route registrations.
- `make test-fast` runs the suite under `pytest-xdist -n auto`; coverage gate stays at 90%.
- Cache hit/miss metrics emitted at the `CacheManager` decorator layer rather than per-service wrapping, so every cached service method automatically gets a Prometheus label derived from its `key_pattern`.

### Notes

- No external API or MCP tool contract changes. The MCP tool counter is wired but only populated by Phase 3.

### Added (Phase 3 -- MCP facade & transport unification)

- `gtex_link/mcp/` package with explicit tool registration: `facade.py`, `profiles.py`, `resources.py`, `errors.py`, `output_validation.py`, `service_adapters.py`, and per-category tool modules under `tools/` (reference, expression, search/fetch).
- `gtex_link/mcp/profiles.py` with `full` (all tools) and `lite` (read-only research subset) profiles.
- `GTEX_LINK_MCP_PROFILE` env var (default `full`).
- `gtex_link/__main__.py` so `python -m gtex_link` aliases the unified server.
- `UnifiedServerManager` (`gtex_link/server_manager.py`) with `start_unified_server`, `start_http_only_server`, `start_stdio_server`, and graceful shutdown.
- `server.py --transport {unified,http,stdio}` single entry point.

### Changed (Phase 3)

- MCP layer: replaced `FastMCP.from_fastapi` auto-generation with an explicit facade. Tool names preserved 1:1; tool descriptions hand-tuned for AI clients.
- `mcp_server.py` is now a thin stdio entry that delegates to `UnifiedServerManager`.
- `gtex_link/app.py` is a pure FastAPI factory -- MCP code moved out into `gtex_link/mcp/`.
- Docker: `docker/docker-compose.yml` collapsed the `api` + `mcp` services into a single `gtex-link` service. `docker/docker-compose.npm.yml` collapsed to a single `gtex_link` upstream. `docker/docker-compose.dev.yml` no longer mounts the deleted `mcp_http_server.py`.
- `GTEX_LINK_TRANSPORT_MODE` env var renamed to `GTEX_LINK_TRANSPORT` (values: `unified`, `http`, `stdio`).
- `make dev` and `make mcp-serve-http` now invoke `server.py --transport unified` (was: bare `server.py`).

### Removed (Phase 3 -- BREAKING)

- `mcp_http_server.py` deleted. Use `server.py --transport unified` or `--transport http` instead.
- `gtex-mcp-http` console script removed at the architecture level (the script entry was already absent from `pyproject.toml`; the `mcp_http_server.py` entry point it pointed at is now gone too). Use `gtex-mcp` for stdio or `server.py --transport unified` for HTTP.
- `GTEX_LINK_MCP_PORT` env var removed. Unified mode runs on a single port (`GTEX_LINK_PORT`).
- Two-service Docker compose split (api/mcp) removed.
- `docker/docker-compose.mcp.yml` deleted (it only existed to run `mcp_http_server.py`).
- `GTEX_MCP_MEMORY_LIMIT` / `GTEX_MCP_CPU_LIMIT` env vars dropped from `.env.docker.example` (no separate MCP container).
- MCP tool `version_info_api_version_get` removed. This was auto-generated by `FastMCP.from_fastapi` for the `GET /api/version` route and was never explicitly intended as an MCP tool. The version endpoint remains available as a regular HTTP route at `/api/version`. (See `docs/superpowers/plans/archive/2026-05-11-mcp-tool-audit.md` for the full pre-migration tool audit.)
- Obsolete `tests/unit/test_app.py` MCP coverage replaced by dedicated suites under `tests/test_mcp/`.

### Migration notes (Phase 3)

- Anyone running `mcp_http_server.py` or `gtex-mcp-http`: switch to `gtex-mcp` (stdio) or `python server.py --transport unified` (FastAPI + MCP on one port).
- Anyone setting `GTEX_LINK_TRANSPORT_MODE`: rename the env var to `GTEX_LINK_TRANSPORT`.
- Anyone setting `GTEX_LINK_MCP_PORT`: remove the env var; the MCP endpoint is now served on `GTEX_LINK_PORT` at the `GTEX_LINK_MCP_PATH` path (default `/mcp`).
- Deployments using the two-service compose split: redeploy with the new single-service compose; update reverse-proxy upstream from two pools to one.
- Anyone calling the auto-generated `version_info_api_version_get` MCP tool: switch to `GET /api/version` over HTTP, or read version metadata from any other tool response that already includes it.
