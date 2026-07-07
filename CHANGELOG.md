# Changelog

All notable changes to GTEx-Link are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.3] - 2026-07-07

### Security (PII in logs)

- **Variant coordinates and gene/transcript identifiers no longer logged.**
  Closed the remaining PII-in-logs leak (GDPR Art. 9) that the 2.0.2 pass scoped
  out: the service-layer variant lookups (`_get_variants_impl`,
  `_get_variants_by_location_impl`) and the gene/transcript/expression request
  diagnostics spread the raw request into logs via `**params.model_dump()`,
  emitting variant coordinates (chrom/pos/ref/alt) and gene/GENCODE identifiers.
  These sites now emit only non-identifying metadata (dataset/tissue enums, sort
  fields, page counts, and identifier-list counts) at both the service and route
  layers. Added sentinel guards for each anchor.

## [2.0.2] - 2026-07-07

### Security (inbound-boundary hardening)

- **CORS credentials off by default.** `cors_allow_credentials` now defaults to
  `False` (the backend is unauthenticated and holds no cookies/session), and a
  startup guard rejects the insecure `allow_credentials=True` + wildcard `*`
  origin combination rather than silently misconfiguring. The dev compose no
  longer sets credentials on.
- **Base `docker-compose.yml` loopback-bound.** The base compose publishes the
  host port on `127.0.0.1` only, so copying it to a server never exposes the
  unauthenticated backend on the public IP (Docker otherwise binds `0.0.0.0` and
  bypasses the host firewall). Production reaches the backend only via the
  router / reverse proxy.
- **No PII in logs.** Stopped logging free-text gene-search queries, subject and
  sample identifiers, and the full upstream URL (scheme + host). Request
  diagnostics now retain only the request path plus non-identifying metadata.
  Added route-, service-, and client-level sentinel guards.

## [2.0.1] - 2026-06-29

### Security (Container & Deployment Hardening Standard v1)

- Pinned the `python:3.14-slim` base image by digest, added a `container-security`
  CI workflow (Trivy scan + CycloneDX SBOM), and brought the base
  `docker-compose.yml` to hardening parity with the prod/npm overlays
  (`read_only`, tmpfs, `cap_drop: ALL`, `no-new-privileges`, `init`, pids/mem/cpu);
  the prod overlay now inherits those controls from the base.

## [2.0.0] - 2026-06-16

### Changed (BREAKING — GeneFoundry Logging & CLI Standard v1)

GTEx-Link now conforms to the fleet-wide **GeneFoundry Logging & CLI Standard
v1**. This is a CLI/transport front-end change only: the **MCP tool surface,
services, and `/api/health` / `/mcp` endpoints are unchanged**, so the
`genefoundry-router` gateway is unaffected.

- **CLI migrated from `argparse` to `typer`.** `gtex_link/cli.py` is now a
  single `typer.Typer(no_args_is_help=True)` app with `rich` output exposing
  the standard commands: `serve`, `config [--validate]`, `health [--url]`,
  `cache stats|clear`, and `version`. The server always boots via
  `gtex-link serve` — there is **no bare-serve**.
- `serve` options: `--transport {unified,http}` (default `unified`), `--host`,
  `--port`, `--mcp-path`, `--log-level`, `--disable-docs`, `--dev`.
- **Single console script.** `pyproject.toml` now declares only
  `gtex-link = "gtex_link.cli:app"`. The previous `gtex-link` (argparse `main`),
  `gtex-link-mcp`, and `gtex-mcp` entry points are **removed** with no aliases.
- **Root entry scripts deleted.** `server.py` and `mcp_server.py` are gone;
  `python -m gtex_link` now delegates to the typer app.
- **stdio transport removed.** The `stdio` transport value, the
  `UnifiedServerManager.start_stdio_server` / `_configure_stdio_environment`
  methods, and all stdio references in config, Docker, Makefile, and docs are
  removed. Streamable HTTP only.
- Docker `CMD`, all `docker-compose*.yml` commands, and the `make dev` / new
  `make serve` targets invoke `gtex-link serve …`.

### Fixed

- Version reporting is now sourced from `gtex_link.__version__` in `app.py`,
  the FastAPI app version, and the `/api/health` / `/api/version` responses
  (previously hardcoded `1.0.0`).

### Confirmed

- `gtex_link/logging_config.py` remains on the structlog canon (contextvars +
  log level + ISO timestamp + stack-info + exc-info + static fields, JSON in
  prod / console in dev, `asgi-correlation-id` binding). No regression.

## [1.0.0] - 2026-06-15

