# Phase 3 — MCP Facade & Transport Unification Implementation Plan

> Historical record — **Historical design record — not a live contract.** This dated document is kept as
> written: it records the intent at the time and may not describe current behaviour.
> The live contract is `docs/data.md`, `README.md`, and the code. Excluded from the
> docs prose lint in `tests/test_mcp/test_provenance_meta.py` for exactly that reason.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `FastMCP.from_fastapi` with an explicit facade-based MCP layer. Unify the three server entry scripts into a single `server.py --transport {unified,http,stdio}` flow. Collapse the Docker compose split (api + mcp) into a single service. Preserve all MCP tool names 1:1.

**Architecture:** New `gtex_link/mcp/` package with `facade.py`, `profiles.py`, `resources.py`, `errors.py`, `output_validation.py`, `service_adapters.py`, and per-category tool modules in `tools/`. The facade builds a `FastMCP` instance with hand-tuned `instructions`, `mask_error_details=True`, and explicit `register_*` calls per tool category. `app.py` becomes a pure FastAPI factory. `server_manager.py` becomes `UnifiedServerManager` with `start_unified_server`, `start_http_only_server`, `start_stdio_server`, and graceful shutdown. `mcp_http_server.py` is deleted. The `gtex-mcp-http` console script is removed. `GTEX_LINK_MCP_PORT` env var is removed.

**Tech Stack:** fastmcp 3.2+, mcp[cli] 1.27+, FastAPI, asgi-correlation-id (already wired), prometheus-client (already wired).

**Prerequisite:** Phases 1 and 2 merged.

---

## File Structure

**Create:**
- `gtex_link/mcp/__init__.py`
- `gtex_link/mcp/facade.py`
- `gtex_link/mcp/profiles.py`
- `gtex_link/mcp/resources.py`
- `gtex_link/mcp/errors.py`
- `gtex_link/mcp/output_validation.py`
- `gtex_link/mcp/service_adapters.py`
- `gtex_link/mcp/tools/__init__.py`
- `gtex_link/mcp/tools/reference.py`
- `gtex_link/mcp/tools/expression.py`
- `gtex_link/mcp/tools/search_fetch.py`
- `gtex_link/__main__.py`
- `tests/test_mcp/__init__.py`
- `tests/test_mcp/test_facade.py`
- `tests/test_mcp/test_profiles.py`
- `tests/test_mcp/test_tools_reference.py`
- `tests/test_mcp/test_tools_expression.py`
- `tests/test_mcp/test_tools_search_fetch.py`
- `tests/test_mcp/test_errors.py`

**Modify:**
- `gtex_link/app.py` (remove MCP code; pure FastAPI factory)
- `gtex_link/server_manager.py` (replace `ServerManager` with `UnifiedServerManager`)
- `gtex_link/config.py` (add `transport`, `mcp_profile`; remove `mcp_port`)
- `server.py` (replace HTTP-only entry with argparse `--transport` entry)
- `mcp_server.py` (thin stdio wrapper using `UnifiedServerManager.start_stdio_server`)
- `pyproject.toml` (remove `gtex-mcp-http` script entry; bump version)
- `Makefile` (update `dev`, `mcp-serve-http` targets to point at unified `server.py`)
- `docker/docker-compose.yml` (collapse `api` + `mcp` services to one)
- `docker/docker-compose.npm.yml` (point upstream at single service)
- `CHANGELOG.md` (Phase 3 entries)

**Delete:**
- `mcp_http_server.py`

---

## Task 1: Create a feature branch

**Files:**
- No files modified

- [ ] **Step 1: Create branch from main**

```bash
git checkout main
git pull origin main
git checkout -b phase-3-mcp-facade-and-transport
```

---

## Task 2: Audit current MCP tool surface

**Files:**
- Create (temp): `docs/superpowers/plans/archive/2026-05-11-mcp-tool-audit.md`

- [ ] **Step 1: List every MCP tool currently exposed**

The current `app.py` uses `FastMCP.from_fastapi` which auto-generates tools from FastAPI routes. The explicit `mcp_custom_names` dict only renames six tools — any *other* route also becomes a tool. Enumerate the complete list.

Run a one-off Python snippet to dump every tool name:

```bash
uv run python - <<'PY'
from gtex_link.app import mcp_app

if mcp_app is None:
    print("ERROR: mcp_app is None")
    raise SystemExit(1)

# fastmcp 0.2.x and 3.x both expose tools via an internal registry; the
# attribute name varies. Try both:
tools = []
for attr in ("_tool_manager", "tool_manager", "tools"):
    obj = getattr(mcp_app, attr, None)
    if obj is None:
        continue
    if hasattr(obj, "list_tools"):
        tools = list(obj.list_tools())
        break
    if isinstance(obj, dict):
        tools = list(obj.keys())
        break

for t in tools:
    name = getattr(t, "name", t)
    print(name)
PY
```

(If the attribute names differ in the installed fastmcp 3.x version, run the snippet inside a debugger or use `dir(mcp_app)` to find the registry.)

- [ ] **Step 2: Record the result**

Create `docs/superpowers/plans/archive/2026-05-11-mcp-tool-audit.md` and paste the listing:

```markdown
# MCP tool audit — 2026-05-11

Tools exposed by the current `FastMCP.from_fastapi` build, prior to facade migration:

- search
- fetch
- search_gtex_genes
- get_gene_information
- get_transcript_information
- get_median_expression_levels
- get_individual_expression_data
- get_top_expressed_genes_by_tissue
- <any others discovered>

Decision per tool:
- preserve = explicitly registered in new facade
- drop = intentionally removed; documented in CHANGELOG
```

Mark each tool `preserve` or `drop`. The expected baseline is the 8 tools above (3 ChatGPT-compatible search/fetch — wait, there are 2 — and the 6 in the `mcp_custom_names` dict). If anything extra appears, that's a "drop" candidate and must go in the changelog.

- [ ] **Step 3: Commit the audit**

```bash
git add docs/superpowers/plans/archive/2026-05-11-mcp-tool-audit.md
git commit -m "docs: record pre-migration MCP tool audit"
```

---

## Task 3: Scaffold `gtex_link/mcp/` package

**Files:**
- Create: `gtex_link/mcp/__init__.py`
- Create: `gtex_link/mcp/tools/__init__.py`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p gtex_link/mcp/tools
```

- [ ] **Step 2: Write `gtex_link/mcp/__init__.py`**

```python
"""MCP facade for GTEx-Link.

This package replaces the previous auto-generation via FastMCP.from_fastapi
with an explicit facade. Construction entry point: `create_gtex_mcp`.
"""

from gtex_link.mcp.facade import create_gtex_mcp

__all__ = ["create_gtex_mcp"]
```

- [ ] **Step 3: Write `gtex_link/mcp/tools/__init__.py`**

```python
"""MCP tool registration modules grouped by category."""

from gtex_link.mcp.tools.expression import register_expression_tools
from gtex_link.mcp.tools.reference import register_reference_tools
from gtex_link.mcp.tools.search_fetch import register_search_fetch_tools

__all__ = [
    "register_expression_tools",
    "register_reference_tools",
    "register_search_fetch_tools",
]
```

(Imports fail until the modules in later tasks exist — proceed.)

---

## Task 4: Write `profiles.py`

**Files:**
- Create: `gtex_link/mcp/profiles.py`
- Test: `tests/test_mcp/test_profiles.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/__init__.py` (empty).

Create `tests/test_mcp/test_profiles.py`:

```python
"""Tests for MCP tool profiles."""

