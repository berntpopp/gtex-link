# PR1 — Correctness Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the gtex-link MCP surface from misleading agents — un-double-encode every tool, make `search` accept natural language, magnitude-sort `fetch`, and resolve gene symbols instead of returning silent empties.

**Architecture:** Introduce a shared `run_mcp_tool` error/envelope boundary (mirrors `../gnomad-link/gnomad_link/mcp/errors.py`) so tools return Python `dict`s (FastMCP emits `structuredContent` + a serialized text copy) instead of `json.dumps` strings. Add a small `search_match` module for the NL tokenizer, identifier match-quality ranking, and symbol→GENCODE resolution. `search`/`fetch` keep their OpenAI deep-research shapes; the error boundary turns swallowed failures into structured envelopes while leaving legitimate no-match results as `{"results": []}`.

**Tech Stack:** Python 3.12, FastMCP, Pydantic v2, pytest + pytest-asyncio, respx (not needed here — tool tests mock `GTExService` via `unittest.mock.AsyncMock`).

**Spec:** `docs/superpowers/specs/2026-06-01-mcp-excellence-design.md` (PR1 section + MCP Semantics). Pre-alpha: breaking the response envelope is intended.

---

## File Structure

- Create `gtex_link/mcp/envelope.py` — `McpToolError`, `McpErrorContext`, `_classify`, `run_mcp_tool`, provenance `_meta`. One responsibility: the success/error envelope boundary. (~120 lines)
- Create `gtex_link/mcp/search_match.py` — `recall_terms` tokenizer, `_STOP_WORDS`, `classify_match`, `resolve_gene_ids`. One responsibility: query→identifier matching/resolution helpers. (~110 lines)
- Modify `gtex_link/mcp/resources.py` — add `GTEX_DATA_RELEASE` constant.
- Modify `gtex_link/mcp/tools/reference.py` — dict returns via `run_mcp_tool`; NL handling left to `search` (this file is the catalog tools).
- Modify `gtex_link/mcp/tools/expression.py` — dict returns via `run_mcp_tool`; symbol resolution on median + individual.
- Modify `gtex_link/mcp/tools/search_fetch.py` — `search` NL + `run_mcp_tool`; `fetch` magnitude-sort + bare-GENCODE alias, dict returns.
- Tests: `tests/test_mcp/test_envelope.py`, `tests/test_mcp/test_search_match.py` (new); update `tests/test_mcp/test_tool_bodies.py`.

**Envelope contract (PR1 minimal, forward-compatible):**
- Success: the tool's `dict` plus `success: true` and `_meta` (provenance). PR2 adds nothing that removes these.
- Error: `{"success": false, "error_code": <code>, "message": <safe text>, "_meta": {...}}`. PR2 extends with `retryable`, `recovery_action`, `field_errors`; PR3 adds `_meta.next_commands`.
- Error codes (PR1 set): `not_found`, `invalid_input`, `validation_failed`, `rate_limited`, `upstream_unavailable`, `internal_error`.

---

## Task 1: Envelope boundary module

**Files:**
- Create: `gtex_link/mcp/envelope.py`
- Modify: `gtex_link/mcp/resources.py`
- Test: `tests/test_mcp/test_envelope.py`

- [ ] **Step 1: Add the data-release constant**

In `gtex_link/mcp/resources.py`, after the `GTEX_PORTAL_URL` line, add:

```python
# Default GTEx data release surfaced in provenance _meta and capabilities.
GTEX_DATA_RELEASE = "gtex_v8"
```

- [ ] **Step 2: Write the failing test for `run_mcp_tool`**

Create `tests/test_mcp/test_envelope.py`:

```python
"""Tests for the shared MCP envelope boundary."""

from __future__ import annotations

import pytest

from gtex_link.exceptions import RateLimitError, ValidationError
from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool


@pytest.mark.asyncio
async def test_success_injects_success_and_meta() -> None:
    async def call() -> dict[str, object]:
        return {"data": [1, 2, 3]}

    result = await run_mcp_tool("demo", call)

    assert result["data"] == [1, 2, 3]
    assert result["success"] is True
    assert result["_meta"]["unsafe_for_clinical_use"] is True
    assert result["_meta"]["gtex_release"] == "gtex_v8"


@pytest.mark.asyncio
async def test_rate_limit_maps_to_rate_limited_envelope() -> None:
    async def call() -> dict[str, object]:
        raise RateLimitError("slow down")

    result = await run_mcp_tool("demo", call)

    assert result["success"] is False
    assert result["error_code"] == "rate_limited"
    assert "rate limit" in result["message"].lower()
    assert result["_meta"]["tool"] == "demo"


@pytest.mark.asyncio
async def test_validation_error_maps_to_invalid_input() -> None:
    async def call() -> dict[str, object]:
        raise ValidationError("bad gene", field="gencode_id")

    result = await run_mcp_tool("demo", call)

    assert result["success"] is False
    assert result["error_code"] == "invalid_input"


@pytest.mark.asyncio
async def test_explicit_mcp_tool_error_passes_code_through() -> None:
    from gtex_link.mcp.envelope import McpToolError

    async def call() -> dict[str, object]:
        raise McpToolError(error_code="not_found", message="no gene")

    result = await run_mcp_tool("demo", call, context=McpErrorContext(tool_name="demo"))

    assert result["error_code"] == "not_found"
    assert result["success"] is False
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/test_mcp/test_envelope.py -v`
Expected: FAIL with `ModuleNotFoundError: gtex_link.mcp.envelope`.

