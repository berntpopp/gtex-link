# Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring `gtex-link` up to the stack baseline, agent-file shape, CI maturity, and tooling discipline of `../pubtator-link` without changing any runtime behavior.

**Architecture:** Replace setuptools with hatchling. Bump Python minimum to 3.12. Mirror pubtator-link's dependency versions. Split the 16K-line `CLAUDE.md` into `AGENTS.md` (source of truth), thin `CLAUDE.md` and `GEMINI.md` pointers, and `docs/architecture.md` + `docs/conventions.md` for long-form content. Rewrite the `Makefile` around `ci-local`. Add `.github/` workflows (CI, security/CodeQL, docker, release), Dependabot, PR template, and 5 repo-local skills under `.claude/skills/`. Add `CHANGELOG.md`. Clean repo hygiene (delete generated artifacts, audit `.gitignore`, remove checked-in `.env`).

**Tech Stack:** Python 3.12+, uv, hatchling, ruff 0.8+, mypy 1.14+, pytest 9+, pre-commit 4+, GitHub Actions.

---

## File Structure

**Create:**
- `AGENTS.md`
- `GEMINI.md`
- `CHANGELOG.md`
- `docs/architecture.md`
- `docs/conventions.md`
- `docs/superpowers/plans/archive/2025-07-31-original-plan.md` (relocated from root)
- `.github/workflows/ci.yml`
- `.github/workflows/security.yml`
- `.github/workflows/docker.yml`
- `.github/workflows/release.yml`
- `.github/dependabot.yml`
- `.github/pull_request_template.md`
- `.claude/skills/fastapi-route-change/SKILL.md`
- `.claude/skills/mcp-tool-change/SKILL.md`
- `.claude/skills/ci-failure-triage/SKILL.md`
- `.claude/skills/release-readiness/SKILL.md`
- `.claude/skills/gtex-api-endpoint-add/SKILL.md`

**Modify:**
- `pyproject.toml` (full rewrite)
- `Makefile` (full rewrite)
- `CLAUDE.md` (shrink to thin pointer)
- `.pre-commit-config.yaml` (bump versions, add mypy local hook + check-toml/check-json)
- `.gitignore` (add `dist/`, `build/`, `.dmypy.json`; verify others)

**Delete:**
- `coverage.xml`
- `gtex_link.egg-info/`
- `htmlcov/`
- `mcp_http_server.py` (NOTE: this is deferred to Phase 3; do NOT delete here)
- `PLAN.md` (root) — relocated to `docs/superpowers/plans/archive/`
- `.env` (after content audit)

**No runtime code changes in this phase.** `gtex_link/*.py` is not touched.

---

## Task 1: Create a feature branch

**Files:**
- No files modified

- [ ] **Step 1: Create branch from main**

Run:
```bash
git checkout main
git pull origin main
git checkout -b phase-1-foundation
```
Expected: switched to a new branch `phase-1-foundation`.

---

## Task 2: Rewrite `pyproject.toml`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace the entire contents of `pyproject.toml` with the modern baseline**

Open `pyproject.toml` and replace its contents with:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "gtex-link"
version = "0.2.0"
description = "High-performance MCP/API server for GTEx Portal genetic expression database"
readme = "README.md"
license = { text = "MIT" }
authors = [
    { name = "GTEx-Link Development Team", email = "dev@gtex-link.org" },
]
keywords = [
    "gtex", "genomics", "expression", "eqtl", "bioinformatics", "api", "mcp",
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Science/Research",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Typing :: Typed",
]
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

[project.urls]
Homepage = "https://github.com/gtex-link/gtex-link"
Repository = "https://github.com/gtex-link/gtex-link"
"Bug Tracker" = "https://github.com/gtex-link/gtex-link/issues"
Changelog = "https://github.com/gtex-link/gtex-link/blob/main/CHANGELOG.md"

[project.scripts]
gtex-link = "gtex_link.cli:main"
gtex-mcp  = "mcp_server:main"

