# GTEx-Link Modernization — Design Spec

> Historical record — **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

**Date:** 2026-05-11
**Status:** Approved (pending user spec review)
**Owner:** Bernt Popp
**Reference:** Mirrors patterns from `../pubtator-link` (sibling repo) where applicable.

## 1. Goal

Bring `gtex-link` up to the same stack baseline, agent ergonomics, CI maturity, observability, and MCP architecture as `../pubtator-link`, while keeping the project's narrower scope (GTEx Portal v2 client; no review/RAG/postgres layer). Modernize tooling and dependencies, restructure agent files, and replace the current `FastMCP.from_fastapi` auto-generation with an explicit facade-based MCP layer.

## 2. Non-goals

- Expanding FastAPI route coverage to additional GTEx Portal categories (association/dataset/biobank/histology/GWAS). Treated as a follow-on milestone.
- Adding postgres, RAG, or review-index features from pubtator-link.
- Introducing benchmarks or evaluation suites.
- Setting up OpenTelemetry tracing (Prometheus + correlation IDs is sufficient).
- Publishing a docs site (mkdocs is dropped; revisit if needed later).
- GitHub branch-protection or registry-push configuration (out of repo scope).

## 3. Sequencing

Three sequenced phases under one milestone. Each phase is independently shippable and reviewable.

1. **Phase 1 — Foundation.** Stack/build/tooling/CI/agent files. No end-user behavior change.
2. **Phase 2 — Observability & tests.** Correlation IDs, Prometheus metrics, respx, pytest-xdist. No API/MCP contract change.
3. **Phase 3 — MCP facade & transport unification.** New `gtex_link/mcp/` package, unified `server.py --transport`, deleted `mcp_http_server.py`, Docker compose collapse. MCP tool names preserved 1:1; descriptions rewritten.

## 4. Target architecture

```
gtex-link/
├── AGENTS.md                # Source of truth for agentic tools (new)
├── CLAUDE.md                # Thin pointer @AGENTS.md (rewritten, ~15 lines)
├── GEMINI.md                # Thin pointer mirroring CLAUDE.md (new)
├── CHANGELOG.md             # Keep-a-Changelog format (new)
├── Makefile                 # Rewritten: ci-local, typecheck-fast, test-fast, format-check
├── pyproject.toml           # hatchling backend, Python 3.12+, modern deps
├── server.py                # Unified entry: --transport {unified,http,stdio}
├── mcp_server.py            # Thin stdio entry for Claude Desktop
├── (mcp_http_server.py removed)
├── .github/
│   ├── workflows/{ci,security,release,docker}.yml
│   ├── dependabot.yml
│   └── pull_request_template.md
├── .claude/skills/
│   ├── fastapi-route-change/
│   ├── mcp-tool-change/
│   ├── ci-failure-triage/
│   ├── release-readiness/
│   └── gtex-api-endpoint-add/
├── docker/                  # Unchanged structure; compose collapsed to single service in phase 3
└── gtex_link/
    ├── app.py               # Pure FastAPI factory; no MCP code
    ├── __main__.py          # `python -m gtex_link` -> server.py --transport unified
    ├── config.py
    ├── cli.py
    ├── logging_config.py
    ├── exceptions.py
    ├── server_manager.py    # UnifiedServerManager (lifecycle for all transports)
    ├── api/
    │   ├── client.py
    │   ├── retry.py         # NEW: retry abstraction extracted
    │   └── routes/
    ├── models/
    ├── services/gtex_service.py
    ├── observability/       # NEW
    │   ├── correlation.py
    │   └── metrics.py
    ├── utils/caching.py
    └── mcp/                 # NEW package — replaces FastMCP.from_fastapi
        ├── facade.py
        ├── profiles.py
        ├── resources.py
        ├── errors.py
        ├── output_validation.py
        ├── service_adapters.py
        └── tools/
            ├── search_fetch.py
            ├── reference.py
            └── expression.py
```

## 5. pyproject.toml baseline