- [ ] **Step 4: Implement `gtex_link/mcp/envelope.py`**

```python
"""Shared MCP envelope boundary for GTEx-Link tools.

Tools return a Python dict; `run_mcp_tool` injects `success`/`_meta` on the
happy path and converts any exception into a structured error envelope dict
(returned, never raised) so the LLM sees a structured failure instead of an
opaque masked message. Patterned after ../gnomad-link/.../mcp/errors.py, kept
minimal here (PR1); PR2 adds retryable/recovery_action/field_errors and PR3
adds _meta.next_commands.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from gtex_link.mcp.resources import GTEX_DATA_RELEASE

logger = logging.getLogger(__name__)

_BASE_META: dict[str, Any] = {
    "unsafe_for_clinical_use": True,
    "gtex_release": GTEX_DATA_RELEASE,
}


@dataclass
class McpErrorContext:
    """Per-call context so envelopes can name the failing tool."""

    tool_name: str
    dataset_id: str | None = None


class McpToolError(Exception):
    """Raised inside a tool body to emit a specific error code/message."""

    def __init__(self, *, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _provenance_meta(context: McpErrorContext | None = None) -> dict[str, Any]:
    meta = dict(_BASE_META)
    if context is not None and context.dataset_id:
        meta["dataset_id"] = context.dataset_id
    return meta


def _safe_message(exc: BaseException) -> str:
    return (str(exc) or exc.__class__.__name__)[:240]


def _classify(exc: BaseException) -> tuple[str, str]:
    """Return (error_code, client_safe_message)."""
    if isinstance(exc, McpToolError):
        return exc.error_code, exc.message
    if isinstance(exc, RateLimitError):
        return "rate_limited", "GTEx Portal rate limit exceeded. Try again shortly."
    if isinstance(exc, ServiceUnavailableError):
        return "upstream_unavailable", "GTEx Portal is temporarily unavailable. Try again later."
    if isinstance(exc, PydanticValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"]) or "input"
        return "invalid_input", f"Invalid input -- `{loc}`: {first['msg']}"
    if isinstance(exc, ValidationError):
        field = f"`{exc.field}`: " if exc.field else ""
        return "invalid_input", f"Invalid input -- {field}{exc.message}"
    if isinstance(exc, GTExAPIError):
        return "upstream_unavailable", "GTEx Portal returned an error. Verify the request inputs."
    return "internal_error", "An internal error occurred. The request was not completed."


def _error_envelope(exc: BaseException, context: McpErrorContext) -> dict[str, Any]:
    error_code, message = _classify(exc)
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "_meta": {"tool": context.tool_name, **_provenance_meta(context)},
    }


async def run_mcp_tool(
    tool_name: str,
    call: Callable[[], Awaitable[dict[str, Any]]],
    *,
    context: McpErrorContext | None = None,
) -> dict[str, Any]:
    """Execute a tool body, returning the result dict or a structured error dict."""
    ctx = context or McpErrorContext(tool_name=tool_name)
    try:
        result = await call()
        if isinstance(result, dict):
            result.setdefault("success", True)
            existing_meta: dict[str, Any] = result.get("_meta") or {}
            result["_meta"] = {**existing_meta, **_provenance_meta(ctx)}
        return result
    except Exception as exc:  # broad catch is the error-boundary contract
        envelope = _error_envelope(exc, ctx)
        logger.warning(
            "mcp_tool_error tool=%s code=%s exc=%s",
            tool_name,
            envelope["error_code"],
            exc.__class__.__name__,
        )
        return envelope
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `uv run pytest tests/test_mcp/test_envelope.py -v`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/envelope.py gtex_link/mcp/resources.py tests/test_mcp/test_envelope.py
git commit -m "feat(mcp): add run_mcp_tool envelope boundary"
```

---

## Task 2: Search-match helpers (tokenizer, ranking, symbol resolution)

**Files:**
- Create: `gtex_link/mcp/search_match.py`
- Test: `tests/test_mcp/test_search_match.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp/test_search_match.py`:

