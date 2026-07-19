# Post-Sync Stack and Agent Parity Implementation Plan

> Historical record — **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the residual stack, agent, README, and local workflow parity work after syncing `gtex-link` with the updated `origin/main`.

**Architecture:** Keep the completed Phase 1 foundation and Phase 2 observability work. This plan makes narrow config, documentation, and workflow updates only; the explicit MCP facade and unified transport remain owned by the existing Phase 3 plan.

**Tech Stack:** Python 3.12, uv, hatchling, Ruff, mypy strict, pytest, pytest-xdist, FastAPI, FastMCP, asgi-correlation-id, prometheus-client.

---

## File Structure

**Create:**
- `.python-version` - pins local tool/runtime discovery to Python 3.12.
- `.editorconfig` - editor defaults matching sibling repositories.
- `scripts/check_file_size.py` - 600-line source module budget check.

**Modify:**
- `pyproject.toml` - add `gtex-link-mcp`, expand mypy overrides, remove default coverage from pytest, move coverage gate to coverage config, remove global warning-as-error policy.
- `uv.lock` - refresh after `pyproject.toml` metadata changes.
- `Makefile` - add `lint-loc` and include it in `ci-local`.
- `AGENTS.md` - document `lint-loc` and file-size discipline.
- `README.md` - replace stale commands with current `Makefile` and `uv run` commands.

**Do not modify in this plan:**
- `gtex_link/app.py`
- `gtex_link/server_manager.py`
- `server.py`
- `mcp_server.py`
- `mcp_http_server.py`
- `docker/*`

Those files are part of the existing Phase 3 MCP facade and transport plan.

---

## Task 1: Reconcile `pyproject.toml` Test and Script Metadata

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`

- [ ] **Step 1: Run a failing metadata check**

Run:

```bash
uv run python - <<'PY'
import tomllib
from pathlib import Path

data = tomllib.loads(Path("pyproject.toml").read_text())
scripts = data["project"]["scripts"]
assert scripts["gtex-link"] == "gtex_link.cli:main"
assert scripts["gtex-mcp"] == "mcp_server:main"
assert scripts["gtex-link-mcp"] == "mcp_server:main"

overrides = data["tool"]["mypy"]["overrides"][0]["module"]
for module in [
    "async_lru.*",
    "structlog.*",
    "mcp.*",
    "fastmcp.*",
    "fastapi.*",
    "pydantic.*",
    "pydantic_settings.*",
    "httpx.*",
    "uvicorn.*",
    "asgi_correlation_id.*",
    "prometheus_client.*",
]:
    assert module in overrides, module

pytest_opts = data["tool"]["pytest"]["ini_options"]
joined = "\n".join(pytest_opts["addopts"])
assert "--cov=gtex_link" not in joined
assert "--cov-fail-under=90" not in joined
assert "filterwarnings" not in pytest_opts
assert data["tool"]["coverage"]["report"]["fail_under"] == 90
PY
```

Expected before implementation: FAIL on missing `gtex-link-mcp` and coverage/warning assertions.

- [ ] **Step 2: Update `[project.scripts]`**

Change the script block to:

```toml
[project.scripts]
gtex-link = "gtex_link.cli:main"
gtex-link-mcp = "mcp_server:main"
gtex-mcp = "mcp_server:main"
```

- [ ] **Step 3: Expand mypy overrides**

Change the existing override module list to:

```toml
[[tool.mypy.overrides]]
module = [
    "async_lru.*",
    "structlog.*",
    "mcp.*",
    "fastmcp.*",
    "fastapi.*",
    "pydantic.*",
    "pydantic_settings.*",
    "httpx.*",
    "uvicorn.*",
    "asgi_correlation_id.*",
    "prometheus_client.*",
]
ignore_missing_imports = true
```

- [ ] **Step 4: Make pytest fast by default**

Change `[tool.pytest.ini_options]` so `addopts` contains only:

```toml
addopts = [
    "--strict-markers",
    "--strict-config",
    "-ra",
]
```

Remove the entire `filterwarnings = [...]` block from `[tool.pytest.ini_options]`.

- [ ] **Step 5: Move coverage gate to coverage config**

Update `[tool.coverage.report]` to include:

```toml
[tool.coverage.report]
fail_under = 90
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
```

- [ ] **Step 6: Refresh lockfile**

Run:

```bash
uv lock
```

Expected: `uv.lock` updates only if project metadata or resolution metadata changes.

- [ ] **Step 7: Re-run metadata check**

Run the Step 1 Python snippet again.

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: tighten project test metadata"
```