### Changed (BREAKING — GeneFoundry Tool-Naming Standard v1)

GTEx-Link now conforms to the GeneFoundry Tool-Naming & Normalization Standard
v1 so it composes cleanly behind the `genefoundry-router` MCP gateway, which
mounts this server under the **`gtex`** namespace (leaf tool `get_gene_information`
surfaces at the gateway as `gtex_get_gene_information`). There are **no
deprecation aliases** — update callers directly.

**Renamed tools:**

- `search_gtex_genes` → `search_genes`. The embedded `gtex` source token was
  redundant under the gateway namespace (it produced the double-prefixed
  `gtex_search_gtex_genes`). Payload and behaviour are unchanged.

The `search` / `fetch` deep-research pair (OpenAI deep-research / Apps SDK
contract) is **kept verbatim** as a documented exception to the canonical-verb
rule.

**Renamed arguments (fleet canon — applies to all paginated tools):**

- `page` → `offset`, `page_size` → `limit` on `search_genes`,
  `get_transcript_information`, `get_median_expression_levels`,
  `get_individual_expression_data`, and `get_top_expressed_genes_by_tissue`.
  `offset` is a zero-based row offset (`page = offset // limit`); `limit` is the
  page size. Defaults are unchanged.

### Added

- README documents the canonical gateway **namespace token** `gtex` and the
  full, refreshed MCP tool list (the previous list named a non-existent
  `get_expression_qtl_associations` and omitted five real tools).
- Domain `tags` on `get_server_capabilities` (`meta`, `discovery`).
- CI guard `tests/unit/test_tool_names.py`: every registered tool matches
  `^[a-z0-9_]{1,50}$`, starts with a canonical verb (with the `search`/`fetch`
  deep-research allowlist), and does not self-prefix the `gtex` namespace token.

### Fixed

- Reconciled version drift: the FastAPI app, `/api/health`, and `/api/version`
  previously reported stale `0.2.0` / `0.1.0` strings; all now report the
  package version (`1.0.0`).

## [Unreleased]

### Fixed (MCP surface hardening)

- `get_gene_information` now returns a structured `not_found` error for unknown
  genes instead of a silent `success: true` with an empty `data` list.
- `get_median_expression_levels` returns `not_found` (with a GENCODE-version
  hint for non-`gtex_v8` datasets) instead of silently succeeding with no rows,
  closing the `gtex_v10` silent-empty trap.
- `get_transcript_information` and `get_individual_expression_data` now return
  `not_found` (with the offending GENCODE ID and a resolution hint) instead of
  a silent `success: true` empty `data` list, extending the no-silent-false-
  negative contract across the whole tool surface.
- Invalid tissue filters on `get_median_expression_levels` and
  `get_individual_expression_data` now raise the same short `invalid_input`
  message as `get_top_expressed_genes_by_tissue` instead of dumping the full
  54-tissue enum twice (shared `ensure_valid_tissue` helper).
- Compact median output no longer emits always-null `ontologyId`/`spread` keys
  (honoring the documented "tissue/median/n only" contract).
- Median and spread `min`/`max` values are rounded to 4 decimals, removing
  floating-point noise like `484.38300000000004`.

### Added (MCP surface hardening)

- `get_median_expression_levels` `tissue_site_detail_id` accepts a list of
  tissues for a compact multi-tissue comparison (filtered client-side).
- `get_individual_expression_data` rows now carry `n` (sample count); the
  per-sample vector is documented as unlabeled and in upstream order.
- `get_top_expressed_genes_by_tissue` emits `_meta.next_commands` pointing at
  `get_median_expression_levels` for the top gene.
- `not_found` now maps to the `reformulate_input` recovery action.

### Changed (Dependency maintenance)

- Consolidated the open Dependabot updates into a single change set:
  - Runtime: `uvicorn[standard]` 0.48 → 0.49, `structlog` 25.5 → 26.1,
    `typer` 0.25.1 → 0.26.7, `mcp[cli]` 1.27.1 → 1.27.2,
    `fastmcp` 3.3.1 → 3.4.2, `asgi-correlation-id` 4.3 → 5.0.
  - Dev/tooling: `pytest-asyncio` 1.3 → 1.4, `ruff` 0.15.14 → 0.15.16.
  - CI actions: `actions/checkout` 6.0.2 → 6.0.3,
    `astral-sh/setup-uv` 7.6.0 → 8.2.0.
  - Validated against `make ci-local` (format, lint, file-size, mypy strict,
    360 tests) and app/MCP boot smoke checks after the `structlog` 26 and
    `asgi-correlation-id` 5 major bumps.

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