```python
"""Tests for NL tokenization, match ranking, and symbol resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gtex_link.mcp.search_match import classify_match, recall_terms, resolve_gene_ids
from gtex_link.models.responses import Gene, PaginatedGeneResponse, PaginationInfo


def test_recall_terms_strips_stopwords_and_short_tokens() -> None:
    assert recall_terms("UMOD kidney expression") == ["umod", "kidney", "expression"]
    assert recall_terms("the BRCA1 of a gene") == ["brca1", "gene"]
    assert recall_terms("a or in") == []


def test_recall_terms_dedupes_preserving_order() -> None:
    assert recall_terms("BRCA1 brca1 TP53") == ["brca1", "tp53"]


def test_classify_match_ranks_exact_symbol_first() -> None:
    assert classify_match("umod", symbol="UMOD", gencode_id="ENSG00000169344.15") == "exact_symbol"
    assert classify_match("ensg00000169344", symbol="UMOD", gencode_id="ENSG00000169344.15") == "exact_ensembl_id"
    assert classify_match("umo", symbol="UMOD", gencode_id="ENSG00000169344.15") == "prefix"
    assert classify_match("mod", symbol="UMOD", gencode_id="ENSG00000169344.15") == "substring"


def _gene(symbol: str, gencode: str) -> Gene:
    return Gene.model_validate(
        {
            "chromosome": "chr16", "dataSource": "GENCODE", "description": "x", "end": 2,
            "entrezGeneId": 1, "gencodeId": gencode, "gencodeVersion": "v26",
            "geneStatus": "KNOWN", "geneSymbol": symbol, "geneSymbolUpper": symbol.upper(),
            "geneType": "protein_coding", "genomeBuild": "GRCh38", "start": 1,
            "strand": "-", "tss": 2,
        }
    )


@pytest.mark.asyncio
async def test_resolve_gene_ids_passes_through_versioned_gencode() -> None:
    service = AsyncMock()
    resolved = await resolve_gene_ids(service, ["ENSG00000169344.15"])
    assert resolved == ["ENSG00000169344.15"]
    service.get_genes.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_gene_ids_resolves_symbol_to_gencode() -> None:
    service = AsyncMock()
    service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(
            data=[_gene("UMOD", "ENSG00000169344.15")],
            pagingInfo=PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=50, totalNumberOfItems=1),
        )
    )
    resolved = await resolve_gene_ids(service, ["UMOD"])
    assert resolved == ["ENSG00000169344.15"]


@pytest.mark.asyncio
async def test_resolve_gene_ids_raises_invalid_input_for_unknown() -> None:
    from gtex_link.mcp.envelope import McpToolError

    service = AsyncMock()
    service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(
            data=[],
            pagingInfo=PaginationInfo(numberOfPages=0, page=0, maxItemsPerPage=50, totalNumberOfItems=0),
        )
    )
    with pytest.raises(McpToolError) as excinfo:
        await resolve_gene_ids(service, ["NOTAGENE123"])
    assert excinfo.value.error_code == "invalid_input"
    assert "NOTAGENE123" in excinfo.value.message
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_search_match.py -v`
Expected: FAIL with `ModuleNotFoundError: gtex_link.mcp.search_match`.

- [ ] **Step 3: Implement `gtex_link/mcp/search_match.py`**