---

## Task 2: Add File-Size Discipline and Root Tooling Defaults

**Files:**
- Create: `.python-version`
- Create: `.editorconfig`
- Create: `scripts/check_file_size.py`
- Modify: `Makefile`

- [ ] **Step 1: Create `.python-version`**

Write:

```text
3.12
```

- [ ] **Step 2: Create `.editorconfig`**

Write:

```ini
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{yml,yaml,toml,json,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

- [ ] **Step 3: Create `scripts/check_file_size.py`**

Write:

```python
"""Enforce source module line-count budgets for agent-friendly refactors."""

from __future__ import annotations

from pathlib import Path

MAX_SOURCE_LINES = 600
ROOT = Path(__file__).resolve().parents[1]
CHECK_PATHS = [
    ROOT / "gtex_link",
    ROOT / "server.py",
    ROOT / "mcp_server.py",
    ROOT / "mcp_http_server.py",
]
ALLOWLIST_PATH = ROOT / ".loc-allowlist"


def read_allowlist() -> dict[Path, int]:
    """Read optional grandfathered file ceilings."""
    if not ALLOWLIST_PATH.exists():
        return {}

    allowlist: dict[Path, int] = {}
    for line in ALLOWLIST_PATH.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        path_text, _, ceiling_text = stripped.partition(":")
        allowlist[ROOT / path_text] = int(ceiling_text)
    return allowlist


def iter_python_files() -> list[Path]:
    """Return checked Python source files."""
    files: list[Path] = []
    for path in CHECK_PATHS:
        if not path.exists():
            continue
        if path.is_file():
            files.append(path)
        else:
            files.extend(sorted(path.rglob("*.py")))
    return files


def line_count(path: Path) -> int:
    """Count physical lines in a source file."""
    return len(path.read_text().splitlines())


def main() -> int:
    """Check source files and print violations."""
    allowlist = read_allowlist()
    failures: list[str] = []

    for path in iter_python_files():
        count = line_count(path)
        ceiling = allowlist.get(path, MAX_SOURCE_LINES)
        if count > ceiling:
            rel = path.relative_to(ROOT)
            failures.append(f"{rel}: {count} lines exceeds limit {ceiling}")

    if failures:
        print("File-size budget exceeded:")
        for failure in failures:
            print(f"  {failure}")
        return 1

    print(f"File-size budget OK: {MAX_SOURCE_LINES} line default")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Update `.PHONY` in `Makefile`**

Add `lint-loc` to the quality target line:

```make
        format format-check lint lint-ci lint-fix lint-loc \
```

- [ ] **Step 5: Add `lint-loc` target**

Insert after `lint-fix`:

```make
lint-loc: ## Enforce per-file line budget (see AGENTS.md "File Size Discipline")
	uv run python scripts/check_file_size.py
```

- [ ] **Step 6: Wire `lint-loc` into `ci-local`**

Change:

```make
ci-local: format-check lint-ci typecheck-fast test-fast ## Fast local CI-equivalent checks
```

to:

```make
ci-local: format-check lint-ci lint-loc typecheck-fast test-fast ## Fast local CI-equivalent checks
```

- [ ] **Step 7: Verify file-size check**

Run:

```bash
make lint-loc
```

Expected: PASS with `File-size budget OK: 600 line default`.

- [ ] **Step 8: Commit**

```bash
git add .python-version .editorconfig scripts/check_file_size.py Makefile
git commit -m "chore: add source file size discipline"
```

---

## Task 3: Update Agent Instructions

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: Update focused commands**

Add `make lint-loc` to the "Useful focused commands" list immediately after `make lint-fix`:

```markdown
- `make lint-loc`
```

- [ ] **Step 2: Update testing notes**

Change:

```markdown
- `make ci-local` runs formatting, linting, type checking, and tests.
```

to:

```markdown
- `make ci-local` runs formatting, linting, file-size checks, type checking, and tests.
```

- [ ] **Step 3: Add file-size discipline section**