[tool.hatch.build.targets.wheel]
packages = ["gtex_link"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
extend-select = [
    "E", "W", "F", "I", "N", "UP", "B", "C4", "S", "T20", "SIM", "RUF",
]
ignore = [
    "E501",   # Line too long (handled by formatter)
    "B008",   # FastAPI Query/Depends pattern
    "S101",   # asserts ok in tests (also per-file-ignores)
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "lf"

[tool.ruff.lint.per-file-ignores]
"tests/**/*" = ["S101", "T20"]
"docs/**/*.py" = ["UP035"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
exclude = [
    ".*site-packages.*",
    ".*/venv/.*",
    ".*/\\.venv/.*",
    "htmlcov/.*",
]

[[tool.mypy.overrides]]
module = [
    "async_lru.*",
    "structlog.*",
    "mcp.*",
    "fastmcp.*",
]
ignore_missing_imports = true

[tool.pytest.ini_options]
minversion = "9.0"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=gtex_link",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--cov-fail-under=90",
    "-ra",
]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests",
    "unit: marks tests as unit tests",
    "api: marks tests that require API access",
    "mcp: marks tests that test MCP functionality",
]
filterwarnings = [
    "error",
    "ignore::UserWarning",
    "ignore::DeprecationWarning:httpx.*",
    "ignore::DeprecationWarning:fastmcp.*",
]

[tool.coverage.run]
source = ["gtex_link"]
omit = [
    "tests/*",
    "gtex_link/__main__.py",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod",
]
show_missing = true
skip_covered = false

[tool.coverage.html]
directory = "htmlcov"

[tool.coverage.xml]
output = "coverage.xml"
```

- [ ] **Step 2: Delete `gtex_link.egg-info/` (setuptools artifact)**

Run:
```bash
rm -rf gtex_link.egg-info/
```
Expected: directory removed; nothing to commit (it shouldn't have been tracked, but if it was, `git status` shows the deletion).

- [ ] **Step 3: Regenerate `uv.lock`**

Run:
```bash
uv lock
```
Expected: `uv.lock` updated with new constraints. No errors.

- [ ] **Step 4: Sync the environment**

Run:
```bash
uv sync --group dev
```
Expected: dependencies installed against the new lockfile. If resolution fails, inspect the error and verify all version constraints in `pyproject.toml` are mutually satisfiable.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "build: switch to hatchling and modernize dependencies"
```

---

## Task 3: Update `.pre-commit-config.yaml`

**Files:**
- Modify: `.pre-commit-config.yaml`

- [ ] **Step 1: Replace file contents**

Open `.pre-commit-config.yaml` and replace with:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format

  - repo: local
    hooks:
      - id: mypy
        name: mypy
        entry: uv run mypy gtex_link server.py mcp_server.py
        language: system
        pass_filenames: false
```

- [ ] **Step 2: Reinstall pre-commit hooks**

Run:
```bash
uv run pre-commit install
uv run pre-commit autoupdate --freeze
```
Expected: hooks installed; `autoupdate --freeze` pins repo SHAs alongside tags.

- [ ] **Step 3: Run hooks once against all files**

Run:
```bash
uv run pre-commit run --all-files
```
Expected: most hooks pass; ruff may make small format/lint fixes — that's OK. If mypy fails, capture the output; the next task only commits config, not unrelated code changes.

- [ ] **Step 4: Commit (config + any auto-applied formatting fixes)**

```bash
git add .pre-commit-config.yaml
# Add only auto-formatting changes if any
git add -p   # interactively review and stage only safe whitespace/import-sort changes
git commit -m "build(pre-commit): bump hooks and add mypy/check-toml"
```

If mypy errors remain, they belong to Phase 2/3 fixes — record the error count in the commit message: `Note: mypy reports N errors; addressed in later phases.`

---

## Task 4: Update `.gitignore`

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Append missing entries**

The current `.gitignore` already covers most generated files. Append (idempotent — if a line already exists, leave it):

```
# Hatchling / dist artifacts
dist/
build/

# dmypy daemon state
.dmypy.json

# Local IDE state
.idea/
.vscode/
```

Verify present (add if missing):
```
htmlcov/
coverage.xml
.coverage
*.egg-info/
.mypy_cache/
.ruff_cache/
.pytest_cache/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore(gitignore): cover dist/build and dmypy state"
```

---

## Task 5: Delete generated repo clutter

**Files:**
- Delete: `coverage.xml`
- Delete: `htmlcov/`
- Delete: `gtex_link.egg-info/` (re-verify after Task 2)

- [ ] **Step 1: Remove tracked generated files**

Run:
```bash
git rm -r --cached coverage.xml htmlcov/ 2>/dev/null || true
git rm -r --cached gtex_link.egg-info/ 2>/dev/null || true
rm -rf coverage.xml htmlcov/ gtex_link.egg-info/
```
Expected: removals shown in `git status`. The `--cached` flag handles cases where the artifacts were tracked; the working-tree `rm` covers untracked copies.

- [ ] **Step 2: Verify `.gitignore` covers them (from Task 4)**

Run:
```bash
git check-ignore -v coverage.xml htmlcov/test.html gtex_link.egg-info/PKG-INFO 2>&1 || true
```
Expected: each path matches a `.gitignore` rule.

- [ ] **Step 3: Commit**

```bash
git commit -m "chore: remove generated artifacts from repo"
```

---

## Task 6: Relocate the stale root `PLAN.md`

**Files:**
- Move: `PLAN.md` → `docs/superpowers/plans/archive/2025-07-31-original-plan.md`

- [ ] **Step 1: Create the archive directory and move the file**

Run:
```bash
mkdir -p docs/superpowers/plans/archive
git mv PLAN.md docs/superpowers/plans/archive/2025-07-31-original-plan.md
```
Expected: file relocated. `git status` shows the rename.

- [ ] **Step 2: Commit**

```bash
git commit -m "docs: archive original PLAN.md under superpowers/plans/archive/"
```

---

## Task 7: Audit and remove the checked-in `.env`

**Files:**
- Delete: `.env` (after content review)

- [ ] **Step 1: Verify file contents are non-sensitive**

Run:
```bash
cat .env
```
Expected output:
```
# uv performance optimization for WSL2/NTFS
UV_LINK_MODE=copy
UV_CACHE_DIR=/tmp/uv-cache
```

If output matches (only uv perf settings), proceed. If there are credentials or anything else, **STOP** and surface to the user before deleting.

- [ ] **Step 2: Append the same content to `.env.example` (create if missing)**

Open or create `.env.example` and ensure it contains:
```
# Example environment overrides for GTEx-Link.
# Copy to .env and adjust as needed.

# uv performance optimization for WSL2/NTFS
# UV_LINK_MODE=copy
# UV_CACHE_DIR=/tmp/uv-cache

# Server
# GTEX_LINK_HOST=127.0.0.1
# GTEX_LINK_PORT=8000
# GTEX_LINK_LOG_LEVEL=INFO
# GTEX_LINK_LOG_FORMAT=console

# API
# GTEX_LINK_API_RATE_LIMIT_PER_SECOND=5.0

# Cache
# GTEX_LINK_CACHE_SIZE=1000
# GTEX_LINK_CACHE_TTL=3600
```

- [ ] **Step 3: Remove tracked `.env`**

Run:
```bash
git rm .env
```
Expected: `.env` deleted from index.

- [ ] **Step 4: Add `.env` to `.gitignore` if not already present**

Run:
```bash
grep -qxF ".env" .gitignore || echo ".env" >> .gitignore
```

- [ ] **Step 5: Commit**

```bash
git add .env.example .gitignore
git commit -m "chore: remove tracked .env and add .env.example template"
```

---

## Task 8: Write `AGENTS.md`

**Files:**
- Create: `AGENTS.md`

- [ ] **Step 1: Create `AGENTS.md` with the full content**

Open `AGENTS.md` and write:

```markdown
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
- `docs/` - GTEx Portal endpoint documentation (`docs/README.md`,
  `docs/api_v2_*.md`) and design specs/plans (`docs/superpowers/`)
- `.claude/skills/` - repo-local Claude Code workflows for recurring tasks

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

## Coding Standards

- Use `uv` for dependency management; do not use direct `pip` installs.
- Use modern Python typing: `list[str]`, `dict[str, int]`, `str | None`.
- Format and lint Python with Ruff.
- Type check with mypy targeting Python 3.12 (strict mode).
- Keep FastAPI route behavior covered by route tests and service behavior
  covered by unit tests.
- Use `respx` to mock outbound httpx calls in tests.

## Testing Notes

- `make test` is the fast default.
- `make test-fast` runs in parallel via pytest-xdist.
- `make test-cov` runs coverage; gate is 90%.
- `make ci-local` runs formatting, linting, type checking, and tests.
- Treat failing checks as real issues unless you have clear evidence otherwise.

## GTEx Domain Notes

- Public API: `https://gtexportal.org/api/v2/` (no auth required).
- Rate-limited to 5 req/s by default; respect the token-bucket limiter.
- Use GENCODE IDs over gene symbols when possible.
- Standard test data: genes BRCA1/BRCA2/TP53/CFH/APOE; tissues
  Muscle_Skeletal/Whole_Blood/Brain_Cortex/Liver; dataset `gtex_v8`.
- Endpoint catalog: `docs/README.md` and `docs/api_v2_*.md`.
```

- [ ] **Step 2: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): add AGENTS.md as shared source of truth"
```

---

## Task 9: Rewrite `CLAUDE.md` to a thin pointer

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Replace the full contents of `CLAUDE.md` with**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): shrink CLAUDE.md to thin pointer at AGENTS.md"
```

---

## Task 10: Create `GEMINI.md`

**Files:**
- Create: `GEMINI.md`

- [ ] **Step 1: Write `GEMINI.md`**

```markdown
# GEMINI.md