```python
"""Query tokenization, identifier match ranking, and symbol->GENCODE resolution.

GTEx's geneSearch endpoint matches a gene_id only (symbol / GENCODE / Ensembl);
there is no description/free-text search and no local corpus. So NL recall is
identifier-based: tokenize, query per candidate token, union, rank by how the
identifier matched. Tokenizer ported from ../genereviews-link/.../retrieval/lexical.py.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from gtex_link.mcp.envelope import McpToolError
from gtex_link.models import GeneRequest

if TYPE_CHECKING:
    from gtex_link.services.gtex_service import GTExService

_TOKEN_RE = re.compile(r"[A-Za-z0-9.]+")
_VERSIONED_GENCODE_RE = re.compile(r"^ENSG\d+\.\d+$", re.IGNORECASE)

_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "of", "in", "is", "it", "to", "for",
        "on", "at", "be", "as", "by", "do", "up", "if", "no", "so", "we",
        "are", "was", "not", "but", "has", "had", "its", "can", "may", "who",
        "how", "all", "one", "two", "gene", "genes", "level", "levels",
    }
)

# Maximum candidate tokens turned into upstream geneSearch calls. The upstream
# token-bucket is 5 req/s; a small cap keeps NL search fast.
MAX_QUERY_TOKENS = 5


def recall_terms(query: str) -> list[str]:
    """Distinct 3+-char lowercased tokens from *query*, excluding stop words."""
    out: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(query):
        tok = match.group(0).lower()
        if len(tok) < 3 or tok in _STOP_WORDS or tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def classify_match(token: str, *, symbol: str, gencode_id: str) -> str:
    """Rank how *token* matched an identifier: exact_symbol > exact_ensembl_id > prefix > substring."""
    tok = token.lower()
    sym = symbol.lower()
    ensembl = gencode_id.split(".")[0].lower()
    if tok == sym:
        return "exact_symbol"
    if tok == ensembl or tok == gencode_id.lower():
        return "exact_ensembl_id"
    if sym.startswith(tok) or ensembl.startswith(tok):
        return "prefix"
    return "substring"


_RANK_ORDER = {"exact_symbol": 0, "exact_ensembl_id": 1, "prefix": 2, "substring": 3}


def is_versioned_gencode(value: str) -> bool:
    """True if *value* is already a versioned GENCODE id (no resolution needed)."""
    return bool(_VERSIONED_GENCODE_RE.match(value))


async def resolve_gene_ids(service: GTExService, raw_ids: list[str]) -> list[str]:
    """Resolve symbols / unversioned ids to versioned GENCODE ids.

    Inputs already shaped like ENSG00000169344.15 pass through untouched. Anything
    else is resolved via get_genes (which accepts symbols). Raises McpToolError
    (invalid_input) listing any token that cannot be resolved -- never returns a
    silently shorter list.
    """
    if all(is_versioned_gencode(rid) for rid in raw_ids):
        return raw_ids

    request = GeneRequest.model_validate(
        {"geneId": raw_ids, "page": 0, "itemsPerPage": len(raw_ids)}
    )
    result = await service.get_genes(request)
    by_input: dict[str, str] = {}
    for gene in result.data:
        by_input[gene.gene_symbol.lower()] = gene.gencode_id
        by_input[gene.gencode_id.lower()] = gene.gencode_id
        by_input[gene.gencode_id.split(".")[0].lower()] = gene.gencode_id

    resolved: list[str] = []
    unresolved: list[str] = []
    for rid in raw_ids:
        if is_versioned_gencode(rid):
            resolved.append(rid)
        elif rid.lower() in by_input:
            resolved.append(by_input[rid.lower()])
        else:
            unresolved.append(rid)
    if unresolved:
        raise McpToolError(
            error_code="invalid_input",
            message=(
                f"Could not resolve to GENCODE IDs: {', '.join(unresolved)}. "
                "Provide a gene symbol (e.g. UMOD) or a versioned GENCODE ID "
                "(e.g. ENSG00000169344.15)."
            ),
        )
    return resolved
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_search_match.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/search_match.py tests/test_mcp/test_search_match.py
git commit -m "feat(mcp): add NL tokenizer, match ranking, symbol resolution helpers"
```

---

## Task 3: Convert reference tools to dict returns via the envelope

**Files:**
- Modify: `gtex_link/mcp/tools/reference.py`
- Test: `tests/test_mcp/test_tool_bodies.py` (existing happy-path tests already assert subset keys; they keep passing because the serialized text copy is still present)

- [ ] **Step 1: Write a failing test for structured (non-double-encoded) output**

Add to `tests/test_mcp/test_tool_bodies.py` (near the other reference tests):

```python
@pytest.mark.asyncio
async def test_search_gtex_genes_returns_structured_not_double_encoded() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
        result = await mcp.call_tool("search_gtex_genes", {"query": "BRCA1"})

    # structured_content is a real object, not a JSON string in a string
    assert result.structured_content is not None
    assert result.structured_content["success"] is True
    assert result.structured_content["data"][0]["geneSymbol"] == "BRCA1"
    assert result.structured_content["_meta"]["gtex_release"] == "gtex_v8"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py::test_search_gtex_genes_returns_structured_not_double_encoded -v`
Expected: FAIL — currently `structured_content` is absent/None because the tool returns a JSON string.

- [ ] **Step 3: Rewrite `gtex_link/mcp/tools/reference.py`**

Replace the file body with dict-returning tools routed through `run_mcp_tool`. Full file:

```python
"""Reference-category MCP tools (gene search, gene info, transcript info)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, TranscriptRequest
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_reference_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
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
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query,
                    gencode_version=None,
                    genome_build=None,
                    page=page,
                    page_size=page_size,
                )
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "search_gtex_genes", call, context=McpErrorContext("search_gtex_genes")
                )
                success = payload.get("success", False)
                return payload
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
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "geneId": gene_id,
                    "page": 0,
                    "itemsPerPage": len(gene_id),
                }
                if gencode_version is not None:
                    payload["gencodeVersion"] = gencode_version
                if genome_build is not None:
                    payload["genomeBuild"] = genome_build
                request = GeneRequest.model_validate(payload)
                result = await service.get_genes(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_gene_information", call, context=McpErrorContext("get_gene_information")
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_gene_information", success=success)

    if is_tool_in_profile("get_transcript_information", profile):

        @mcp.tool(
            name="get_transcript_information",
            description=(
                "Retrieve transcript annotations for a single GENCODE ID from "
                "GTEx Portal. Returns transcript identifiers, coordinates, "
                "and gene linkage. Use for transcript-level analysis or when "
                "the user asks about isoforms."
            ),
        )
        async def get_transcript_information(
            gencode_id: str,
            gencode_version: str | None = None,
            genome_build: str | None = None,
            page: int = 0,
            page_size: int = 250,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                payload: dict[str, object] = {
                    "gencodeId": gencode_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if gencode_version is not None:
                    payload["gencodeVersion"] = gencode_version
                if genome_build is not None:
                    payload["genomeBuild"] = genome_build
                request = TranscriptRequest.model_validate(payload)
                result = await service.get_transcripts(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_transcript_information",
                    call,
                    context=McpErrorContext("get_transcript_information"),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_transcript_information", success=success)
```