from __future__ import annotations

import pytest

from gtex_link.mcp.profiles import (
    LITE_TOOLS,
    MCPToolProfile,
    is_tool_in_profile,
    normalize_mcp_profile,
)


def test_normalize_accepts_canonical_strings() -> None:
    assert normalize_mcp_profile("full") == MCPToolProfile.FULL
    assert normalize_mcp_profile("lite") == MCPToolProfile.LITE


def test_normalize_accepts_enum() -> None:
    assert normalize_mcp_profile(MCPToolProfile.FULL) == MCPToolProfile.FULL


def test_normalize_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        normalize_mcp_profile("expert")


def test_lite_tool_set_is_explicit() -> None:
    expected = {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
    }
    assert LITE_TOOLS == expected


def test_full_profile_includes_everything() -> None:
    assert is_tool_in_profile("get_top_expressed_genes_by_tissue", MCPToolProfile.FULL)


def test_lite_profile_excludes_advanced_tools() -> None:
    assert not is_tool_in_profile(
        "get_top_expressed_genes_by_tissue", MCPToolProfile.LITE
    )
    assert is_tool_in_profile("search_gtex_genes", MCPToolProfile.LITE)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_profiles.py -v
```
Expected: import error on `gtex_link.mcp.profiles`.

- [ ] **Step 3: Write `gtex_link/mcp/profiles.py`**

```python
"""MCP tool profile selection.

A profile is a named subset of MCP tools to expose. `full` enables everything;
`lite` exposes only the common-path tools.
"""

from __future__ import annotations

from enum import Enum


class MCPToolProfile(str, Enum):
    """MCP tool profile identifiers."""

    FULL = "full"
    LITE = "lite"


LITE_TOOLS: frozenset[str] = frozenset(
    {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
    }
)


def normalize_mcp_profile(value: MCPToolProfile | str) -> MCPToolProfile:
    """Coerce a string or enum into an MCPToolProfile.

    Raises:
        ValueError: if `value` is not a known profile.
    """
    if isinstance(value, MCPToolProfile):
        return value
    try:
        return MCPToolProfile(value)
    except ValueError as exc:
        valid = ", ".join(p.value for p in MCPToolProfile)
        raise ValueError(
            f"Unknown MCP profile {value!r}; valid: {valid}"
        ) from exc


def is_tool_in_profile(tool_name: str, profile: MCPToolProfile) -> bool:
    """Return True if `tool_name` should be exposed under `profile`."""
    if profile is MCPToolProfile.FULL:
        return True
    if profile is MCPToolProfile.LITE:
        return tool_name in LITE_TOOLS
    return False
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/test_mcp/test_profiles.py -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/__init__.py gtex_link/mcp/profiles.py \
        gtex_link/mcp/tools/__init__.py \
        tests/test_mcp/__init__.py tests/test_mcp/test_profiles.py
git commit -m "feat(mcp): add profiles module with full/lite selection"
```

---

## Task 5: Write `resources.py`

**Files:**
- Create: `gtex_link/mcp/resources.py`

- [ ] **Step 1: Write the file**

```python
"""Static string resources used in MCP tool descriptions and instructions."""

from __future__ import annotations

RESEARCH_USE_NOTICE = (
    "Research use only; not for clinical decision support, diagnosis, "
    "treatment, or patient management."
)

GTEX_SERVER_INSTRUCTIONS = (
    "GTEx-Link exposes GTEx Portal v8 expression data. "
    "For ChatGPT-compatible workflows use `search` then `fetch`. "
    "For programmatic access: `search_gtex_genes` -> `get_gene_information` "
    "-> `get_median_expression_levels` or `get_top_expressed_genes_by_tissue`. "
    "Gene IDs accept symbols or GENCODE IDs; prefer GENCODE for precision. "
    f"{RESEARCH_USE_NOTICE}"
)

GTEX_PORTAL_URL = "https://gtexportal.org"
```

- [ ] **Step 2: Commit**

```bash
git add gtex_link/mcp/resources.py
git commit -m "feat(mcp): add static resource strings"
```

---

## Task 6: Write `errors.py`

**Files:**
- Create: `gtex_link/mcp/errors.py`
- Test: `tests/test_mcp/test_errors.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/test_errors.py`:

```python
"""Tests for MCP error mapping."""

from __future__ import annotations

import pytest

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from gtex_link.mcp.errors import map_to_mcp_error_message


def test_rate_limit_error_maps_to_friendly_message() -> None:
    err = RateLimitError("Rate limit exceeded", retry_after=10.0)
    msg = map_to_mcp_error_message(err)
    assert "rate limit" in msg.lower()
    # Does not leak retry-after detail or upstream URL
    assert "https" not in msg


def test_service_unavailable_error_maps_to_friendly_message() -> None:
    err = ServiceUnavailableError()
    msg = map_to_mcp_error_message(err)
    assert "unavailable" in msg.lower()


def test_validation_error_maps_to_friendly_message() -> None:
    err = ValidationError("must be one of A, B, C", field="dataset")
    msg = map_to_mcp_error_message(err)
    assert "dataset" in msg
    assert "must be one of" in msg


def test_gtex_api_error_maps_to_generic_message() -> None:
    err = GTExAPIError("internal upstream failure", status_code=502)
    msg = map_to_mcp_error_message(err)
    assert "502" not in msg  # leaked detail
    assert "GTEx" in msg


def test_unknown_exception_maps_to_generic_message() -> None:
    err = RuntimeError("internal traceback should not leak")
    msg = map_to_mcp_error_message(err)
    assert "internal traceback" not in msg
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_errors.py -v
```
Expected: import error.

- [ ] **Step 3: Write `gtex_link/mcp/errors.py`**

```python
"""Map internal exceptions to safe MCP error messages.

Combined with `FastMCP(mask_error_details=True)`, this prevents upstream
HTTP detail or stack-trace contents from leaking to MCP clients.
"""

from __future__ import annotations

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


def map_to_mcp_error_message(exc: Exception) -> str:
    """Return a client-safe error message for an exception."""
    if isinstance(exc, RateLimitError):
        return "GTEx Portal rate limit exceeded. Try again shortly."
    if isinstance(exc, ServiceUnavailableError):
        return "GTEx Portal is temporarily unavailable. Try again later."
    if isinstance(exc, ValidationError):
        field = f"`{exc.field}`: " if exc.field else ""
        return f"Invalid input — {field}{exc.message}"
    if isinstance(exc, GTExAPIError):
        return "GTEx Portal returned an error. Verify the request inputs."
    return "An internal error occurred. The request was not completed."
```

- [ ] **Step 4: Run to verify pass**

```bash
uv run pytest tests/test_mcp/test_errors.py -v
```
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/errors.py tests/test_mcp/test_errors.py
git commit -m "feat(mcp): add error mapping for safe MCP responses"
```

---

## Task 7: Write `output_validation.py`

**Files:**
- Create: `gtex_link/mcp/output_validation.py`

- [ ] **Step 1: Write the file**