@AGENTS.md

Gemini CLI entrypoint:

- Use `AGENTS.md` for shared instructions.
- Run `make ci-local` before final handoff.
```

- [ ] **Step 2: Commit**

```bash
git add GEMINI.md
git commit -m "docs(gemini): add GEMINI.md pointer at AGENTS.md"
```

---

## Task 11: Create `docs/architecture.md`

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Write `docs/architecture.md`**

This file absorbs the architecture and configuration content removed from the old `CLAUDE.md`. Open `docs/architecture.md` and write:

```markdown
# GTEx-Link Architecture

## Core Components

1. **API Layer** (`gtex_link/api/`)
   - `client.py` - HTTP client with token-bucket rate limiting (5 req/sec
     default), retry logic, connection pooling
   - `routes/` - FastAPI route handlers organized by GTEx data category

2. **Models Layer** (`gtex_link/models/`)
   - `requests.py` - Pydantic request models
   - `responses.py` - Pydantic response models matching GTEx v2 schema
   - `gtex.py` - GTEx-specific enums (tissues, datasets)

3. **Services Layer** (`gtex_link/services/`)
   - `gtex_service.py` - Business logic, async LRU caching, validation

4. **Utilities Layer** (`gtex_link/utils/`)
   - `caching.py` - Centralized async caching with configurable TTL/size

5. **Configuration** (`gtex_link/config.py`)
   - Pydantic settings with `GTEX_LINK_` env prefix
   - Nested models for API, cache, CORS, logging