- [ ] **Step 4: Update the existing error-path test**

In `tests/test_mcp/test_tool_bodies.py`, replace `test_search_gtex_genes_error_path_returns_friendly_message` body assertion with:

```python
    with patch_service(mock_service):
        payload = await _call_tool("search_gtex_genes", {"query": "BRCA1"})

    assert payload["success"] is False
    assert payload["error_code"] == "rate_limited"
    assert "rate limit" in payload["message"].lower()
```

- [ ] **Step 5: Run reference tool tests**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "search_gtex_genes or gene_information or transcript" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/tools/reference.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): reference tools return structured envelopes"
```

---

## Task 4: Convert expression tools + add symbol resolution

**Files:**
- Modify: `gtex_link/mcp/tools/expression.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write failing tests for symbol resolution + structured output**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_median_resolves_symbol_to_gencode() -> None:
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        payload = await _call_tool("get_median_expression_levels", {"gencode_id": ["BRCA1"]})

    assert payload["success"] is True
    request = mock_service.get_median_gene_expression.call_args.args[0]
    assert request.gencode_id == ["ENSG00000012048.22"]


@pytest.mark.asyncio
async def test_median_unknown_symbol_returns_invalid_input_not_silent_empty() -> None:
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        payload = await _call_tool("get_median_expression_levels", {"gencode_id": ["NOTAGENE"]})

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
    assert "NOTAGENE" in payload["message"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "resolves_symbol or unknown_symbol" -v`
Expected: FAIL (symbols currently passed through; empty data returned).

- [ ] **Step 3: Rewrite `gtex_link/mcp/tools/expression.py`**

Full file:

```python
"""Expression-category MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.search_match import resolve_gene_ids
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import (
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    TopExpressedGenesRequest,
)
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_expression_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register expression-category tools on a FastMCP instance."""
    if is_tool_in_profile("get_median_expression_levels", profile):

        @mcp.tool(
            name="get_median_expression_levels",
            description=(
                "Get median GTEx Portal expression (TPM) per tissue for one or "
                "more genes (GENCODE IDs or symbols; symbols are auto-resolved). "
                "Returns per-tissue medians for dataset `gtex_v8` by default. Use "
                "this when comparing expression of a known gene across tissues; "
                "pair with `get_top_expressed_genes_by_tissue` for the reverse "
                "question."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                resolved = await resolve_gene_ids(service, gencode_id)
                payload: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = MedianGeneExpressionRequest.model_validate(payload)
                result = await service.get_median_gene_expression(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_median_expression_levels",
                    call,
                    context=McpErrorContext("get_median_expression_levels", dataset_id=dataset_id),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_median_expression_levels", success=success)

    if is_tool_in_profile("get_individual_expression_data", profile):

        @mcp.tool(
            name="get_individual_expression_data",
            description=(
                "Get individual-sample GTEx Portal expression data (TPM) for one "
                "or more genes (GENCODE IDs or symbols; symbols are auto-resolved), "
                "optionally filtered by tissue and dataset. High volume -- limit "
                "`page_size` accordingly. Use for variance/distribution analyses "
                "where per-sample data is needed."
            ),
        )
        async def get_individual_expression_data(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                resolved = await resolve_gene_ids(service, gencode_id)
                payload: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": page,
                    "itemsPerPage": page_size,
                }
                if tissue_site_detail_id is not None:
                    payload["tissueSiteDetailId"] = tissue_site_detail_id
                request = GeneExpressionRequest.model_validate(payload)
                result = await service.get_gene_expression(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_individual_expression_data",
                    call,
                    context=McpErrorContext("get_individual_expression_data", dataset_id=dataset_id),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_individual_expression_data", success=success)

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
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                request = TopExpressedGenesRequest.model_validate(
                    {
                        "tissueSiteDetailId": tissue_site_detail_id,
                        "datasetId": dataset_id,
                        "filterMtGene": filter_mt_gene,
                        "page": page,
                        "itemsPerPage": page_size,
                    }
                )
                result = await service.get_top_expressed_genes(request)
                return result.model_dump(by_alias=True)

            success = False
            try:
                payload = await run_mcp_tool(
                    "get_top_expressed_genes_by_tissue",
                    call,
                    context=McpErrorContext("get_top_expressed_genes_by_tissue", dataset_id=dataset_id),
                )
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="get_top_expressed_genes_by_tissue", success=success)
```

- [ ] **Step 4: Fix the two existing median tests for resolution behavior**

The existing `test_get_median_expression_levels_omits_tissue_when_none` and `..._passes_tissue_when_given` pass GENCODE-shaped ids (`ENSG00000012048.22`) which now pass through `resolve_gene_ids` without a `get_genes` call — they keep working. Confirm by running them in Step 5. (No edit needed; if either mock lacked `get_genes` it is unused.)

- [ ] **Step 5: Run expression tool tests**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "median or individual or top_expressed" -v`
Expected: PASS (including the two new resolution tests).

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): expression tools structured + auto-resolve symbols"
```

---

## Task 5: Natural-language `search` + magnitude-sorted `fetch`

**Files:**
- Modify: `gtex_link/mcp/tools/search_fetch.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_mcp/test_tool_bodies.py` (and update the two existing search tests):

```python
@pytest.mark.asyncio
async def test_search_natural_language_query_finds_gene() -> None:
    # The NL query tokenizes to [umod, kidney, expression]; only "umod" resolves.
    umod = Gene.model_validate(
        {
            "chromosome": "chr16", "dataSource": "GENCODE", "description": "uromodulin",
            "end": 2, "entrezGeneId": 7369, "gencodeId": "ENSG00000169344.15",
            "gencodeVersion": "v26", "geneStatus": "KNOWN", "geneSymbol": "UMOD",
            "geneSymbolUpper": "UMOD", "geneType": "protein_coding",
            "genomeBuild": "GRCh38", "start": 1, "strand": "-", "tss": 2,
        }
    )

    async def fake_search(query: str, **kwargs: Any) -> PaginatedGeneResponse:
        if query.lower() == "umod":
            return PaginatedGeneResponse(data=[umod], pagingInfo=_paging(1))
        return PaginatedGeneResponse(data=[], pagingInfo=_paging(0))

    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(side_effect=fake_search)

    with patch_service(mock_service):
        payload = await _call_tool("search", {"query": "UMOD kidney expression"})

    ids = [r["id"] for r in payload["results"]]
    assert "gene:ENSG00000169344.15" in ids


@pytest.mark.asyncio
async def test_fetch_sorts_expression_by_descending_median() -> None:
    def _median(tissue: str, value: float) -> MedianGeneExpression:
        return MedianGeneExpression.model_validate(
            {
                "datasetId": "gtex_v8", "ontologyId": "X", "gencodeId": "ENSG00000169344.15",
                "geneSymbol": "UMOD", "median": value, "numSamples": None,
                "tissueSiteDetailId": tissue, "unit": "TPM",
            }
        )

    umod = _brca1_gene().model_copy(update={"gene_symbol": "UMOD", "gencode_id": "ENSG00000169344.15"})
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[umod], pagingInfo=_paging(1))
    )
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(
            data=[_median("Adipose_Subcutaneous", 0.0), _median("Kidney_Medulla", 2116.02)],
            pagingInfo=_paging(2),
        )
    )

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "gene:ENSG00000169344.15"})

    text = payload["text"]
    assert "Kidney_Medulla: 2116.02 TPM" in text
    # Highest-expression tissue appears before the 0.00 one
    assert text.index("Kidney_Medulla") < text.index("Adipose_Subcutaneous")