Mirrors `../pubtator-link` version constraints to keep the two repos in lockstep.

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gtex-link"
version = "0.2.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0,<1.0.0",
    "uvicorn[standard]>=0.46.0,<1.0.0",
    "pydantic>=2.11.0,<3.0.0",
    "pydantic-settings>=2.6.0,<3.0.0",
    "httpx>=0.28.0,<1.0.0",
    "async-lru>=2.0.4,<3.0.0",
    "structlog>=24.4.0,<26.0.0",
    "orjson>=3.10.0,<4.0.0",
    "rich>=15.0.0,<16.0.0",
    "typer>=0.25.1,<1.0.0",
    "mcp[cli]>=1.27.0,<2.0.0",
    "fastmcp>=3.2.0,<4.0.0",
    "gunicorn>=25.3.0,<26.0.0",
    "asgi-correlation-id>=4.3.0,<5.0.0",
    "prometheus-client>=0.21.0,<1.0.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.3,<10.0.0",
    "pytest-asyncio>=1.3.0,<2.0.0",
    "pytest-cov>=6.0.0,<8.0.0",
    "pytest-mock>=3.14.0,<4.0.0",
    "pytest-xdist>=3.6.0,<4.0.0",
    "httpx>=0.28.0,<1.0.0",
    "respx>=0.22.0,<1.0.0",
    "ruff>=0.8.0,<1.0.0",
    "mypy>=1.14.0,<2.0.0",
    "pre-commit>=4.0.0,<5.0.0",
]

