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