Insert before `## Testing Notes`:

```markdown
## File Size Discipline

Hard cap: **600 lines per Python module** in `gtex_link/`, `server.py`,
`mcp_server.py`, and `mcp_http_server.py` while it remains. Enforced by
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
```

- [ ] **Step 4: Verify AGENTS mentions lint-loc once in commands and once in file-size section**

Run:

```bash
rg -n "lint-loc|File Size Discipline|600 lines" AGENTS.md
```

Expected: output includes the focused command, the section header, and the cap.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md
git commit -m "docs: document file size discipline"
```

---

## Task 4: Refresh README Commands

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Replace Quick Start installation block**

Replace the current Quick Start installation code block with:

````markdown
```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/gtex-link/gtex-link.git
cd gtex-link
make install

# Run local CI-equivalent checks
make ci-local
```
````

- [ ] **Step 2: Replace HTTP server usage block**

Use:

````markdown
```bash
# Start the development HTTP server
make dev

# Start HTTP server with custom options
uv run gtex-link server --host 127.0.0.1 --port 8000

# With auto-reload for development
uv run gtex-link server --reload
```
````

- [ ] **Step 3: Replace MCP server usage block**

Use:

````markdown
```bash
# Start MCP stdio server
make mcp-serve

# Start hosted MCP endpoint with REST API
make mcp-serve-http

# Direct console scripts
uv run gtex-link-mcp
uv run gtex-mcp  # compatibility alias
```
````

- [ ] **Step 4: Update Claude Desktop example**

Use the new preferred command while documenting the compatibility alias nearby:

```json
{
  "mcpServers": {
    "gtex-link": {
      "command": "gtex-link-mcp",
      "env": {
        "GTEX_LINK_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Then add one sentence after the JSON block:

````markdown
Existing configurations that use `gtex-mcp` continue to work as a compatibility alias.
````

- [ ] **Step 5: Replace development setup block**

Use:

````markdown
```bash
# Clone repository
git clone https://github.com/gtex-link/gtex-link.git
cd gtex-link

# Install project and development dependencies
make install

# Install pre-commit hooks
uv run pre-commit install
```
````

- [ ] **Step 6: Replace tests block**

Use:

````markdown
```bash
# Run tests
make test

# Run fast parallel tests
make test-fast

# Run with coverage
make test-cov

# Run specific test categories
uv run pytest -m "not integration"
uv run pytest -m "unit"
```
````

- [ ] **Step 7: Replace code quality block**

Use:

````markdown
```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Full local CI-equivalent check
make ci-local
```
````

- [ ] **Step 8: Ensure stale commands are gone**

Run:

```bash
rg -n "make dev-setup|make server|make check-all|make mcp(\\s|$)" README.md
```

Expected: no output.

- [ ] **Step 9: Commit**

```bash
git add README.md
git commit -m "docs: refresh development commands"
```

---

## Task 5: Run Final Verification

**Files:**
- No planned edits.

- [ ] **Step 1: Run lock check/update**

Run:

```bash
uv lock
```

Expected: exits 0.

- [ ] **Step 2: Run formatting check**

Run:

```bash
make format-check
```

Expected: PASS. If it fails only on files edited in this plan, run `make format`, then repeat `make format-check`.

- [ ] **Step 3: Run lint**

Run:

```bash
make lint
```

Expected: PASS.

- [ ] **Step 4: Run file-size check**

Run:

```bash
make lint-loc
```

Expected: PASS.

- [ ] **Step 5: Run typecheck**

Run:

```bash
make typecheck
```

Expected: PASS, or existing unrelated strictness debt documented with exact errors.

- [ ] **Step 6: Run tests**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 7: Run local CI**

Run:

```bash
make ci-local
```

Expected: PASS.

- [ ] **Step 8: Final commit if verification changed files**

If `uv lock` or `make format` changed files after earlier commits:

```bash
git status --short
git add <changed-files>
git commit -m "chore: finalize stack parity verification"
```

---

## Handoff Notes

After this plan is complete, the remaining modernization work is the existing Phase 3 MCP facade and transport unification plan:

- `docs/superpowers/plans/2026-05-11-phase-3-mcp-facade-and-transport.md`

Do not mix Phase 3 facade changes into this residual stack parity plan.