6. **Application Factory** (`gtex_link/app.py`)
   - Creates FastAPI app, configures CORS, includes routers

7. **Server Management** (`gtex_link/server_manager.py`)
   - Unified entry point for HTTP, stdio, and unified (HTTP + MCP) transports

## Key Features

- Dual protocol (HTTP REST + MCP) over the same FastAPI app
- Async/await with connection pooling
- Token-bucket rate limiting respecting upstream limits
- Strict typing (Pydantic models, mypy strict)
- Structured logging (structlog) with JSON/console formats

## Environment Variables

All settings use the `GTEX_LINK_` prefix:

- `GTEX_LINK_HOST` (default `127.0.0.1`)
- `GTEX_LINK_PORT` (default `8000`)
- `GTEX_LINK_LOG_LEVEL` (default `INFO`)
- `GTEX_LINK_LOG_FORMAT` (`console` or `json`, default `console`)
- `GTEX_LINK_TRANSPORT` (`unified` | `http` | `stdio`, default `unified`)
- `GTEX_LINK_MCP_PATH` (default `/mcp`)
- `GTEX_LINK_MCP_PROFILE` (`full` | `lite`, default `full`)
- `GTEX_LINK_API_RATE_LIMIT_PER_SECOND` (default `5.0`)
- `GTEX_LINK_CACHE_SIZE` (default `1000`)
- `GTEX_LINK_CACHE_TTL` (default `3600`)

## Caching

Multi-level:
- Service-level async LRU cache for processed results
- Client-level HTTP response caching with TTL

## Error Hierarchy

- `GTExAPIError` - base
- `RateLimitError` - 429 from upstream
- `ServiceUnavailableError` - upstream 503
- `ValidationError` - input validation
- `ConfigurationError`, `CacheError` - misc

## Rate Limiting

Token-bucket algorithm:
- Default 5 req/s, burst 10
- Exponential backoff for retries
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture.md absorbing CLAUDE.md content"
```

---

## Task 12: Create `docs/conventions.md`

**Files:**
- Create: `docs/conventions.md`

- [ ] **Step 1: Write `docs/conventions.md`**

```markdown
# GTEx-Link Conventions

## Code Style

- Line length: 100 characters
- String quotes: double quotes (`"`)
- Imports: ruff `I` (isort)
- Docstring style: Google
- Strict mypy; no untyped defs

## Test Data Standards

Tests use a consistent set of genomic identifiers and tissues so fixtures
are interchangeable across files.

- **Genes**: `BRCA1`, `BRCA2`, `TP53`, `CFH`, `APOE`
- **Tissues**: `Muscle_Skeletal`, `Whole_Blood`, `Brain_Cortex`, `Liver`
- **Dataset**: `gtex_v8`

## Test Organization

- `tests/unit/` - unit tests for individual components
- `tests/test_api/` - FastAPI route tests
- `tests/test_models/` - Pydantic model tests
- `tests/test_services/` - service-layer tests
- `tests/test_client/` - HTTP client tests
- `tests/integration/` - end-to-end integration tests
- `tests/fixtures/` - shared GTEx response fixtures
- `tests/conftest.py` - shared pytest fixtures

## Test Markers

- `unit` - unit tests
- `integration` - integration tests
- `slow` - long-running tests
- `api` - tests that exercise FastAPI surface
- `mcp` - tests that exercise MCP surface

## Mocking

- Outbound HTTP calls are mocked with `respx`.
- Internal collaborators are mocked with `pytest-mock`'s `mocker` where appropriate.
- Avoid monkeypatching httpx internals; respx intercepts at the transport layer.

## GTEx API Response Conventions

- Responses include pagination metadata: `page`, `itemsPerPage`,
  `totalItems`, `totalPages`.
- Field names: snake_case in the upstream API; matched by Pydantic models.
- Null values appear for missing expression data — handle as `Optional`.

## Pagination

Most endpoints accept `page` and `itemsPerPage`. Defaults vary; consult the
per-endpoint docs in `docs/api_v2_*.md`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/conventions.md
git commit -m "docs: add conventions.md absorbing CLAUDE.md content"
```

---

## Task 13: Rewrite `Makefile`

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Replace `Makefile` contents**

Open `Makefile` and replace with:

```make
.PHONY: help install lock upgrade sync \
        format format-check lint lint-ci lint-fix \
        typecheck typecheck-fast typecheck-stop typecheck-fresh \
        test test-fast test-unit test-integration test-cov test-all \
        check ci-local precommit clean \
        dev mcp-serve mcp-serve-http \
        docker-build docker-up docker-down docker-logs docker-prod-config docker-npm-config \
        setup info