@pytest.mark.asyncio
async def test_fetch_accepts_bare_gencode_id() -> None:
    umod = _brca1_gene().model_copy(update={"gene_symbol": "UMOD", "gencode_id": "ENSG00000169344.15"})
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[umod], pagingInfo=_paging(1))
    )
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "ENSG00000169344.15"})

    assert payload["id"] == "ENSG00000169344.15"
    assert payload["title"].startswith("UMOD - ")
```

Update `test_search_tool_returns_chatgpt_shape` to assert on `payload["results"]` (the envelope now also carries `success`/`_meta`):

```python
    assert payload["results"] == [
        {
            "id": "gene:ENSG00000012048.22",
            "title": "BRCA1 - BRCA1 DNA repair associated",
            "url": "https://gtexportal.org/home/gene/BRCA1",
        }
    ]
```

Replace `test_search_tool_returns_empty_on_error` with a structured-error assertion:

```python
@pytest.mark.asyncio
async def test_search_tool_returns_structured_error_on_upstream_failure() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(side_effect=RuntimeError("upstream down"))

    with patch_service(mock_service):
        payload = await _call_tool("search", {"query": "BRCA1"})

    assert payload["success"] is False
    assert payload["error_code"] == "internal_error"
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "search or fetch" -v`
Expected: FAIL (NL not handled; fetch not sorted; bare id rejected; old shape).

- [ ] **Step 3: Rewrite `gtex_link/mcp/tools/search_fetch.py`**

Full file:

```python
"""ChatGPT-compatible search and fetch MCP tools.

These mirror the OpenAI deep-research / Apps SDK shape -- `search(query) ->
{results: [...]}` and `fetch(id) -> {id, title, text, url, metadata}` -- so a
single MCP server is consumable by ChatGPT (reads `text`) and Claude (reads
structuredContent). `search` recall is identifier-only (GTEx geneSearch matches
gene_id), so a natural-language query is tokenized and each candidate token is
resolved against the catalog, then unioned and ranked by match quality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool
from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_PORTAL_URL
from gtex_link.mcp.search_match import (
    MAX_QUERY_TOKENS,
    _RANK_ORDER,
    classify_match,
    recall_terms,
)
from gtex_link.mcp.service_adapters import get_gtex_service
from gtex_link.models import GeneRequest, MedianGeneExpressionRequest
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

_FETCH_TISSUE_LIMIT = 10


def register_search_fetch_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register the ChatGPT-compatible `search` and `fetch` tools."""
    if is_tool_in_profile("search", profile):

        @mcp.tool(
            name="search",
            description=(
                "Search the GTEx Portal genetic expression database for genes. "
                "Accepts a natural-language query (e.g. 'UMOD kidney "
                "expression'); gene-like terms are matched against the catalog. "
                "Returns result documents with id, title, and URL."
            ),
        )
        async def search(query: str) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                tokens = recall_terms(query)[:MAX_QUERY_TOKENS] or [query.strip()]
                # token -> (rank, gene) keeping the best rank seen per gencode_id
                best: dict[str, tuple[int, Any]] = {}
                for token in tokens:
                    result = await service.search_genes(
                        query=token,
                        gencode_version=None,
                        genome_build=None,
                        page=0,
                        page_size=20,
                    )
                    for gene in result.data:
                        quality = classify_match(
                            token, symbol=gene.gene_symbol, gencode_id=gene.gencode_id
                        )
                        rank = _RANK_ORDER[quality]
                        prior = best.get(gene.gencode_id)
                        if prior is None or rank < prior[0]:
                            best[gene.gencode_id] = (rank, gene)
                ordered = sorted(best.values(), key=lambda rg: (rg[0], rg[1].gene_symbol))
                items = [
                    {
                        "id": f"gene:{gene.gencode_id}",
                        "title": f"{gene.gene_symbol} - {gene.description or 'Gene'}",
                        "url": f"{GTEX_PORTAL_URL}/home/gene/{gene.gene_symbol}",
                    }
                    for _rank, gene in ordered
                ]
                return {"results": items}

            success = False
            try:
                payload = await run_mcp_tool("search", call, context=McpErrorContext("search"))
                success = payload.get("success", False)
                return payload
            finally:
                record_mcp_tool_call(tool="search", success=success)

    if is_tool_in_profile("fetch", profile):

        @mcp.tool(
            name="fetch",
            description=(
                "Retrieve full details for a gene from the GTEx Portal database. "
                "Use the `id` returned by `search` (`gene:<GENCODE_ID>`); a bare "
                "GENCODE ID is also accepted. Expression is listed highest-median "
                "tissue first."
            ),
        )
        async def fetch(id: str) -> dict[str, Any]:
            success = False
            try:
                service = get_gtex_service()
                gencode_id = id[len("gene:") :] if id.startswith("gene:") else id
                if not gencode_id:
                    return _error_doc(id, "Unsupported resource type", f"Unsupported resource id: {id!r}")

                gene_request = GeneRequest.model_validate(
                    {"geneId": [gencode_id], "page": 0, "itemsPerPage": 1}
                )
                gene_result = await service.get_genes(gene_request)
                if not gene_result.data:
                    return _error_doc(id, "Resource not found", f"No gene found for {gencode_id!r}")
                gene = gene_result.data[0]

                expression_text = await _expression_lines(service, gene.gencode_id)
                lines = [
                    f"Gene Symbol: {gene.gene_symbol}",
                    f"GENCODE ID: {gene.gencode_id}",
                    f"Description: {gene.description or 'Not available'}",
                    f"Chromosome: {gene.chromosome}",
                    f"Position: {gene.start:,}-{gene.end:,}",
                    f"Strand: {gene.strand}",
                    f"Gene Type: {gene.gene_type}",
                ]
                if gene.entrez_gene_id:
                    lines.append(f"Entrez Gene ID: {gene.entrez_gene_id}")
                lines.extend(expression_text)

                success = True
                return {
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
            except Exception:
                return _error_doc(id, "Error", "An error occurred fetching this resource.")
            finally:
                record_mcp_tool_call(tool="fetch", success=success)


def _error_doc(resource_id: str, title: str, text: str) -> dict[str, Any]:
    return {
        "id": resource_id,
        "title": title,
        "text": text,
        "url": GTEX_PORTAL_URL,
        "metadata": {"source": "GTEx Portal", "type": "error"},
    }


async def _expression_lines(service: Any, gencode_id: str) -> list[str]:
    """Return median-TPM lines sorted highest-first; empty list on any failure."""
    try:
        request = MedianGeneExpressionRequest.model_validate(
            {
                "gencodeId": [gencode_id],
                "tissueSiteDetailId": "",
                "datasetId": "gtex_v8",
                "page": 0,
                "itemsPerPage": 60,
            }
        )
        result = await service.get_median_gene_expression(request)
    except Exception:
        return []
    if not result.data:
        return []
    ranked = sorted(result.data, key=lambda exp: exp.median, reverse=True)
    lines = ["\nExpression Data (median TPM by tissue, highest first):"]
    for exp in ranked[:_FETCH_TISSUE_LIMIT]:
        lines.append(f"  {exp.tissue_site_detail_id}: {exp.median:.2f} TPM")
    if len(ranked) > _FETCH_TISSUE_LIMIT:
        cutoff = ranked[_FETCH_TISSUE_LIMIT].median
        lines.append(f"  ... and {len(ranked) - _FETCH_TISSUE_LIMIT} more tissues at <= {cutoff:.2f} TPM")
    return lines
```

- [ ] **Step 4: Run search/fetch tests**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "search or fetch" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/search_fetch.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): natural-language search + magnitude-sorted fetch"
```

---

## Task 6: Retire the legacy error-string mapper and update instructions

**Files:**
- Modify: `gtex_link/mcp/errors.py`
- Modify: `gtex_link/mcp/resources.py`
- Test: `tests/test_mcp/test_errors.py`

- [ ] **Step 1: Confirm `map_to_mcp_error_message` is unused**

Run: `rg -n "map_to_mcp_error_message" gtex_link tests`
Expected: only `gtex_link/mcp/errors.py` (definition) and `tests/test_mcp/test_errors.py`. If any tool still imports it, that tool was missed in Tasks 3-5 — fix it before continuing.

- [ ] **Step 2: Keep `errors.py` but mark it legacy**

`gtex_link/mcp/errors.py` is now only exercised by its own unit test. Leave the function in place (the envelope's `_classify` supersedes it) and add a one-line module note so future readers use the envelope:

Add below the module docstring:

```python
# NOTE: superseded by gtex_link.mcp.envelope._classify for tool error handling.
# Retained only for any non-tool callers; new code should not import this.
```

- [ ] **Step 3: Update server instructions for the new behavior**

In `gtex_link/mcp/resources.py`, replace `GTEX_SERVER_INSTRUCTIONS` value with:

```python
GTEX_SERVER_INSTRUCTIONS = (
    "GTEx-Link exposes GTEx Portal v8 expression data. "
    "For ChatGPT-compatible workflows use `search` (natural language ok) then "
    "`fetch`. For programmatic access: `search_gtex_genes` -> "
    "`get_gene_information` -> `get_median_expression_levels` or "
    "`get_top_expressed_genes_by_tissue`. Gene IDs accept symbols or GENCODE "
    "IDs; symbols are auto-resolved. Tool results are structured JSON with a "
    "`success` flag and `_meta`; errors carry an `error_code`. "
    f"{RESEARCH_USE_NOTICE}"
)
```

- [ ] **Step 4: Run the full MCP test module**

Run: `uv run pytest tests/test_mcp/ -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/errors.py gtex_link/mcp/resources.py
git commit -m "docs(mcp): mark legacy error mapper, update server instructions"
```

---

## Task 7: Full verification

- [ ] **Step 1: Run the whole suite + gates**

Run: `make ci-local`
Expected: PASS (format, lint, lint-loc, typecheck, tests; coverage >= 90%).

- [ ] **Step 2: Live MCP smoke check (the reviewer's failing calls)**

Start the server (`make mcp-serve`) or call the in-process facade in a `uv run python` shell, then verify:
- `search("UMOD kidney expression")` returns UMOD (not empty).
- `fetch("gene:ENSG00000169344.15")` text lists `Kidney_Medulla` near the top, not 10 alphabetical `0.00 TPM` rows.
- `get_median_expression_levels(["PKD1"])` returns data or a structured `invalid_input` — never a silent empty.
- All payloads are structured (no `{"result":"{...}"}` double-encoding).

- [ ] **Step 3: Final commit if any lint/format fixups were needed**

```bash
git add -A && git commit -m "chore(mcp): PR1 verification fixups" || echo "nothing to fix up"
```

---

## Self-Review Notes

- **Spec coverage:** PR1 bullets all mapped — un-double-encode (Tasks 3-5), `fetch` magnitude-sort (Task 5), NL `search` (Task 5), symbol resolution / no silent empties (Task 4), bare-GENCODE `fetch` alias (Task 5), minimal forward-compatible error envelope (Task 1). `headline`, `output_schema`, annotations, `next_commands`, gene-grouping are intentionally PR2/PR3.
- **Type consistency:** `run_mcp_tool`, `McpErrorContext`, `McpToolError`, `resolve_gene_ids`, `recall_terms`, `classify_match`, `_RANK_ORDER` names are identical across tasks. Tools annotated `-> dict[str, Any]`.
- **Contract notes:** `search` flows through `run_mcp_tool` (gains `success`/`_meta`; ChatGPT reads `results`, tolerates extra keys; a genuine upstream error becomes a structured error rather than a fake empty). `fetch` returns document-shaped dicts directly (ChatGPT reads `text`); only its `text`/`metadata` matter to deep research, so it is not wrapped in the envelope.