[project.scripts]
gtex-link = "gtex_link.cli:main"
gtex-mcp  = "mcp_server:main"
```

**Removed deps:** `bandit` (ruff S rules cover it), `python-multipart` (no file uploads), `opentelemetry-*` (unused), `mkdocs*` (no docs site deployed).

**Added deps:** `respx`, `pytest-xdist`, `asgi-correlation-id`, `prometheus-client`. Bumped `mcp` + `fastmcp` to current majors.

**Tooling config:**
- Ruff: `target-version = "py312"`, extend-select adds `N`, `S`, `T20`, `RUF`. `line-length = 100`, double quotes.
- Mypy: `python_version = "3.12"`, strict; override list trimmed to `async_lru`, `mcp`, `fastmcp`, `structlog`.
- Pytest: keep `filterwarnings = ["error", ...]`, `asyncio_mode = "auto"`, coverage gate stays at 90%.

## 6. Agent files

**`AGENTS.md`** (new, source of truth): project pitch, primary areas, source-of-truth rules, working rules, required `make ci-local` before completion, common Make targets, coding standards (uv not pip, modern typing, ruff, mypy 3.12), MCP guidance (research-use only; no destructive cache ops), testing notes.

**`CLAUDE.md`** (rewritten, ~15 lines): `@AGENTS.md` pointer + Claude-specific notes (skills list, ci-local reminder).

**`GEMINI.md`** (new, mirrors `CLAUDE.md`).

**Content moved out of current 16K-line CLAUDE.md:**
- Architecture & component details → `docs/architecture.md` (new)
- 55-endpoint catalogue → already in `docs/README.md`; delete duplicate from CLAUDE.md
- GTEx data standards & test conventions → `docs/conventions.md` (new)
- Performance benchmarks ("~50ms cold, ~5ms warm") → deleted (unmeasured, aspirational)

## 7. Makefile rewrite

Single canonical "is it ready?" target: `make ci-local` = `format-check + lint-ci + typecheck-fast + test-fast`.

Targets:
- **Deps:** `install`, `sync`, `lock`, `upgrade`
- **Quality:** `format`, `format-check`, `lint`, `lint-ci`, `lint-fix`, `typecheck`, `typecheck-fast` (dmypy with crash-fallback), `typecheck-stop`, `typecheck-fresh`
- **Tests:** `test`, `test-fast` (xdist), `test-unit`, `test-integration`, `test-cov`, `test-all`
- **Aggregate:** `check` (format + lint), `ci-local`, `precommit`
- **Dev:** `dev` (unified), `mcp-serve` (stdio), `mcp-serve-http` (unified — alias for clarity)
- **Docker:** `docker-build`, `docker-up`, `docker-down`, `docker-logs`, `docker-prod-config`, `docker-npm-config`
- **Misc:** `clean`, `setup` (keeps existing `setup_gtex_link.sh` invocation)

Consolidated away: today's `docker-dev`, `docker-dev-bg`, `docker-mcp`, `docker-npm-bg`, `docker-clean`, `docker-stop`, `docker-logs-dev`, `docker-logs-npm`. Anything still needed moves to `scripts/`.

Compose detection (`docker compose` vs `docker-compose`) copied from pubtator-link.

Windows note: `typecheck-fast` shell script requires bash (Git Bash / WSL), not PowerShell. This matches how the user already invokes `make`.

## 8. CI / GitHub config

**Workflows** (all pin actions by SHA, matching pubtator-link's hardening):

- `ci.yml` — PR + push to main: checkout, setup-python 3.12, setup-uv (cached, pinned), `uv sync --group dev --frozen`, `make ci-local`, `make test-cov`. Concurrency cancels in-progress.
- `security.yml` — PR + push to main + weekly cron: CodeQL Python analyze (repo is public), Dependency Review on PRs (continue-on-error).
- `docker.yml` — PR + push: validate `docker-prod-config`, validate `docker-npm-config`, build production Dockerfile (no push).
- `release.yml` — `v*` tag push: full CI checks, validate compose configs, build release Docker image (no auto-push initially).

**`dependabot.yml`:** uv group (or pip fallback per current Dependabot capability), GitHub Actions weekly, Docker weekly for `docker/`.

**`pull_request_template.md`:** summary, `make ci-local` checkbox, tests added/updated checkbox, breaking-change note.

## 9. Repo-local skills (`.claude/skills/`)

Five SKILL.md skills, each a focused workflow:

1. **`fastapi-route-change/`** — add/modify a FastAPI route: request model, response model, route registration, test, OpenAPI snapshot.
2. **`mcp-tool-change/`** — add/rename an MCP tool: register in `gtex_link/mcp/tools/<category>.py`, add to profile, tune description, test, update docs.
3. **`ci-failure-triage/`** — classify (format/lint/typecheck/test/flaky), reproduce locally, fix at root cause, no bypass.
4. **`release-readiness/`** — bump version, update CHANGELOG, all green on main, tag `vX.Y.Z`, monitor release workflow.
5. **`gtex-api-endpoint-add/`** — wire a new upstream GTEx endpoint: read OpenAPI entry, add request/response models, service method with caching, route, respx tests, MCP exposure decision.

## 10. Test infrastructure

- **Add `respx`** for HTTP mocking; migrate route-by-route from hand-rolled httpx mocks in `tests/conftest.py`; keep old fixtures alongside until all routes migrated, then delete.
- **Add `pytest-xdist`**; `make test-fast` uses `-n auto`. Integration tests stay serial via the `integration` marker.
- **Keep `filterwarnings = ["error", ...]`**. Extend ignore list narrowly for any unavoidable fastmcp 3.x noise.
- **Coverage gate stays at 90%** (current is 92.7% per recent commits).
- **New test directories:**
  - `tests/test_mcp/` — facade construction, profile selection, every registered tool, error masking, output validation.
  - `tests/test_observability/` — correlation ID propagation, `/metrics` endpoint behavior.
- **Bandit-related config removed** with the dep.

## 11. Observability layer

New `gtex_link/observability/`.

**Correlation IDs** via `asgi-correlation-id`:
- `CorrelationIdMiddleware` added after CORS in `app.py` factory.
- Generates UUID if no inbound `X-Request-ID`; echoes on responses.
- Structlog processor binds `correlation_id` from the contextvar.
- `GTExClient` propagates inbound correlation ID as `X-Request-ID` on outbound calls.

**Prometheus metrics** via `prometheus-client`:
- Collectors:
  - `gtex_http_requests_total{method,route,status}`
  - `gtex_http_request_duration_seconds{method,route}` (histogram)
  - `gtex_upstream_requests_total{endpoint,status}`
  - `gtex_upstream_request_duration_seconds{endpoint}`
  - `gtex_cache_hits_total{cache}` / `gtex_cache_misses_total{cache}`
  - `gtex_rate_limit_waits_total` / `gtex_rate_limit_wait_seconds`
  - `gtex_mcp_tool_calls_total{tool,status}`
- ASGI middleware for HTTP metrics; client/service code increments upstream and cache/rate-limit counters at call sites.
- New `GET /metrics` exposed via FastAPI; excluded from MCP route map; excluded from request-timing histogram.

**Structlog tuning:**
- Existing JSON/console toggle stays.
- Add `correlation_id`, `service=gtex-link`, `version=__version__` to processor chain.
- In stdio MCP mode, force all log output to stderr (pattern lifted from pubtator-link's `mcp_server.py`).

## 12. MCP facade (`gtex_link/mcp/`)

Replaces `FastMCP.from_fastapi` with explicit registration.

**`facade.py`** — `create_gtex_mcp(profile)` builds a `FastMCP(name="gtex-link", mask_error_details=True, instructions=...)` with explicit `register_*` calls per tool category, plus `install_output_validation_error_handler`.

**`profiles.py`** — `full` (every tool) and `lite` (`search` + `fetch` + `search_gtex_genes` + `get_gene_information` + `get_median_expression_levels`). Selected via `GTEX_LINK_MCP_PROFILE` env var; default `full`.

**`tools/reference.py`** — explicit registration of `search_gtex_genes`, `get_gene_information`, `get_transcript_information`. Each tool is a typed function with a hand-tuned description targeted at AI clients.

**`tools/expression.py`** — explicit registration of `get_median_expression_levels`, `get_individual_expression_data`, `get_top_expressed_genes_by_tissue`.

**`tools/search_fetch.py`** — ChatGPT-compatible `search` and `fetch` tools moved out of `app.py`; properly typed and tested.

**`errors.py`** — maps `GTExAPIError`, `RateLimitError`, `ServiceUnavailableError`, `ValidationError` to structured MCP error responses. Combined with `mask_error_details=True`, upstream HTTP detail does not leak.

**`output_validation.py`** — wraps tool returns in Pydantic validation; prevents malformed output.

**`service_adapters.py`** — single instantiation of `GTExService` and `GTExClient` for tools.

**MCP tool names preserved 1:1**: `search`, `fetch`, `search_gtex_genes`, `get_gene_information`, `get_transcript_information`, `get_median_expression_levels`, `get_individual_expression_data`, `get_top_expressed_genes_by_tissue`.

**Pre-phase-3 audit task:** enumerate every MCP tool currently exposed via `FastMCP.from_fastapi` (including any auto-generated tools not in `mcp_custom_names`) to ensure 1:1 preservation. Any "accidental" tools are either explicitly re-registered or documented as removed in `CHANGELOG.md`.

**`app.py` after refactor** — pure FastAPI factory. No MCP imports, no `try/except` around MCP boot. MCP app is built by `server_manager.py` when transport is `unified` or `stdio`.

## 13. Transport unification

**`server.py`** — single argparse entry with `--transport {unified,http,stdio}`, `--host`, `--port`, `--log-level`. ~50 lines. Delegates to `UnifiedServerManager`.

**`gtex_link/server_manager.py`** — `UnifiedServerManager` class:
- `start_unified_server(host, port)` — FastAPI + MCP mounted at `mcp_path`, same port.
- `start_http_only_server(host, port)` — FastAPI only.
- `start_stdio_server()` — FastMCP stdio with full stdout-protection setup (env vars to suppress fastmcp banner, redirect rich/structlog to stderr).
- `shutdown()` — graceful close.

**`mcp_server.py`** — thin stdio entry preserving the `gtex-mcp` console script. Sets env, calls `UnifiedServerManager.start_stdio_server()`.

**`mcp_http_server.py`** — **deleted**. Replaced by `server.py --transport unified` or `--transport http`.

**`gtex_link/__main__.py`** — new; `python -m gtex_link` aliases `server.py --transport unified`.

**Settings:**
- `GTEX_LINK_TRANSPORT` (unified|http|stdio, default `unified`)
- `GTEX_LINK_MCP_PROFILE` (full|lite, default `full`)
- `GTEX_LINK_MCP_PATH` stays `/mcp`
- `GTEX_LINK_MCP_PORT` **removed** (unified mode runs on single port)

**Docker compose collapse** (phase 3): separate `api` and `mcp` services merge to one in `docker-compose.yml`; `docker-compose.npm.yml` upstream simplified accordingly. Existing deployments need redeploy.

## 14. Repo hygiene

**Delete from repo:**
- `coverage.xml` (generated)
- `gtex_link.egg-info/` (gone after hatchling swap)
- `htmlcov/` (pytest-cov output)
- Root-level `PLAN.md` (stale; relocate to `docs/superpowers/specs/archive/2025-07-31-original-plan.md` as history)

**Manual confirmation required before deletion:**
- `.env` is currently checked in. Phase 1 plan must flag this as a step requiring the user to confirm the file holds no secrets before removal. Replaced by `.env.example` / `.env.docker.example` (latter exists).

**`.gitignore` audit:** ensure `coverage.xml`, `htmlcov/`, `*.egg-info/`, `.coverage*`, `dist/`, `build/`, `.dmypy.json` are listed.

**`docs/` reorganization:**
- `docs/api_v2_*.md` — keep (generated catalog).
- `docs/README.md` — keep as catalog index.
- `docs/architecture.md` — new (absorbs CLAUDE.md content).
- `docs/conventions.md` — new (absorbs GTEx data standards).
- `docs/superpowers/specs/` — this spec and future ones.
- `docs/superpowers/plans/` — implementation plans from writing-plans.

**`CHANGELOG.md` 0.2.0 entry** documents every breaking change (see §15).

## 15. Breaking changes (CHANGELOG.md / migration notes)

- Python 3.10 → 3.12 minimum.
- Build backend: setuptools → hatchling.
- Stack version jumps: fastapi 0.110→0.115+, fastmcp 0.2→3.2+, pydantic 2.7→2.11+, pytest 8→9, ruff 0.4→0.8+, mypy 1.10→1.14+.
- `gtex-mcp-http` console script removed (use `gtex-mcp` or `server.py --transport unified`).
- `mcp_http_server.py` removed.
- `GTEX_LINK_MCP_PORT` env var removed.
- Docker: two services (api + mcp) → one (unified).
- MCP layer: auto-generation via `FastMCP.from_fastapi` → explicit facade. **Tool names preserved 1:1; descriptions improved.**
- Deps removed: `bandit`, `mkdocs`, `mkdocs-material`, `mkdocstrings`, `opentelemetry-*`, `python-multipart`.
- Deps added: `respx`, `pytest-xdist`, `asgi-correlation-id`, `prometheus-client`.
- New `/metrics` HTTP endpoint.

## 16. Risks

| Risk | Phase | Mitigation |
|---|---|---|
| fastmcp 0.2 → 3.2 API surface changes | 3 | Tool names preserved 1:1; `tests/test_mcp/` smoke suite per tool; staged behind facade refactor. |
| pytest 8 → 9 / pytest-asyncio deprecations | 1 | Caught on first test run; config tweaks land with pyproject bump. |
| respx migration disrupts test stability | 2 | Route-by-route migration; old fixtures kept until each is replaced. |
| `.env` deletion loses local config | 1 | Manual confirmation step in plan; user reviews before deletion. |
| Docker compose collapse breaks prod | 3 | Documented in changelog; deployment coordination is user's responsibility. |
| Hidden MCP tools removed by facade switch | 3 | Pre-phase-3 audit task enumerates current tools; any losses go into changelog. |
| Windows + bash-only Makefile targets | 1 | `typecheck-fast` requires Git Bash / WSL; user already runs `make` this way. |

## 17. Success criteria

Per phase:

- **Phase 1:** `make ci-local` green on a CI run with the new workflow file; `uv lock` regenerated with new dep set; AGENTS.md/CLAUDE.md/GEMINI.md split done; 5 skill scaffolds present; PR template, dependabot, security/docker/release workflows live.
- **Phase 2:** `/metrics` endpoint exposes all collectors; structured logs include `correlation_id`; respx-driven tests cover every route; `make test-fast` runs in parallel; coverage gate still ≥90%.
- **Phase 3:** All current MCP tool names callable via the new facade; `server.py --transport unified` boots FastAPI + MCP on one port; `mcp_http_server.py` and `GTEX_LINK_MCP_PORT` gone; docker compose runs as single service; CHANGELOG.md 0.2.0 entry merged; version bumped.