DOCKER_COMPOSE := $(shell if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

.DEFAULT_GOAL := help

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install project and development dependencies with uv
	uv sync --group dev

sync: install ## Alias for install

lock: ## Resolve and update uv.lock
	uv lock

upgrade: ## Upgrade locked dependencies
	uv lock --upgrade

format: ## Format Python code
	uv run ruff format gtex_link tests server.py mcp_server.py

format-check: ## Check formatting without writing
	uv run ruff format --check gtex_link tests server.py mcp_server.py

lint: ## Lint Python code
	uv run ruff check gtex_link tests server.py mcp_server.py

lint-ci: ## Lint Python code with GitHub-Actions output
	uv run ruff check gtex_link tests server.py mcp_server.py --output-format=github

lint-fix: ## Lint and apply safe fixes
	uv run ruff check gtex_link tests server.py mcp_server.py --fix

typecheck: ## Type check package
	uv run mypy gtex_link server.py mcp_server.py

typecheck-fast: ## Type check with mypy daemon and fallback
	@tmp_log=$$(mktemp); \
	if uv run dmypy run -- gtex_link server.py mcp_server.py >$$tmp_log 2>&1; then \
		cat $$tmp_log; \
	elif grep -Eq "Daemon crashed!|INTERNAL ERROR" $$tmp_log; then \
		echo "dmypy crashed; retrying with a fresh daemon..."; \
		uv run dmypy stop >/dev/null 2>&1 || true; \
		if uv run dmypy run -- gtex_link server.py mcp_server.py >$$tmp_log 2>&1; then \
			cat $$tmp_log; \
		else \
			cat $$tmp_log; \
			echo "Falling back to plain mypy..."; \
			uv run dmypy stop >/dev/null 2>&1 || true; \
			uv run mypy gtex_link server.py mcp_server.py; \
		fi; \
	else \
		cat $$tmp_log; \
		rm -f $$tmp_log; \
		exit 1; \
	fi; \
	rm -f $$tmp_log

typecheck-stop: ## Stop mypy daemon
	uv run dmypy stop

typecheck-fresh: ## Clear mypy cache and run typecheck
	rm -rf .mypy_cache
	uv run mypy gtex_link server.py mcp_server.py

test: ## Run tests quickly
	uv run pytest tests -q

test-fast: ## Run tests in parallel with pytest-xdist
	uv run pytest tests -q -n auto

test-unit: ## Run unit tests in parallel
	uv run pytest tests -q -n auto -m "not integration and not slow"

test-integration: ## Run integration tests serially
	uv run pytest tests -q -m "integration"

test-cov: ## Run tests with coverage
	uv run pytest tests --cov=gtex_link --cov-report=term-missing --cov-report=html

test-all: test-cov ## Alias for full test run with coverage

check: format lint ## Format and lint

ci-local: format-check lint-ci typecheck-fast test-fast ## Fast local CI-equivalent checks

precommit: ci-local ## Run checks expected before commit

clean: ## Remove local caches and generated reports
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage coverage.xml dist build

dev: ## Start unified REST + MCP development server
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

mcp-serve: ## Start local stdio MCP server
	uv run python mcp_server.py

mcp-serve-http: ## Start unified server (alias for `dev`)
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

docker-build: ## Build Docker image
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml build

docker-up: ## Start Docker development stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml up -d

docker-down: ## Stop Docker development stack
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml down

docker-logs: ## Follow Docker logs
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml logs -f

docker-prod-config: ## Render production Compose configuration
	$(DOCKER_COMPOSE) -f docker/docker-compose.yml config

docker-npm-config: ## Render NPM Compose configuration
	$(DOCKER_COMPOSE) -f docker/docker-compose.npm.yml --env-file .env.docker.example config

setup: ## Run comprehensive setup for Docker + NPM deployment
	./setup_gtex_link.sh

info: ## Show project information
	@echo "Project: GTEx-Link"
	@echo "uv: $(shell uv --version 2>/dev/null || echo 'not installed')"
```

**Note:** the `dev` and `mcp-serve-http` targets reference `server.py --transport unified` which doesn't exist yet — it lands in Phase 3. Until then, `make dev` will fail. That's acceptable for a tooling-only phase; the targets are correct for the post-Phase-3 reality.

If you want a working `make dev` *during* Phase 1, replace its body with the legacy command temporarily:
```make
dev: ## Start development HTTP server (legacy until Phase 3)
	uv run python server.py
```
Remove the legacy form when Phase 3 lands.

- [ ] **Step 2: Verify `make help` renders**

Run:
```bash
make help
```
Expected: a sorted, colorized list of targets.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "build(make): rewrite Makefile around ci-local"
```

---

## Task 14: Create `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Ensure `.github/workflows/` exists**

Run:
```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Write `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  pull_request:
  push:
    branches:
      - main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  quality:
    name: Format, lint, typecheck, tests, and coverage
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9 # v7
        with:
          enable-cache: true
          version: "0.8.7"

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Run local CI checks
        run: make ci-local

      - name: Run coverage
        run: make test-cov
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow running make ci-local and coverage"
```

---

## Task 15: Create `.github/workflows/security.yml`

**Files:**
- Create: `.github/workflows/security.yml`

- [ ] **Step 1: Write the file**

```yaml
name: Security

on:
  pull_request:
  push:
    branches:
      - main
  schedule:
    - cron: "17 3 * * 1"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  codeql:
    name: CodeQL
    runs-on: ubuntu-latest
    if: ${{ !github.event.repository.private }}
    permissions:
      actions: read
      contents: read
      security-events: write

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Initialize CodeQL
        uses: github/codeql-action/init@ed410739ba306e4ebe5e123421a6bd694e494a2b # v4
        with:
          languages: python
          build-mode: none

      - name: Analyze
        uses: github/codeql-action/analyze@ed410739ba306e4ebe5e123421a6bd694e494a2b # v4

  dependency-review:
    name: Dependency review
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    permissions:
      contents: read
      pull-requests: read

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Dependency Review
        uses: actions/dependency-review-action@2031cfc080254a8a887f58cffee85186f0e49e48 # v4.9.0
        continue-on-error: true
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/security.yml
git commit -m "ci(security): add CodeQL and dependency review"
```

---

## Task 16: Create `.github/workflows/docker.yml`

**Files:**
- Create: `.github/workflows/docker.yml`

- [ ] **Step 1: Write the file**

```yaml
name: Docker

on:
  pull_request:
    paths:
      - "docker/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/docker.yml"
  push:
    branches:
      - main
    paths:
      - "docker/**"
      - "pyproject.toml"
      - "uv.lock"

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

jobs:
  validate-compose:
    name: Validate Compose configs
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Render production compose
        run: docker compose -f docker/docker-compose.yml config

      - name: Render NPM compose
        run: docker compose -f docker/docker-compose.npm.yml --env-file .env.docker.example config

  build-image:
    name: Build production image
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Build
        run: docker build -f docker/Dockerfile -t gtex-link:ci .
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/docker.yml
git commit -m "ci(docker): validate compose configs and build image"
```

---

## Task 17: Create `.github/workflows/release.yml`

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Write the file**

```yaml
name: Release

on:
  push:
    tags:
      - "v*"

permissions:
  contents: read

jobs:
  release-validation:
    name: Release validation
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6

      - name: Set up Python
        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405 # v6
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@94527f2e458b27549849d47d273a16bec83a01e9 # v7
        with:
          enable-cache: true
          version: "0.8.7"

      - name: Install dependencies
        run: uv sync --group dev --frozen

      - name: Run local CI checks
        run: make ci-local

      - name: Validate production Compose config
        run: make docker-prod-config

      - name: Validate NPM Compose config
        run: make docker-npm-config

      - name: Build release Docker image
        run: docker build -f docker/Dockerfile -t gtex-link:release .
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci(release): add tag-triggered release validation"
```

---

## Task 18: Create `.github/dependabot.yml`

**Files:**
- Create: `.github/dependabot.yml`

- [ ] **Step 1: Write the file**

```yaml
version: 2
updates:
  - package-ecosystem: "uv"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      uv:
        patterns:
          - "*"

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"

  - package-ecosystem: "docker"
    directory: "/docker"
    schedule:
      interval: "weekly"
```

**Note:** if GitHub rejects `package-ecosystem: "uv"` (it may not yet be GA depending on Dependabot's current support matrix), switch to `pip` as a fallback:
```yaml
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
```

- [ ] **Step 2: Commit**

```bash
git add .github/dependabot.yml
git commit -m "ci(dependabot): enable weekly uv/actions/docker updates"
```

---

## Task 19: Create `.github/pull_request_template.md`

**Files:**
- Create: `.github/pull_request_template.md`

- [ ] **Step 1: Write the file**

```markdown
## Summary

-

## Type

- [ ] feat: new feature
- [ ] fix: bug fix
- [ ] refactor: code reorganization, no behavior change
- [ ] docs: documentation only
- [ ] build/ci: tooling
- [ ] test: tests only

## Verification

- [ ] `make ci-local` passes locally
- [ ] Tests added/updated for behavior changes
- [ ] CHANGELOG.md updated if user-facing or breaking

## Breaking changes

(Leave blank if none. Otherwise: API/MCP/CLI/env-var contract changes and migration notes.)
```

- [ ] **Step 2: Commit**

```bash
git add .github/pull_request_template.md
git commit -m "ci: add pull request template"
```

---

## Task 20: Scaffold `.claude/skills/fastapi-route-change/SKILL.md`

**Files:**
- Create: `.claude/skills/fastapi-route-change/SKILL.md`

- [ ] **Step 1: Create directory and file**

```bash
mkdir -p .claude/skills/fastapi-route-change
```

Write `.claude/skills/fastapi-route-change/SKILL.md`:

```markdown
---
name: fastapi-route-change
description: Use when adding or modifying a FastAPI route in gtex-link. Walks through request/response models, route handler, service wiring, and tests.
---

# FastAPI route change

Use this skill when adding or modifying a FastAPI route under `gtex_link/api/routes/`.

## Checklist

1. **Request model.** Define or extend a Pydantic model in `gtex_link/models/requests.py`. Field aliases map to GTEx Portal query parameters. Set sensible defaults and validators.
2. **Response model.** Define or extend the matching response model in `gtex_link/models/responses.py`. Match upstream field names.
3. **Service method.** Add or update a method on `GTExService` in `gtex_link/services/gtex_service.py`. Wrap upstream calls in the existing caching/rate-limiting paths. Do not bypass `GTExClient`.
4. **Route handler.** Add the route in the appropriate file under `gtex_link/api/routes/`. Reuse FastAPI `Depends` for `GTExService`. Return the Pydantic response model.
5. **Tests.**
   - Route test under `tests/test_api/test_<category>_routes.py` using `respx` to stub `https://gtexportal.org/api/v2/...`.
   - Service test under `tests/test_services/` for the new service method.
6. **Docs.** If the route exposes a new GTEx endpoint, update `docs/README.md` and add per-endpoint markdown via `python docs/generate_endpoint_docs.py` when the openapi spec is updated.
7. **MCP exposure.** Decide if this should be an MCP tool (see `mcp-tool-change` skill if yes).
8. **CI.** Run `make ci-local` before pushing.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/fastapi-route-change/
git commit -m "docs(skills): add fastapi-route-change skill"
```

---

## Task 21: Scaffold `.claude/skills/mcp-tool-change/SKILL.md`

**Files:**
- Create: `.claude/skills/mcp-tool-change/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/mcp-tool-change/
git commit -m "docs(skills): add mcp-tool-change skill"
```

---

## Task 22: Scaffold `.claude/skills/ci-failure-triage/SKILL.md`

**Files:**
- Create: `.claude/skills/ci-failure-triage/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
---
name: ci-failure-triage
description: Use when CI fails on a PR or main. Walks through reproducing locally and root-causing without bypassing checks.
---

# CI failure triage

## Classify the failure

Look at the GitHub Actions log and decide which stage failed:

- **Format check** (`make format-check`) — ruff disagrees with the committed formatting.
- **Lint** (`make lint-ci`) — ruff lint rule.
- **Typecheck** (`make typecheck-fast`) — mypy.
- **Tests** (`make test-fast`) — failing or erroring test.
- **Coverage** — gate fell below 90%.
- **Docker** — compose render or build failed.
- **CodeQL / dependency review** — security workflows.

## Reproduce locally

Run the same Make target that failed in CI:

- `make format-check`
- `make lint-ci`
- `make typecheck-fast`
- `make test-fast`
- `make test-cov`
- `make docker-prod-config`

## Fix at root cause

- Do not add `# type: ignore` or `# noqa` to silence a check unless the
  underlying behavior is genuinely correct and the tool is wrong.
- Do not use `git commit --no-verify` to bypass pre-commit.
- For flaky tests, rerun once to confirm flakiness, then mark with the
  `slow` marker and open a follow-up issue rather than disabling the test.

## Confirm fix

Run `make ci-local` locally. Push. Watch the workflow re-run.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/ci-failure-triage/
git commit -m "docs(skills): add ci-failure-triage skill"
```

---

## Task 23: Scaffold `.claude/skills/release-readiness/SKILL.md`

**Files:**
- Create: `.claude/skills/release-readiness/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
---
name: release-readiness
description: Use when preparing a versioned release of gtex-link. Walks through changelog, version bump, tag, and watching the release workflow.
---

# Release readiness

## Pre-flight

1. Confirm `main` is green: latest CI run succeeded.
2. Verify there are no outstanding `dependabot` PRs that should land first.
3. Confirm `CHANGELOG.md` has an Unreleased section with all user-visible changes since the last tag.

## Bump

1. Open `pyproject.toml` and bump `version`. Follow semver:
   - `MAJOR.MINOR.PATCH`
   - MAJOR for breaking changes
   - MINOR for feature additions
   - PATCH for fixes
2. Rewrite the `[Unreleased]` heading in `CHANGELOG.md` to `[X.Y.Z] - YYYY-MM-DD` and add a fresh empty `[Unreleased]` section above it.
3. Commit: `chore(release): bump to X.Y.Z`.

## Tag and push

```bash
git tag vX.Y.Z
git push origin main vX.Y.Z
```

## Watch

The `release.yml` workflow runs on `v*` tag pushes. It runs `make ci-local`, validates compose configs, and builds the release Docker image.

## Roll forward

If `release.yml` fails, fix on `main`, bump to `vX.Y.(Z+1)`, retag.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/release-readiness/
git commit -m "docs(skills): add release-readiness skill"
```

---

## Task 24: Scaffold `.claude/skills/gtex-api-endpoint-add/SKILL.md`

**Files:**
- Create: `.claude/skills/gtex-api-endpoint-add/SKILL.md`

- [ ] **Step 1: Write the file**

```markdown
---
name: gtex-api-endpoint-add
description: Use when wiring a new upstream GTEx Portal endpoint into gtex-link. Walks through the spec, models, service, route, tests, and MCP exposure decision.
---

# Add a new GTEx Portal endpoint

## Locate the endpoint spec

1. Open `docs/gtex-openapi-spec-formatted.json` and find the path you want.
2. Cross-reference the per-endpoint markdown under `docs/api_v2_<category>_<endpoint>_<method>.md`.

## Wire the models

1. Add the request model to `gtex_link/models/requests.py`. Map field aliases to GTEx Portal query parameter names (camelCase).
2. Add the response model to `gtex_link/models/responses.py`. Match upstream field names exactly.

## Wire the service

1. Open `gtex_link/services/gtex_service.py`.
2. Add an async method on `GTExService` that:
   - Builds the URL from `settings.api.endpoints[<key>]`.
   - Calls `self._client.get(...)` or `.post(...)`.
   - Wraps the response in the response model.
   - Uses `async_lru` caching where idempotent.

## Wire the route

1. Add a handler under `gtex_link/api/routes/<category>.py` (create the file if missing and register the router in `gtex_link/api/routes/__init__.py` and `gtex_link/app.py`).
2. Use `Depends(GTExService)`.

## Tests

1. **Route test** under `tests/test_api/test_<category>_routes.py`:
   - Use `respx` to mock `https://gtexportal.org/api/v2/<path>`.
   - Hit the route via the FastAPI test client.
   - Assert response shape.
2. **Service test** under `tests/test_services/`.
3. **Model tests** under `tests/test_models/`.

## MCP exposure

Decide:
- Should this be an MCP tool? If yes, run the `mcp-tool-change` skill.
- Add to `full` profile, and to `lite` only if it's a common-path tool.

## Update docs

- Add a section in `docs/README.md` if this is a new category.
- Regenerate per-endpoint docs from the OpenAPI spec:
  ```bash
  cd docs && python generate_endpoint_docs.py
  ```

## CI

Run `make ci-local`.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/gtex-api-endpoint-add/
git commit -m "docs(skills): add gtex-api-endpoint-add skill"
```

---

## Task 25: Create `CHANGELOG.md`

**Files:**
- Create: `CHANGELOG.md`

- [ ] **Step 1: Write the file**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add CHANGELOG.md with Phase 1 entries"
```

---

## Task 26: Run `make ci-local` and fix anything that fails

**Files:**
- Modify: any test or code file with mypy/ruff errors introduced by the upgrades

- [ ] **Step 1: Run the gate**

Run:
```bash
make ci-local
```
Expected: pass. If failures appear:

- **`format-check`** — run `make format` and commit the result.
- **`lint-ci`** — fix lint findings. New rules enabled (`N`, `S`, `T20`, `RUF`) may flag existing code. Fix legitimate issues; for false positives, use the narrowest possible `# noqa: <rule>` comment.
- **`typecheck-fast`** — fix mypy findings. Common 1.14 vs 1.10 differences: stricter inference around `Optional` and stricter handling of `Any`. Fix at the source; do not add `type: ignore` without a specific code.
- **`test-fast`** — fix test failures caused by pytest 9 deprecations (e.g., `event_loop` fixture is now session-scoped by default — adjust `conftest.py` if needed).

Each fix should be committed separately so the PR history is clear:
```bash
git commit -m "fix(<area>): adjust for <tool> upgrade"
```

- [ ] **Step 2: Confirm coverage still meets 90%**

Run:
```bash
make test-cov
```
Expected: terminal output shows `TOTAL ... 90%+`. If it dropped below, do NOT lower the gate — investigate which file's coverage regressed and either restore the tests or fix the source.

---

## Task 27: Push branch and open PR

**Files:**
- No file changes

- [ ] **Step 1: Push the branch**

```bash
git push -u origin phase-1-foundation
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "Phase 1: Foundation modernization" --body "$(cat <<'EOF'
## Summary

- Switch build backend from setuptools to hatchling.
- Bump Python minimum from 3.10 to 3.12.
- Modernize all dependencies to mirror ../pubtator-link constraints.
- Split CLAUDE.md into AGENTS.md (source of truth) + thin CLAUDE.md/GEMINI.md pointers.
- Move long-form content to docs/architecture.md and docs/conventions.md.
- Rewrite Makefile around `make ci-local`; add `typecheck-fast` (dmypy), `test-fast` (xdist parallel).
- Add .github/ workflows: CI, security (CodeQL + dependency review), docker, release.
- Add Dependabot config and PR template.
- Add five repo-local skills under .claude/skills/.
- Add CHANGELOG.md.
- Clean repo: delete coverage.xml, htmlcov/, gtex_link.egg-info/, root PLAN.md (relocated), tracked .env.

No runtime code changes. Phase 2 (observability + tests) and Phase 3 (MCP facade + transport unification) are separate PRs.

## Type

- [x] build/ci: tooling
- [x] docs: documentation

## Verification

- [x] `make ci-local` passes locally
- [x] Coverage gate still ≥90%
- [ ] Tests added/updated for behavior changes — N/A, no runtime changes
- [x] CHANGELOG.md updated

## Breaking changes

See CHANGELOG.md "[Unreleased] → Changed/Removed" sections.
EOF
)"
```

Expected: PR URL printed. Wait for CI to pass.

---

## Phase 1 success criteria

- [ ] `make ci-local` green locally and in GitHub Actions
- [ ] `uv lock` regenerated with new constraints
- [ ] AGENTS.md / CLAUDE.md / GEMINI.md split done
- [ ] Five skill SKILL.md files present
- [ ] PR template, dependabot, CI/security/docker/release workflows live
- [ ] Coverage gate still ≥90%
- [ ] No runtime behavior change (no `gtex_link/*.py` files modified)