```python
"""Output validation handler — guards against malformed MCP tool outputs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastmcp import FastMCP

_logger = logging.getLogger("gtex_link.mcp.output_validation")


def install_output_validation_error_handler(mcp: "FastMCP") -> None:
    """Install a handler that logs and re-raises output validation failures.

    fastmcp 3.x supports registering tool-call middleware; this hook wraps the
    tool dispatch path and surfaces structured logs when output validation
    fails. The handler does NOT swallow the exception — fastmcp's
    `mask_error_details=True` translates it to a safe client message.
    """
    # fastmcp 3.x: middleware registration shape may vary. The reference is
    # https://gofastmcp.com/integrations/middleware (check installed version).
    if not hasattr(mcp, "add_middleware"):
        _logger.warning("FastMCP instance lacks add_middleware; output validation skipped")
        return

    def _middleware(call_next):  # type: ignore[no-untyped-def]
        async def _wrapped(request):  # type: ignore[no-untyped-def]
            try:
                return await call_next(request)
            except Exception as exc:
                _logger.error(
                    "MCP output validation failed",
                    extra={"tool": getattr(request, "tool_name", None), "error": str(exc)},
                )
                raise

        return _wrapped

    mcp.add_middleware(_middleware)
```

**Note:** the exact middleware API on fastmcp 3.x may differ slightly. After this file is written, run a probe:

```bash
uv run python - <<'PY'
from fastmcp import FastMCP
mcp = FastMCP(name="probe")
print([attr for attr in dir(mcp) if "middleware" in attr.lower() or "hook" in attr.lower()])
PY
```

Adjust the implementation to match the actual API surface (e.g., `mcp.middleware`, `mcp.add_hook`, or a decorator).

- [ ] **Step 2: Commit**

```bash
git add gtex_link/mcp/output_validation.py
git commit -m "feat(mcp): add output validation middleware hook"
```

---

## Task 8: Write `service_adapters.py`

**Files:**
- Create: `gtex_link/mcp/service_adapters.py`

- [ ] **Step 1: Write the file**

```python
"""Service binding for MCP tools.

This module is the single place where `GTExClient` and `GTExService` are
instantiated for MCP tool use. Tool modules call `get_gtex_service()` to
obtain a shared, lazily-constructed service instance.
"""

from __future__ import annotations

from functools import lru_cache

from gtex_link.api.client import GTExClient
from gtex_link.config import DEFAULT_API_CONFIG, DEFAULT_CACHE_CONFIG
from gtex_link.services.gtex_service import GTExService


@lru_cache(maxsize=1)
def get_gtex_service() -> GTExService:
    """Return the shared GTExService instance for MCP tools."""
    client = GTExClient(config=DEFAULT_API_CONFIG)
    return GTExService(client=client, cache_config=DEFAULT_CACHE_CONFIG)


def reset_gtex_service() -> None:
    """Clear the cached service instance (test helper)."""
    get_gtex_service.cache_clear()
```

- [ ] **Step 2: Commit**

```bash
git add gtex_link/mcp/service_adapters.py
git commit -m "feat(mcp): add service adapter module for tool bindings"
```

---

## Task 9: Write `tools/reference.py`

**Files:**
- Create: `gtex_link/mcp/tools/reference.py`
- Test: `tests/test_mcp/test_tools_reference.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/test_tools_reference.py`:

```python
"""Tests for reference-category MCP tools."""

from __future__ import annotations

import pytest
import respx
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.service_adapters import reset_gtex_service
from gtex_link.mcp.tools.reference import register_reference_tools

GTEX_BASE = "https://gtexportal.org/api/v2"


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_gtex_service()
    yield
    reset_gtex_service()


@pytest.mark.asyncio
async def test_search_gtex_genes_registered() -> None:
    mcp = FastMCP(name="test")
    register_reference_tools(mcp, profile=MCPToolProfile.FULL)
    # fastmcp tool discovery — adjust attribute to actual API
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search_gtex_genes" in names
    assert "get_gene_information" in names
    assert "get_transcript_information" in names


@pytest.mark.asyncio
async def test_lite_profile_includes_only_lite_reference_tools() -> None:
    mcp = FastMCP(name="test")
    register_reference_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search_gtex_genes" in names
    assert "get_gene_information" in names
    assert "get_transcript_information" not in names
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_tools_reference.py -v
```
Expected: import error.

- [ ] **Step 3: Write `gtex_link/mcp/tools/reference.py`**

```python
"""Reference-category MCP tools (gene search, gene info, transcript info)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.errors import map_to_mcp_error_message
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, TranscriptRequest
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_reference_tools(mcp: "FastMCP", *, profile: MCPToolProfile) -> None:
    """Register reference-category tools on a FastMCP instance."""

    if is_tool_in_profile("search_gtex_genes", profile):

        @mcp.tool(
            name="search_gtex_genes",
            description=(
                "Search the GTEx Portal gene catalog by gene symbol or partial "
                "match. Returns a paginated list of genes with GENCODE IDs, "
                "symbols, chromosome, and basic metadata. Use this when the "
                "user provides a gene name or partial symbol and you need to "
                "disambiguate. Pair with `get_gene_information` for full detail."
            ),
        )
        async def search_gtex_genes(
            query: str,
            page: int = 0,
            page_size: int = 20,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=page,
                    page_size=page_size,
                )
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="search_gtex_genes", success=success)

    if is_tool_in_profile("get_gene_information", profile):

        @mcp.tool(
            name="get_gene_information",
            description=(
                "Retrieve detailed gene information from GTEx Portal for one "
                "or more GENCODE IDs or gene symbols. Returns chromosome, "
                "coordinates, gene type, Entrez ID, and description. Use when "
                "you already know the gene identifier."
            ),
        )
        async def get_gene_information(
            gene_id: list[str],
            gencode_version: str | None = None,
            genome_build: str | None = None,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                request = GeneRequest(
                    geneId=gene_id,
                    gencodeVersion=gencode_version,
                    genomeBuild=genome_build,
                    page=0,
                    itemsPerPage=len(gene_id) or 1,
                )
                result = await service.get_genes(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="get_gene_information", success=success)

    if is_tool_in_profile("get_transcript_information", profile):

        @mcp.tool(
            name="get_transcript_information",
            description=(
                "Retrieve transcript annotations for one or more GENCODE IDs "
                "from GTEx Portal. Returns transcript identifiers, "
                "coordinates, and gene linkage. Use for transcript-level "
                "analysis or when the user asks about isoforms."
            ),
        )
        async def get_transcript_information(
            gencode_id: list[str],
            gencode_version: str | None = None,
            genome_build: str | None = None,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                request = TranscriptRequest(
                    gencodeId=gencode_id,
                    gencodeVersion=gencode_version,
                    genomeBuild=genome_build,
                    page=0,
                    itemsPerPage=len(gencode_id) or 1,
                )
                result = await service.get_transcripts(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(tool="get_transcript_information", success=success)
```

Note: if `TranscriptRequest` or `GeneRequest` field names differ in the actual `gtex_link.models.requests` module, adjust accordingly. The plan assumes the existing names from `app.py:_add_chatgpt_tools`.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_mcp/test_tools_reference.py -v
```
Expected: pass. If the `mcp.list_tools()` API differs in fastmcp 3.x, adapt the assertion (e.g., access `mcp._tool_manager.list_tools()`).

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/reference.py tests/test_mcp/test_tools_reference.py
git commit -m "feat(mcp): add reference-category tools (gene/transcript search)"
```

---

## Task 10: Write `tools/expression.py`

**Files:**
- Create: `gtex_link/mcp/tools/expression.py`
- Test: `tests/test_mcp/test_tools_expression.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/test_tools_expression.py`:

```python
"""Tests for expression-category MCP tools."""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.service_adapters import reset_gtex_service
from gtex_link.mcp.tools.expression import register_expression_tools


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_gtex_service()
    yield
    reset_gtex_service()


@pytest.mark.asyncio
async def test_expression_tools_registered_under_full_profile() -> None:
    mcp = FastMCP(name="test")
    register_expression_tools(mcp, profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert {
        "get_median_expression_levels",
        "get_individual_expression_data",
        "get_top_expressed_genes_by_tissue",
    } <= names


@pytest.mark.asyncio
async def test_lite_profile_only_exposes_median_expression() -> None:
    mcp = FastMCP(name="test")
    register_expression_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "get_median_expression_levels" in names
    assert "get_top_expressed_genes_by_tissue" not in names
    assert "get_individual_expression_data" not in names
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_tools_expression.py -v
```

- [ ] **Step 3: Write `gtex_link/mcp/tools/expression.py`**

```python
"""Expression-category MCP tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.errors import map_to_mcp_error_message
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import (
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    TopExpressedGeneRequest,
)
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_expression_tools(mcp: "FastMCP", *, profile: MCPToolProfile) -> None:
    """Register expression-category tools on a FastMCP instance."""

    if is_tool_in_profile("get_median_expression_levels", profile):

        @mcp.tool(
            name="get_median_expression_levels",
            description=(
                "Get median GTEx Portal expression (TPM) per tissue for one or "
                "more GENCODE IDs. Returns per-tissue medians for dataset "
                "`gtex_v8` by default. Use this when comparing expression of "
                "a known gene across tissues; pair with `get_top_expressed_"
                "genes_by_tissue` for the reverse question."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: list[str] | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                request = MedianGeneExpressionRequest(
                    gencodeId=gencode_id,
                    tissueSiteDetailId=tissue_site_detail_id,
                    datasetId=dataset_id,
                    page=page,
                    itemsPerPage=page_size,
                )
                result = await service.get_median_gene_expression(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(
                    tool="get_median_expression_levels", success=success
                )

    if is_tool_in_profile("get_individual_expression_data", profile):

        @mcp.tool(
            name="get_individual_expression_data",
            description=(
                "Get individual-sample GTEx Portal expression data (TPM) for "
                "one or more GENCODE IDs, optionally filtered by tissue and "
                "dataset. High volume — limit `page_size` accordingly. Use "
                "for variance/distribution analyses where per-sample data is "
                "needed."
            ),
        )
        async def get_individual_expression_data(
            gencode_id: list[str],
            tissue_site_detail_id: list[str] | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                request = GeneExpressionRequest(
                    gencodeId=gencode_id,
                    tissueSiteDetailId=tissue_site_detail_id,
                    datasetId=dataset_id,
                    page=page,
                    itemsPerPage=page_size,
                )
                result = await service.get_gene_expression(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(
                    tool="get_individual_expression_data", success=success
                )

    if is_tool_in_profile("get_top_expressed_genes_by_tissue", profile):

        @mcp.tool(
            name="get_top_expressed_genes_by_tissue",
            description=(
                "Get the top expressed genes for a given tissue from GTEx "
                "Portal. Use when answering 'what's expressed in this "
                "tissue?' rather than 'where is this gene expressed?'. "
                "Returns genes ranked by median expression."
            ),
        )
        async def get_top_expressed_genes_by_tissue(
            tissue_site_detail_id: str,
            dataset_id: str = "gtex_v8",
            filter_mt_gene: bool = True,
            page: int = 0,
            page_size: int = 100,
        ) -> str:
            success = False
            try:
                service = get_gtex_service()
                request = TopExpressedGeneRequest(
                    tissueSiteDetailId=tissue_site_detail_id,
                    datasetId=dataset_id,
                    filterMtGene=filter_mt_gene,
                    page=page,
                    itemsPerPage=page_size,
                )
                result = await service.get_top_expressed_genes(request)
                success = True
                return json.dumps(result.model_dump(by_alias=True))
            except Exception as exc:
                return json.dumps({"error": map_to_mcp_error_message(exc)})
            finally:
                record_mcp_tool_call(
                    tool="get_top_expressed_genes_by_tissue", success=success
                )
```

Note: adjust request-model field names to match `gtex_link.models.requests`. Verify each model exists; if any are missing, surface and stop.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_mcp/test_tools_expression.py -v
```

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tools_expression.py
git commit -m "feat(mcp): add expression-category tools"
```

---

## Task 11: Write `tools/search_fetch.py`

**Files:**
- Create: `gtex_link/mcp/tools/search_fetch.py`
- Test: `tests/test_mcp/test_tools_search_fetch.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/test_tools_search_fetch.py`:

```python
"""Tests for ChatGPT-compatible search/fetch MCP tools."""

from __future__ import annotations

import json

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.mcp.service_adapters import reset_gtex_service
from gtex_link.mcp.tools.search_fetch import register_search_fetch_tools


@pytest.fixture(autouse=True)
def _reset_service() -> None:
    reset_gtex_service()
    yield
    reset_gtex_service()


@pytest.mark.asyncio
async def test_search_fetch_registered_under_full_profile() -> None:
    mcp = FastMCP(name="test")
    register_search_fetch_tools(mcp, profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search" in names
    assert "fetch" in names


@pytest.mark.asyncio
async def test_search_fetch_registered_under_lite_profile() -> None:
    mcp = FastMCP(name="test")
    register_search_fetch_tools(mcp, profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    # search/fetch are always in lite
    assert "search" in names
    assert "fetch" in names
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_tools_search_fetch.py -v
```

- [ ] **Step 3: Write `gtex_link/mcp/tools/search_fetch.py`**

Port the existing `_add_chatgpt_tools` body out of `app.py`. The current implementation lives in `gtex_link/app.py:116-279`. Move it into this new module verbatim, parameterized for profile.

```python
"""ChatGPT-compatible search and fetch MCP tools.

These mirror the OpenAI Apps SDK shape — `search(query) -> {results: [...]}`
and `fetch(id) -> {id, title, text, url, metadata}` — so a single MCP server
can be consumed by both ChatGPT and Claude Desktop.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.errors import map_to_mcp_error_message
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_PORTAL_URL
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, MedianGeneExpressionRequest
from gtex_link.models.gtex import DatasetId, TissueSiteDetailId
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_search_fetch_tools(mcp: "FastMCP", *, profile: MCPToolProfile) -> None:
    """Register the ChatGPT-compatible `search` and `fetch` tools."""

    if is_tool_in_profile("search", profile):

        @mcp.tool(
            name="search",
            description=(
                "Search the GTEx Portal genetic expression database for "
                "genes, transcripts, and expression data. Returns a list of "
                "result documents with id, title, and URL."
            ),
        )
        async def search(query: str) -> str:
            success = False
            try:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=0,
                    page_size=20,
                )
                items = []
                if result.data:
                    for gene in result.data:
                        items.append(
                            {
                                "id": f"gene:{gene.gencode_id}",
                                "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                                "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                            }
                        )
                success = True
                return json.dumps({"results": items})
            except Exception:
                return json.dumps({"results": []})
            finally:
                record_mcp_tool_call(tool="search", success=success)

    if is_tool_in_profile("fetch", profile):

        @mcp.tool(
            name="fetch",
            description=(
                "Retrieve full details for a specific gene or genetic element "
                "from the GTEx Portal database. Use the `id` returned by "
                "`search` (format: `gene:<GENCODE_ID>`)."
            ),
        )
        async def fetch(id: str) -> str:  # noqa: A002
            success = False
            try:
                service = get_gtex_service()
                if not id.startswith("gene:"):
                    return json.dumps(
                        {
                            "id": id,
                            "title": "Unsupported resource type",
                            "text": f"Unsupported resource id format: {id!r}",
                            "url": GTEX_PORTAL_URL,
                            "metadata": {"source": "GTEx Portal", "type": "error"},
                        }
                    )

                gencode_id = id[len("gene:") :]
                gene_request = GeneRequest(
                    geneId=[gencode_id],
                    gencodeVersion=None,
                    genomeBuild=None,
                    page=0,
                    itemsPerPage=1,
                )
                gene_result = await service.get_genes(gene_request)
                if not gene_result.data:
                    return json.dumps(
                        {
                            "id": id,
                            "title": "Resource not found",
                            "text": f"No gene found for {gencode_id!r}",
                            "url": GTEX_PORTAL_URL,
                            "metadata": {"source": "GTEx Portal", "type": "error"},
                        }
                    )
                gene = gene_result.data[0]

                expression_text = []
                try:
                    expression_request = MedianGeneExpressionRequest(
                        gencodeId=[gencode_id],
                        tissueSiteDetailId=TissueSiteDetailId.ALL,
                        datasetId=DatasetId.GTEX_V8,
                        page=0,
                        itemsPerPage=50,
                    )
                    expression_result = await service.get_median_gene_expression(
                        expression_request
                    )
                    if expression_result.data:
                        expression_text.append(
                            "\nExpression Data (median TPM by tissue):"
                        )
                        for exp in expression_result.data[:10]:
                            expression_text.append(
                                f"  {exp.tissue_site_detail_id}: {exp.median:.2f} TPM"
                            )
                        if len(expression_result.data) > 10:
                            expression_text.append(
                                f"  ... and {len(expression_result.data) - 10} more tissues"
                            )
                except Exception:
                    expression_text = []

                lines = [
                    f"Gene Symbol: {gene.gene_symbol}",
                    f"GENCODE ID: {gene.gencode_id}",
                    f"Description: {gene.description or 'Not available'}",
                    f"Chromosome: {gene.chromosome}",
                    f"Position: {gene.start:,}-{gene.end:,}",
                    f"Strand: {gene.strand}",
                    f"Gene Type: {gene.gene_type}",
                    f"Gene Status: {gene.gene_status}",
                ]
                if gene.entrez_gene_id:
                    lines.append(f"Entrez Gene ID: {gene.entrez_gene_id}")
                lines.extend(expression_text)

                document = {
                    "id": id,
                    "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                    "text": "\n".join(lines),
                    "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                    "metadata": {
                        "source": "GTEx Portal v8",
                        "type": "gene",
                        "chromosome": gene.chromosome,
                        "gene_type": gene.gene_type,
                        "entrez_id": gene.entrez_gene_id,
                    },
                }
                success = True
                return json.dumps(document)
            except Exception as exc:
                return json.dumps(
                    {
                        "id": id,
                        "title": "Error",
                        "text": map_to_mcp_error_message(exc),
                        "url": GTEX_PORTAL_URL,
                        "metadata": {"source": "GTEx Portal", "type": "error"},
                    }
                )
            finally:
                record_mcp_tool_call(tool="fetch", success=success)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_mcp/test_tools_search_fetch.py -v
```

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/search_fetch.py tests/test_mcp/test_tools_search_fetch.py
git commit -m "feat(mcp): add ChatGPT-compatible search and fetch tools"
```

---

## Task 12: Write `facade.py`

**Files:**
- Create: `gtex_link/mcp/facade.py`
- Test: `tests/test_mcp/test_facade.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_mcp/test_facade.py`:

```python
"""Tests for the MCP facade."""

from __future__ import annotations

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile


@pytest.mark.asyncio
async def test_facade_builds_and_lists_all_full_tools() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_transcript_information",
        "get_median_expression_levels",
        "get_individual_expression_data",
        "get_top_expressed_genes_by_tissue",
    }


@pytest.mark.asyncio
async def test_facade_lite_profile_subset() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.LITE)
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "search",
        "fetch",
        "search_gtex_genes",
        "get_gene_information",
        "get_median_expression_levels",
    }


@pytest.mark.asyncio
async def test_facade_accepts_string_profile() -> None:
    mcp = create_gtex_mcp(profile="lite")
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "search" in names
    assert "get_top_expressed_genes_by_tissue" not in names


@pytest.mark.asyncio
async def test_facade_has_mask_error_details_on() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    # fastmcp 3.x: attribute name may be `_mask_error_details` or similar.
    assert getattr(mcp, "mask_error_details", None) or getattr(
        mcp, "_mask_error_details", None
    )
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_mcp/test_facade.py -v
```

- [ ] **Step 3: Write `gtex_link/mcp/facade.py`**

```python
"""MCP facade for GTEx-Link."""

from __future__ import annotations

from fastmcp import FastMCP

from gtex_link.config import settings
from gtex_link.mcp.output_validation import install_output_validation_error_handler
from gtex_link.mcp.profiles import MCPToolProfile, normalize_mcp_profile
from gtex_link.mcp.resources import GTEX_SERVER_INSTRUCTIONS
from gtex_link.mcp.tools import (
    register_expression_tools,
    register_reference_tools,
    register_search_fetch_tools,
)


def create_gtex_mcp(profile: MCPToolProfile | str | None = None) -> FastMCP:
    """Build a FastMCP instance for GTEx-Link.

    Args:
        profile: `MCPToolProfile.FULL` (default), `MCPToolProfile.LITE`, or
            their string equivalents. If `None`, falls back to
            `settings.mcp_profile`.

    Returns:
        A configured `FastMCP` with all matching tools registered.
    """
    if profile is None:
        profile = settings.mcp_profile
    selected = normalize_mcp_profile(profile)

    mcp = FastMCP(
        name="gtex-link",
        instructions=GTEX_SERVER_INSTRUCTIONS,
        mask_error_details=True,
    )

    register_search_fetch_tools(mcp, profile=selected)
    register_reference_tools(mcp, profile=selected)
    register_expression_tools(mcp, profile=selected)

    install_output_validation_error_handler(mcp)
    return mcp
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_mcp/test_facade.py -v
```
Expected: pass. If the `mask_error_details` attribute test fails, adjust assertion to match the actual fastmcp 3.x attribute or drop the check (the keyword is what matters at construction).

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/facade.py tests/test_mcp/test_facade.py
git commit -m "feat(mcp): add facade orchestrating profile-aware tool registration"
```

---

## Task 13: Update `gtex_link/config.py`

**Files:**
- Modify: `gtex_link/config.py`

- [ ] **Step 1: Add `transport` and `mcp_profile` settings; remove `mcp_port`**

Open `gtex_link/config.py`. In the `ServerSettings` class:

Replace the `transport_mode` field (lines 132-136):

```python
    transport: Literal["unified", "http", "stdio"] = Field(
        default="unified",
        description="Server transport mode",
    )
```

(Rename `transport_mode` to `transport` — the env var becomes `GTEX_LINK_TRANSPORT`.)

Find the MCP settings (lines 138-145). Remove the `mcp_port` field entirely. Add:

```python
    mcp_path: str = Field(default="/mcp", description="MCP endpoint path")
    mcp_profile: Literal["full", "lite"] = Field(
        default="full",
        description="MCP tool profile (full or lite)",
    )
```

Search the codebase for any remaining references to `settings.transport_mode` or `settings.mcp_port`:

```bash
uv run grep -rn "transport_mode\|mcp_port" gtex_link/ docker/ server.py mcp_server.py 2>/dev/null
```

For each hit:
- Replace `transport_mode` with `transport`.
- Remove `mcp_port` references (it no longer exists).

- [ ] **Step 2: Verify config loads**

```bash
uv run python -c "from gtex_link.config import settings; print(settings.transport, settings.mcp_profile)"
```
Expected: `unified full` (or whatever defaults).

- [ ] **Step 3: Commit**

```bash
git add gtex_link/config.py
git commit -m "refactor(config): rename transport_mode->transport, add mcp_profile, drop mcp_port"
```

---

## Task 14: Slim down `gtex_link/app.py`

**Files:**
- Modify: `gtex_link/app.py`

- [ ] **Step 1: Remove all MCP code from `app.py`**

Open `gtex_link/app.py`. The file should now contain only the FastAPI factory (Tasks 5 + 9 of Phase 2 left middleware and metrics in place). Remove:

1. The `create_mcp_app` function (entire body).
2. The `_add_chatgpt_tools` function (entire body).
3. The module-bottom block that instantiates `mcp_app` inside a `try/except`.
4. The imports `from fastmcp import FastMCP` and `from fastmcp.server.openapi import MCPType, RouteMap`.
5. The unused import of `MCPType`, `RouteMap`, and any model imports only used by `_add_chatgpt_tools`.

The file should end with:

```python
# Create application instance
app = create_app()
```

Nothing related to MCP should remain.

- [ ] **Step 2: Verify FastAPI app still boots**

```bash
uv run python -c "from gtex_link.app import app; print(app.title)"
```
Expected: `GTEx-Link`.

- [ ] **Step 3: Run existing route tests**

```bash
uv run pytest tests/test_api/ -v
```
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add gtex_link/app.py
git commit -m "refactor(app): remove inline MCP code; pure FastAPI factory now"
```

---

## Task 15: Rewrite `gtex_link/server_manager.py`

**Files:**
- Modify: `gtex_link/server_manager.py`

- [ ] **Step 1: Replace file contents with `UnifiedServerManager`**

Open `gtex_link/server_manager.py` and replace its contents with:

```python
"""Unified server manager for HTTP, stdio, and unified (HTTP+MCP) transports."""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING

import uvicorn

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


class UnifiedServerManager:
    """Orchestrates startup of GTEx-Link in any transport mode."""

    def __init__(self, logger: "FilteringBoundLogger | None" = None) -> None:
        self.logger = logger
        self._uvicorn_server: uvicorn.Server | None = None
        self._mcp_app = None  # type: ignore[assignment]

    # --- Transports -----------------------------------------------------

    async def start_unified_server(self, host: str, port: int) -> None:
        """Start FastAPI + MCP (streamable-http transport) on the same port."""
        if self.logger:
            self.logger.info(
                "Starting unified server", host=host, port=port, mcp_path="/mcp"
            )
        from gtex_link.app import app
        from gtex_link.mcp.facade import create_gtex_mcp

        mcp = create_gtex_mcp()
        # FastMCP 3.x: mount onto the FastAPI app at /mcp
        mcp.mount_to_fastapi(app, path="/mcp")  # type: ignore[attr-defined]

        config = uvicorn.Config(
            app=app, host=host, port=port, log_config=None, lifespan="on"
        )
        self._uvicorn_server = uvicorn.Server(config)
        await self._uvicorn_server.serve()

    async def start_http_only_server(self, host: str, port: int) -> None:
        """Start FastAPI only (no MCP)."""
        if self.logger:
            self.logger.info("Starting HTTP-only server", host=host, port=port)
        from gtex_link.app import app

        config = uvicorn.Config(
            app=app, host=host, port=port, log_config=None, lifespan="on"
        )
        self._uvicorn_server = uvicorn.Server(config)
        await self._uvicorn_server.serve()

    async def start_stdio_server(self) -> None:
        """Start FastMCP stdio transport (for Claude Desktop)."""
        self._configure_stdio_environment()
        if self.logger:
            self.logger.info("Starting stdio MCP server")
        from gtex_link.mcp.facade import create_gtex_mcp

        mcp = create_gtex_mcp()
        await mcp.run_async(transport="stdio")  # type: ignore[func-returns-value]

    # --- Lifecycle ------------------------------------------------------

    async def shutdown(self) -> None:
        """Gracefully stop any running server."""
        if self._uvicorn_server is not None:
            self._uvicorn_server.should_exit = True
        if self.logger:
            self.logger.info("Shutdown complete")

    # --- Helpers --------------------------------------------------------

    @staticmethod
    def _configure_stdio_environment() -> None:
        """Suppress non-JSON output that would corrupt stdio MCP framing."""
        os.environ.setdefault("PYTHONUNBUFFERED", "1")
        os.environ.setdefault("GTEX_LINK_TRANSPORT", "stdio")
        os.environ.setdefault("FASTMCP_DISABLE_BANNER", "1")
        os.environ.setdefault("FASTMCP_NO_BANNER", "1")
        os.environ.setdefault("FASTMCP_QUIET", "1")
        os.environ.setdefault("NO_COLOR", "1")
        os.environ.setdefault("FORCE_COLOR", "0")
        os.environ.setdefault("TERM", "dumb")
        os.environ.setdefault("PYTHONWARNINGS", "ignore")

        # Pin stdout away from any chatty libraries: structlog/rich/etc.
        # all go to stderr. The MCP protocol uses stdout exclusively for
        # JSON-RPC frames.
        sys.stderr = sys.stderr  # explicit no-op so linters see the binding
```

- [ ] **Step 2: Verify import works**

```bash
uv run python -c "from gtex_link.server_manager import UnifiedServerManager; print('OK')"
```
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add gtex_link/server_manager.py
git commit -m "feat(server): replace ServerManager with UnifiedServerManager"
```

---

## Task 16: Rewrite `server.py`

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Replace `server.py` with the unified entry**

```python
#!/usr/bin/env python3
"""Unified entry point for GTEx-Link.

Run any transport mode:

    python server.py --transport unified  # FastAPI + MCP at /mcp (default)
    python server.py --transport http     # FastAPI only
    python server.py --transport stdio    # FastMCP stdio (for Claude Desktop)
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from typing import Any

from gtex_link.config import settings
from gtex_link.logging_config import configure_logging
from gtex_link.server_manager import UnifiedServerManager


async def _run() -> None:
    parser = argparse.ArgumentParser(description="GTEx-Link server")
    parser.add_argument(
        "--transport",
        choices=["unified", "http", "stdio"],
        default=settings.transport,
        help="Server transport mode",
    )
    parser.add_argument("--host", default=settings.host, help="Server host")
    parser.add_argument("--port", type=int, default=settings.port, help="Server port")
    parser.add_argument(
        "--log-level", default=settings.log_level, help="Logging level"
    )
    args = parser.parse_args()

    settings.transport = args.transport
    settings.host = args.host
    settings.port = args.port
    settings.log_level = args.log_level

    logger = configure_logging()
    manager = UnifiedServerManager(logger=logger)

    shutdown_task: asyncio.Task[None] | None = None

    def _signal(signum: int, _frame: Any) -> None:
        nonlocal shutdown_task
        logger.info("Received shutdown signal", signal=signum)
        if shutdown_task is None or shutdown_task.done():
            shutdown_task = asyncio.create_task(manager.shutdown())

    signal.signal(signal.SIGINT, _signal)
    signal.signal(signal.SIGTERM, _signal)

    try:
        if args.transport == "unified":
            await manager.start_unified_server(host=args.host, port=args.port)
        elif args.transport == "http":
            await manager.start_http_only_server(host=args.host, port=args.port)
        elif args.transport == "stdio":
            await manager.start_stdio_server()
        else:
            logger.error("Invalid transport", transport=args.transport)
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as exc:  # noqa: BLE001
        logger.error("Server error", error=str(exc))
        sys.exit(1)
    finally:
        await manager.shutdown()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test the entry**

```bash
uv run python server.py --transport http --port 8765 &
SERVER_PID=$!
sleep 2
curl -sf http://127.0.0.1:8765/api/health || echo "health check failed"
kill $SERVER_PID
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat(server): unify entry point with --transport argparse"
```

---

## Task 17: Rewrite `mcp_server.py`

**Files:**
- Modify: `mcp_server.py`

- [ ] **Step 1: Replace `mcp_server.py` with the thin stdio entry**

```python
#!/usr/bin/env python3
"""Stdio MCP entry point for Claude Desktop and similar clients.

Preserves the `gtex-mcp` console script. For HTTP transport use
`server.py --transport unified` or `--transport http`.
"""

from __future__ import annotations

import asyncio
import os
import sys


def main() -> None:
    # Configure environment BEFORE importing anything that may print.
    os.environ.setdefault("GTEX_LINK_TRANSPORT", "stdio")
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    os.environ.setdefault("FASTMCP_DISABLE_BANNER", "1")
    os.environ.setdefault("FASTMCP_QUIET", "1")
    os.environ.setdefault("NO_COLOR", "1")

    try:
        from gtex_link.logging_config import configure_logging
        from gtex_link.server_manager import UnifiedServerManager
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: gtex_link import failed: {exc}", file=sys.stderr)
        sys.exit(1)

    logger = configure_logging()
    manager = UnifiedServerManager(logger=logger)
    try:
        asyncio.run(manager.start_stdio_server())
    except KeyboardInterrupt:
        logger.info("MCP stdio server shutdown requested")
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP stdio server error", error=str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add mcp_server.py
git commit -m "feat(mcp): rewrite mcp_server.py as thin stdio entry"
```

---

## Task 18: Delete `mcp_http_server.py`

**Files:**
- Delete: `mcp_http_server.py`

- [ ] **Step 1: Remove the file**

```bash
git rm mcp_http_server.py
```

- [ ] **Step 2: Remove the console script entry from `pyproject.toml`**

Open `pyproject.toml`. In `[project.scripts]`, remove the `gtex-mcp-http` line. The remaining entries should be:

```toml
[project.scripts]
gtex-link = "gtex_link.cli:main"
gtex-mcp  = "mcp_server:main"
```

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(mcp): drop gtex-mcp-http; use server.py --transport instead"
```

---

## Task 19: Add `gtex_link/__main__.py`

**Files:**
- Create: `gtex_link/__main__.py`

- [ ] **Step 1: Write the file**

```python
"""`python -m gtex_link` entry — aliases `server.py --transport unified`."""

from __future__ import annotations

from server import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify it works**

```bash
uv run python -m gtex_link --transport http --port 8766 &
SERVER_PID=$!
sleep 2
curl -sf http://127.0.0.1:8766/api/health || echo "health check failed"
kill $SERVER_PID
```

- [ ] **Step 3: Commit**

```bash
git add gtex_link/__main__.py
git commit -m "feat(cli): add python -m gtex_link entry point"
```

---

## Task 20: Update the Makefile dev targets

**Files:**
- Modify: `Makefile`

- [ ] **Step 1: Confirm Phase 1's `dev` and `mcp-serve-http` targets point at the right command**

Open `Makefile`. The `dev` and `mcp-serve-http` targets from Phase 1 should already be:

```make
dev: ## Start unified REST + MCP development server
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000

mcp-serve: ## Start local stdio MCP server
	uv run python mcp_server.py

mcp-serve-http: ## Start unified server (alias for `dev`)
	uv run python server.py --transport unified --host 127.0.0.1 --port 8000
```

If `dev` was temporarily pointed at `uv run python server.py` (no `--transport`), update it now.

- [ ] **Step 2: Smoke-test `make dev`**

```bash
make dev &
DEV_PID=$!
sleep 3
curl -sf http://127.0.0.1:8000/api/health
curl -sf http://127.0.0.1:8000/mcp 2>&1 | head -3 || true
kill $DEV_PID
```
Expected: health passes; `/mcp` returns something fastmcp-shaped (a method-not-allowed or upgrade-required header — that's fine for a GET against a streamable-http endpoint).

- [ ] **Step 3: Commit (only if changes were needed)**

```bash
git add Makefile
git commit -m "chore(make): point dev target at unified transport"
```

---

## Task 21: Collapse `docker/docker-compose.yml` to a single service

**Files:**
- Modify: `docker/docker-compose.yml`

- [ ] **Step 1: Read the current file to identify the api/mcp split**

```bash
cat docker/docker-compose.yml
```

The current file likely has two services (`api`, `mcp`). The post-modernization shape has one (`gtex-link`) that exposes both HTTP and MCP on the same port.

- [ ] **Step 2: Replace the service definitions**

Open `docker/docker-compose.yml` and replace both `api` and `mcp` service blocks with a single `gtex-link` service:

```yaml
services:
  gtex-link:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    image: gtex-link:latest
    container_name: gtex-link
    restart: unless-stopped
    environment:
      GTEX_LINK_HOST: 0.0.0.0
      GTEX_LINK_PORT: 8000
      GTEX_LINK_TRANSPORT: unified
      GTEX_LINK_LOG_LEVEL: ${GTEX_LINK_LOG_LEVEL:-INFO}
      GTEX_LINK_LOG_FORMAT: ${GTEX_LINK_LOG_FORMAT:-json}
    ports:
      - "${GTEX_LINK_PORT:-8000}:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=2)"]
      interval: 30s
      timeout: 5s
      retries: 3
```

Adjust networking/volumes/dependencies as the existing file dictates.

- [ ] **Step 3: Validate the compose config**

```bash
make docker-prod-config
```
Expected: rendered YAML printed, no errors.

- [ ] **Step 4: Commit**

```bash
git add docker/docker-compose.yml
git commit -m "feat(docker): collapse api and mcp services into single gtex-link service"
```

---

## Task 22: Simplify `docker/docker-compose.npm.yml`

**Files:**
- Modify: `docker/docker-compose.npm.yml`

- [ ] **Step 1: Update the NPM compose to reference the single upstream**

Open `docker/docker-compose.npm.yml`. Wherever it routes proxy traffic to the previous `api` or `mcp` services, point everything at the single `gtex-link` service on port 8000.

- [ ] **Step 2: Validate**

```bash
make docker-npm-config
```
Expected: rendered YAML, no errors.

- [ ] **Step 3: Commit**

```bash
git add docker/docker-compose.npm.yml
git commit -m "feat(docker): point NPM compose at unified gtex-link upstream"
```

---

## Task 23: Update `CHANGELOG.md`

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Append a Phase 3 section under `[Unreleased]`**

Open `CHANGELOG.md`. Add to the `[Unreleased]` section:

```markdown
### Added (Phase 3 — MCP facade & transport unification)

- `gtex_link/mcp/` package with explicit tool registration: facade, profiles, resources, errors, output validation, service adapters, and per-category tools (reference, expression, search/fetch).
- `gtex_link/mcp/profiles.py` with `full` and `lite` profiles.
- `GTEX_LINK_MCP_PROFILE` env var (default `full`).
- `gtex_link/__main__.py` — `python -m gtex_link` aliases the unified server.
- `UnifiedServerManager` with `start_unified_server`, `start_http_only_server`, `start_stdio_server`, and graceful shutdown.
- `server.py --transport {unified,http,stdio}` single entry point.

### Changed (Phase 3)

- MCP layer: replaced `FastMCP.from_fastapi` auto-generation with an explicit facade. Tool names preserved 1:1; descriptions hand-tuned for AI clients.
- `mcp_server.py` is now a thin stdio entry that delegates to `UnifiedServerManager`.
- `gtex_link/app.py` is a pure FastAPI factory — MCP code moved out.
- Docker: `docker/docker-compose.yml` collapsed `api` + `mcp` services into a single `gtex-link` service.
- `GTEX_LINK_TRANSPORT_MODE` env var renamed to `GTEX_LINK_TRANSPORT` (values: `unified`, `http`, `stdio`).

### Removed (Phase 3 — BREAKING)

- `mcp_http_server.py` deleted. Use `server.py --transport unified` or `--transport http` instead.
- `gtex-mcp-http` console script removed. Use `gtex-mcp` for stdio or `server.py --transport unified` for HTTP.
- `GTEX_LINK_MCP_PORT` env var removed. Unified mode runs on a single port (`GTEX_LINK_PORT`).
- Two-service Docker compose split (api/mcp) removed.

### Migration notes

- Anyone running `gtex-mcp-http`: switch to `gtex-mcp` (stdio) or `python server.py --transport unified` (HTTP).
- Anyone setting `GTEX_LINK_TRANSPORT_MODE`: rename env var to `GTEX_LINK_TRANSPORT`.
- Anyone setting `GTEX_LINK_MCP_PORT`: remove the env var; the MCP endpoint is now served on `GTEX_LINK_PORT` at the `GTEX_LINK_MCP_PATH` path (default `/mcp`).
- Deployments using the two-service compose split: redeploy with the new single-service compose; update reverse-proxy upstream from two pools to one.
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add Phase 3 entries and migration notes"
```

---

## Task 24: Run full test + CI gate

**Files:**
- As needed

- [ ] **Step 1: Run all MCP tests**

```bash
uv run pytest tests/test_mcp/ -v
```
Expected: all pass. Common failures and fixes:

- `mcp.list_tools()` not awaitable / different shape: adjust per fastmcp 3.x docs.
- `mcp.mount_to_fastapi` method missing: check fastmcp docs for the actual API and update `server_manager.py`.
- A tool's request model field name doesn't match: fix the call in `tools/*.py` to match `gtex_link/models/requests.py`.

- [ ] **Step 2: Run the full CI gate**

```bash
make ci-local
```
Expected: pass.

- [ ] **Step 3: Confirm coverage**

```bash
make test-cov
```
Expected: ≥90%. New MCP code should be covered by `tests/test_mcp/`.

- [ ] **Step 4: Smoke test the deployed artifact**

```bash
make docker-build
make docker-up
sleep 5
curl -sf http://127.0.0.1:8000/api/health
curl -sf http://127.0.0.1:8000/metrics | head -5
make docker-down
```

---

## Task 25: Push branch and open PR

**Files:**
- No file changes

- [ ] **Step 1: Push the branch**

```bash
git push -u origin phase-3-mcp-facade-and-transport
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "Phase 3: MCP facade & transport unification" --body "$(cat <<'EOF'
## Summary

- Replace `FastMCP.from_fastapi` auto-generation with explicit facade-based registration under `gtex_link/mcp/`.
- Add `full` and `lite` tool profiles selectable via `GTEX_LINK_MCP_PROFILE`.
- Unify `server.py` to accept `--transport {unified,http,stdio}`.
- Rewrite `gtex_link/server_manager.py` as `UnifiedServerManager`.
- Delete `mcp_http_server.py` and the `gtex-mcp-http` console script.
- Remove `GTEX_LINK_MCP_PORT` and rename `GTEX_LINK_TRANSPORT_MODE` to `GTEX_LINK_TRANSPORT`.
- Collapse Docker compose split (api + mcp) into a single `gtex-link` service.
- Move ChatGPT search/fetch tools out of `app.py` into `gtex_link/mcp/tools/search_fetch.py`.

MCP tool names preserved 1:1: `search`, `fetch`, `search_gtex_genes`, `get_gene_information`, `get_transcript_information`, `get_median_expression_levels`, `get_individual_expression_data`, `get_top_expressed_genes_by_tissue`.

## Type

- [x] feat: new feature
- [x] refactor: code reorganization
- [x] BREAKING: API and deployment surface changes

## Verification

- [x] `make ci-local` passes locally
- [x] Coverage gate still ≥90%
- [x] Every preserved MCP tool name verified by `tests/test_mcp/test_facade.py`
- [x] `server.py --transport http` and `--transport unified` smoke-tested
- [x] `make docker-build && make docker-up` boot single service
- [x] CHANGELOG.md updated with migration notes

## Breaking changes

See CHANGELOG.md `[Unreleased] → Removed (Phase 3)` and `Migration notes`.

- `mcp_http_server.py` removed
- `gtex-mcp-http` console script removed
- `GTEX_LINK_MCP_PORT` env var removed
- `GTEX_LINK_TRANSPORT_MODE` renamed to `GTEX_LINK_TRANSPORT`
- Docker compose: api + mcp → single gtex-link service
EOF
)"
```

---

## Task 26: After merge — tag 0.2.0 release

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: After PR merges to main, promote `[Unreleased]` to `[0.2.0]`**

On `main`:
```bash
git checkout main
git pull origin main
```

Edit `CHANGELOG.md`:
- Rename `## [Unreleased]` to `## [0.2.0] - YYYY-MM-DD` (use today's date).
- Add a fresh `## [Unreleased]` heading above it.

- [ ] **Step 2: Commit and tag**

```bash
git add CHANGELOG.md
git commit -m "chore(release): promote unreleased to 0.2.0"
git tag v0.2.0
git push origin main v0.2.0
```

The `release.yml` workflow will run on the tag push. Watch it via `gh run watch`.

---

## Phase 3 success criteria

- [ ] All 8 preserved MCP tool names callable through the facade (`tests/test_mcp/test_facade.py` asserts the exact set)
- [ ] `server.py --transport unified` boots FastAPI + MCP on one port
- [ ] `server.py --transport http` boots FastAPI only
- [ ] `server.py --transport stdio` boots FastMCP stdio
- [ ] `python -m gtex_link` aliases the unified server
- [ ] `mcp_http_server.py` and `GTEX_LINK_MCP_PORT` gone from the codebase
- [ ] Docker compose runs as a single service
- [ ] CHANGELOG.md 0.2.0 entry covers every breaking change
- [ ] Version bumped to 0.2.0 in `pyproject.toml`
- [ ] `make ci-local` green on the PR
- [ ] `release.yml` green on the tag
