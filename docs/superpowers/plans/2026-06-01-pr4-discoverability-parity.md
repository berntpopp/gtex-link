# PR4 — Discoverability & Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make gtex-link self-describing and bring it to family parity — a `get_server_capabilities` tool + `gtex://…` resources with a content-hash, a clean tissue vocabulary, and a citation surface.

**Architecture:** A `metadata` module builds a single capabilities document (tools, datasets, tissues, workflows, response modes, error codes, parameter conventions, token-cost hints, limitations, concurrency, citation) plus a `capabilities_version` sha256 content-hash so warm clients can skip re-fetching. Register it as a tool and as MCP resources (`gtex://capabilities|usage|reference|research-use|citations`). Advertise the 54 real tissues (not the internal `""` all-tissues sentinel) and validate tissue inputs against that set. Add a `recommended_citation` to provenance `_meta`.

**Tech Stack:** Python 3.12, FastMCP resources, hashlib/functools, Pydantic enums.

**Spec:** `docs/superpowers/specs/2026-06-01-mcp-excellence-design.md` (PR4 + MCP Semantics: `mcp_protocol_version` 2025-11-25). Depends on PR1-PR3.

---

## File Structure

- Create `gtex_link/mcp/metadata.py` — `valid_tissues()`, `build_capabilities()`, `capabilities_version()`, `register_metadata_tools(mcp, profile)`. (~160 lines)
- Create `gtex_link/mcp/capabilities_resources.py` — register `gtex://…` resources. (~70 lines)
- Modify `gtex_link/mcp/resources.py` — add `RECOMMENDED_CITATION`, usage/reference text constants.
- Modify `gtex_link/mcp/envelope.py` — add `recommended_citation` to provenance `_meta`.
- Modify `gtex_link/mcp/profiles.py` — add `get_server_capabilities` to `LITE_TOOLS`.
- Modify `gtex_link/mcp/facade.py` — register metadata tool + resources.
- Modify `gtex_link/mcp/tools/expression.py` — validate the top-expressed tissue against `valid_tissues()`.
- Tests: `tests/test_mcp/test_metadata.py` (new); extend `tests/test_mcp/test_facade.py`, `tests/test_mcp/test_envelope.py`.

---

## Task 1: Citation in provenance + resource text constants

**Files:**
- Modify: `gtex_link/mcp/resources.py`, `gtex_link/mcp/envelope.py`
- Test: `tests/test_mcp/test_envelope.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_envelope.py`:

```python
@pytest.mark.asyncio
async def test_success_meta_includes_recommended_citation() -> None:
    async def call() -> dict[str, object]:
        return {"data": []}

    result = await run_mcp_tool("demo", call)
    assert "GTEx Consortium" in result["_meta"]["recommended_citation"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_envelope.py::test_success_meta_includes_recommended_citation -v`
Expected: FAIL — key absent.

- [ ] **Step 3: Add citation constants to `resources.py`**

Append to `gtex_link/mcp/resources.py`:

```python
RECOMMENDED_CITATION = (
    "GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects "
    "across human tissues. Science. 2020;369(6509):1318-1330. "
    "doi:10.1126/science.aaz1776"
)

GTEX_USAGE_NOTES = (
    "Resolve a gene with `search` (natural language) or `search_gtex_genes`, "
    "then `get_median_expression_levels` (use sort+top_n for the peak tissue) "
    "or `get_top_expressed_genes_by_tissue`. response_mode=compact is the "
    "default; pass response_mode=full or include_spread=true to widen. Follow "
    "`_meta.next_commands` to advance without guessing the next tool."
)

GTEX_REFERENCE_NOTES = (
    "Error codes: not_found, invalid_input, validation_failed, rate_limited, "
    "upstream_unavailable, internal_error. Errors carry retryable + "
    "recovery_action (retry_backoff | reformulate_input | switch_tool) and, for "
    "validation failures, field_errors. numSamples is the per-tissue RNA-seq "
    "sample denominator (gene-independent). Spread (min/max/quartiles/IQR) is "
    "opt-in via include_spread. Rate limit: 5 req/s (token bucket)."
)
```

- [ ] **Step 4: Add citation to provenance in `envelope.py`**

In `gtex_link/mcp/envelope.py`, import the constant and add it to `_BASE_META`:

```python
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION

_BASE_META: dict[str, Any] = {
    "unsafe_for_clinical_use": True,
    "gtex_release": GTEX_DATA_RELEASE,
    "recommended_citation": RECOMMENDED_CITATION,
}
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_envelope.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/resources.py gtex_link/mcp/envelope.py tests/test_mcp/test_envelope.py
git commit -m "feat(mcp): recommended_citation in provenance + usage/reference text"
```

---

## Task 2: Capabilities builder + content hash

**Files:**
- Create: `gtex_link/mcp/metadata.py`
- Modify: `gtex_link/mcp/profiles.py`
- Test: `tests/test_mcp/test_metadata.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp/test_metadata.py`:

```python
"""Tests for the capabilities surface."""

from __future__ import annotations

from gtex_link.mcp.metadata import build_capabilities, capabilities_version, valid_tissues


def test_valid_tissues_excludes_empty_sentinel() -> None:
    tissues = valid_tissues()
    assert "" not in tissues
    assert "Kidney_Medulla" in tissues
    assert len(tissues) == 54


def test_capabilities_has_expected_top_level_keys() -> None:
    caps = build_capabilities()
    for key in (
        "server", "server_version", "mcp_protocol_version", "gtex_release",
        "research_use_only", "datasets", "tissues", "tools", "error_codes",
        "response_fields", "capabilities_version", "citation",
    ):
        assert key in caps
    assert caps["mcp_protocol_version"] == "2025-11-25"
    assert "" not in caps["tissues"]
    assert "get_median_expression_levels" in caps["tools"]


def test_capabilities_version_is_stable() -> None:
    assert capabilities_version() == capabilities_version()
    assert len(capabilities_version()) == 16
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_metadata.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `gtex_link/mcp/metadata.py`**

```python
"""Capabilities discovery surface for GTEx-Link (parity with sibling -link servers)."""

from __future__ import annotations

import functools
import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

from gtex_link.mcp.profiles import MCPToolProfile, is_tool_in_profile
from gtex_link.mcp.resources import GTEX_DATA_RELEASE, RECOMMENDED_CITATION
from gtex_link.models.gtex import TissueSiteDetailId
from gtex_link.observability.metrics import record_mcp_tool_call

if TYPE_CHECKING:
    from fastmcp import FastMCP

_ALL_TOOLS = (
    "search",
    "fetch",
    "search_gtex_genes",
    "get_gene_information",
    "get_transcript_information",
    "get_median_expression_levels",
    "get_individual_expression_data",
    "get_top_expressed_genes_by_tissue",
    "get_server_capabilities",
)


def _server_version() -> str:
    try:
        return version("gtex-link")
    except PackageNotFoundError:
        return "0.0.0"


def valid_tissues() -> list[str]:
    """The advertised tissue vocabulary: real tissues only, no '' sentinel."""
    return [t.value for t in TissueSiteDetailId if t.value]


@functools.cache
def _surface() -> dict[str, Any]:
    surface: dict[str, Any] = {
        "server": "gtex-link",
        "server_version": _server_version(),
        "mcp_protocol_version": "2025-11-25",
        "gtex_release": GTEX_DATA_RELEASE,
        "research_use_only": True,
        "datasets": ["gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"],
        "tissues": valid_tissues(),
        "tools": list(_ALL_TOOLS),
        "recommended_workflows": [
            "natural language -> search -> fetch",
            "gene symbol -> search_gtex_genes -> get_gene_information -> get_median_expression_levels",
            "tissue -> get_top_expressed_genes_by_tissue",
        ],
        "response_modes": {
            "compact": "default; per-tissue tissue/median/n only",
            "full": "adds ontologyId per tissue",
            "include_spread": "opt-in min/max/quartiles/IQR (one extra upstream call)",
        },
        "error_codes": [
            "not_found", "invalid_input", "validation_failed",
            "rate_limited", "upstream_unavailable", "internal_error",
        ],
        "parameter_conventions": {
            "gene_id": "symbols or GENCODE IDs; symbols auto-resolved",
            "tissue_site_detail_id": "one of `tissues`; omit for all tissues",
            "sort": "desc (default) | asc | none",
            "top_n": "limit tissues per gene for the peak-expression question",
        },
        "token_cost_hints": {
            "search": "~1-3kB",
            "get_median_expression_levels": "compact ~1-4kB; full/include_spread larger",
            "get_individual_expression_data": "high volume; bound page_size",
            "get_server_capabilities": "<3kB",
        },
        "limitations": [
            "Rate-limited to 5 req/s (token bucket).",
            "numSamples is the per-tissue RNA-seq denominator (gene-independent).",
            "Spread requires per-sample arrays (opt-in); no precomputed quartile endpoint.",
            "Research use only; not for clinical decision support.",
        ],
        "concurrency": {"rate_limit_per_second": 5},
        "response_fields": {
            "headline": "one-line plain-English answer at the top of median results",
            "next_commands": "_meta.next_commands: ready-to-call {tool, arguments} next steps",
            "recommended_citation": "_meta.recommended_citation: paste verbatim",
        },
        "resources": {
            "gtex://capabilities": "this document",
            "gtex://usage": "compact usage notes",
            "gtex://reference": "error taxonomy + field glossary",
            "gtex://research-use": "research-use-only notice",
            "gtex://citations": "GTEx citation",
        },
        "citation": RECOMMENDED_CITATION,
    }
    digest = hashlib.sha256(
        json.dumps(surface, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()[:16]
    surface["capabilities_version"] = digest
    return surface


def capabilities_version() -> str:
    """16-char content hash of the capabilities surface for cache invalidation."""
    return _surface()["capabilities_version"]


def build_capabilities() -> dict[str, Any]:
    """Return the full capabilities document (cached)."""
    return dict(_surface())


def register_metadata_tools(mcp: FastMCP, *, profile: MCPToolProfile) -> None:
    """Register the get_server_capabilities discovery tool."""
    if not is_tool_in_profile("get_server_capabilities", profile):
        return

    @mcp.tool(
        name="get_server_capabilities",
        title="Get Server Capabilities",
        description=(
            "Return supported tools, datasets, the tissue vocabulary, recommended "
            "workflows, response modes, error codes, and limits. Compare "
            "`capabilities_version` to skip re-fetching when unchanged."
        ),
    )
    async def get_server_capabilities() -> dict[str, Any]:
        record_mcp_tool_call(tool="get_server_capabilities", success=True)
        return build_capabilities()
```

- [ ] **Step 4: Add the tool to the lite profile**

In `gtex_link/mcp/profiles.py`, add `"get_server_capabilities"` to the `LITE_TOOLS` frozenset.

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_metadata.py -v`
Expected: PASS (3 tests).

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/metadata.py gtex_link/mcp/profiles.py tests/test_mcp/test_metadata.py
git commit -m "feat(mcp): get_server_capabilities tool + content hash"
```

---

## Task 3: Register the tool + `gtex://` resources in the facade

**Files:**
- Create: `gtex_link/mcp/capabilities_resources.py`
- Modify: `gtex_link/mcp/facade.py`
- Test: `tests/test_mcp/test_facade.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_facade.py`:

```python
import pytest
from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile


@pytest.mark.asyncio
async def test_capabilities_tool_and_resources_registered() -> None:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tool_names = {t.name for t in await mcp.list_tools()}
    assert "get_server_capabilities" in tool_names

    resources = await mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "gtex://capabilities" in uris
    assert "gtex://reference" in uris
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_facade.py::test_capabilities_tool_and_resources_registered -v`
Expected: FAIL — neither registered.

- [ ] **Step 3: Implement `gtex_link/mcp/capabilities_resources.py`**

```python
"""Register gtex:// discovery resources on a FastMCP instance."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.metadata import build_capabilities
from gtex_link.mcp.resources import (
    GTEX_REFERENCE_NOTES,
    GTEX_USAGE_NOTES,
    RECOMMENDED_CITATION,
    RESEARCH_USE_NOTICE,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_capability_resources(mcp: FastMCP) -> None:
    """Register the gtex:// resource family."""

    @mcp.resource("gtex://capabilities", mime_type="application/json")
    def capabilities() -> str:
        return json.dumps(build_capabilities())

    @mcp.resource("gtex://usage", mime_type="text/plain")
    def usage() -> str:
        return GTEX_USAGE_NOTES

    @mcp.resource("gtex://reference", mime_type="text/plain")
    def reference() -> str:
        return GTEX_REFERENCE_NOTES

    @mcp.resource("gtex://research-use", mime_type="text/plain")
    def research_use() -> str:
        return RESEARCH_USE_NOTICE

    @mcp.resource("gtex://citations", mime_type="text/plain")
    def citations() -> str:
        return RECOMMENDED_CITATION
```

- [ ] **Step 4: Wire into `gtex_link/mcp/facade.py`**

Add imports and registration calls in `create_gtex_mcp`, after the existing `register_*_tools(...)` calls and before `install_output_validation_error_handler(mcp)`:

```python
from gtex_link.mcp.capabilities_resources import register_capability_resources
from gtex_link.mcp.metadata import register_metadata_tools
```

```python
    register_search_fetch_tools(mcp, profile=selected)
    register_reference_tools(mcp, profile=selected)
    register_expression_tools(mcp, profile=selected)
    register_metadata_tools(mcp, profile=selected)
    register_capability_resources(mcp)

    install_output_validation_error_handler(mcp)
    return mcp
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_facade.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/capabilities_resources.py gtex_link/mcp/facade.py tests/test_mcp/test_facade.py
git commit -m "feat(mcp): register capabilities tool + gtex:// resources"
```

---

## Task 4: Tissue-vocabulary hygiene on the top-expressed tool

**Files:**
- Modify: `gtex_link/mcp/tools/expression.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

The internal `TissueSiteDetailId` enum keeps `""` for request-omission compatibility, but it must not be a usable public input on the tissue-required tool. Validate the input against `valid_tissues()` and echo the vocabulary on error.

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_top_expressed_rejects_empty_tissue_with_valid_values() -> None:
    mock_service = AsyncMock()

    with patch_service(mock_service):
        payload = await _call_tool("get_top_expressed_genes_by_tissue", {"tissue_site_detail_id": ""})

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
    assert "Kidney_Medulla" in payload["message"]
    mock_service.get_top_expressed_genes.assert_not_awaited()
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py::test_top_expressed_rejects_empty_tissue_with_valid_values -v`
Expected: FAIL — empty string currently passes through.

- [ ] **Step 3: Add validation in the top-expressed `call()`**

In `gtex_link/mcp/tools/expression.py`, import:

```python
from gtex_link.mcp.envelope import McpToolError
from gtex_link.mcp.metadata import valid_tissues
```

At the top of the top-expressed tool's `call()`, before building the request:

```python
            async def call() -> dict[str, Any]:
                allowed = valid_tissues()
                if tissue_site_detail_id not in allowed:
                    sample = ", ".join(allowed[:8])
                    raise McpToolError(
                        error_code="invalid_input",
                        message=(
                            f"Unknown tissue_site_detail_id {tissue_site_detail_id!r}. "
                            f"Valid values include: {sample}, ... ({len(allowed)} total; "
                            "see get_server_capabilities.tissues)."
                        ),
                    )
                service = get_gtex_service()
                ...  # unchanged from here
```

> Avoid a circular import: `metadata.py` imports from `profiles`/`resources`/`models`, none of which import `tools.expression`, so this import is safe.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "top_expressed" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): validate tissue vocabulary on top-expressed tool"
```

---

## Task 5: Full verification + the institutionalized eval

**Files:**
- Create: `tests/test_mcp/test_surface_eval.py` (the spec's PR-anchoring eval artifact)

- [ ] **Step 1: Write the eval test (the reviewer's failing calls, now passing)**

Create `tests/test_mcp/test_surface_eval.py`:

```python
"""Institutionalized eval: the PKD1/UMOD task that motivated the redesign.

Asserts correctness and a token/byte budget so the dimension scores stay
repeatable. Uses mocked upstream data; this is a surface contract test, not a
live-API test.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.models.responses import (
    Gene, MedianGeneExpression, PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse, PaginatedTissueSiteDetailResponse,
    PaginationInfo, TissueSiteDetail,
)
from tests.test_mcp.test_tool_bodies import patch_service  # reuse the patcher


def _paging(total: int) -> PaginationInfo:
    return PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=total)


def _umod_gene() -> Gene:
    return Gene.model_validate(
        {"chromosome": "chr16", "dataSource": "GENCODE", "description": "uromodulin",
         "end": 20356301, "entrezGeneId": 7369, "gencodeId": "ENSG00000169344.15",
         "gencodeVersion": "v26", "geneStatus": "KNOWN", "geneSymbol": "UMOD",
         "geneSymbolUpper": "UMOD", "geneType": "protein_coding", "genomeBuild": "GRCh38",
         "start": 20333052, "strand": "-", "tss": 20356301}
    )


def _tissue(tid: str, n: int) -> TissueSiteDetail:
    return TissueSiteDetail.model_validate(
        {"tissueSiteDetailId": tid, "colorHex": "0", "colorRgb": "0", "datasetId": "gtex_v8",
         "eGeneCount": None, "expressedGeneCount": 1, "hasEGenes": False, "hasSGenes": False,
         "mappedInHubmap": False, "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
         "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}}, "sGeneCount": None,
         "samplingSite": "x", "tissueSite": "x", "tissueSiteDetail": "x",
         "tissueSiteDetailAbbr": "x", "ontologyId": "UBERON:1", "ontologyIri": "http://x"}
    )


def _median(tissue: str, value: float) -> MedianGeneExpression:
    return MedianGeneExpression.model_validate(
        {"datasetId": "gtex_v8", "ontologyId": "UBERON:1", "gencodeId": "ENSG00000169344.15",
         "geneSymbol": "UMOD", "median": value, "numSamples": None,
         "tissueSiteDetailId": tissue, "unit": "TPM"}
    )


async def _call(name: str, args: dict) -> dict:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    result = await mcp.call_tool(name, args)
    return json.loads(result.content[0].text)


@pytest.mark.asyncio
async def test_eval_search_nl_returns_umod() -> None:
    async def fake_search(query: str, **kw) -> PaginatedGeneResponse:
        return (
            PaginatedGeneResponse(data=[_umod_gene()], pagingInfo=_paging(1))
            if query.lower() == "umod"
            else PaginatedGeneResponse(data=[], pagingInfo=_paging(0))
        )

    svc = AsyncMock()
    svc.search_genes = AsyncMock(side_effect=fake_search)
    with patch_service(svc):
        payload = await _call("search", {"query": "UMOD kidney expression"})
    assert any(r["id"] == "gene:ENSG00000169344.15" for r in payload["results"])


@pytest.mark.asyncio
async def test_eval_median_top_tissue_is_kidney_medulla_and_compact() -> None:
    svc = AsyncMock()
    svc.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(
            data=[_median("Adipose_Subcutaneous", 0.0), _median("Kidney_Medulla", 2116.02),
                  _median("Kidney_Cortex", 190.13)],
            pagingInfo=_paging(3),
        )
    )
    svc.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[_tissue("Kidney_Medulla", 4)], pagingInfo=_paging(1))
    )
    with patch_service(svc):
        result_obj = create_gtex_mcp(profile=MCPToolProfile.FULL)
        raw = await result_obj.call_tool(
            "get_median_expression_levels",
            {"gencode_id": ["ENSG00000169344.15"], "top_n": 1},
        )
    payload = json.loads(raw.content[0].text)
    top = payload["genes"][0]["tissues"][0]
    assert top["tissue"] == "Kidney_Medulla"
    assert top["n"] == 4
    # Token budget: the compact top_n=1 payload stays small.
    assert len(raw.content[0].text) < 1200


@pytest.mark.asyncio
async def test_eval_symbol_input_never_silent_empty() -> None:
    svc = AsyncMock()
    svc.get_genes = AsyncMock(return_value=PaginatedGeneResponse(data=[], pagingInfo=_paging(0)))
    with patch_service(svc):
        payload = await _call("get_median_expression_levels", {"gencode_id": ["NOTAGENE"]})
    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
```

- [ ] **Step 2: Run the eval**

Run: `uv run pytest tests/test_mcp/test_surface_eval.py -v`
Expected: PASS (3 tests).

- [ ] **Step 3: Run the full gate**

Run: `make ci-local`
Expected: PASS (format, lint, lint-loc, typecheck, all tests; coverage >= 90%).

- [ ] **Step 4: Live smoke**

`get_server_capabilities()` returns the document with `mcp_protocol_version: "2025-11-25"`, a 54-entry `tissues` list (no `""`), and a `capabilities_version`. Read `gtex://reference`. Confirm `_meta.recommended_citation` appears on a successful tool call.

- [ ] **Step 5: Commit**

```bash
git add tests/test_mcp/test_surface_eval.py
git commit -m "test(mcp): institutionalize PKD1/UMOD surface eval"
```

---

## Self-Review Notes

- **Spec coverage:** capabilities tool + `gtex://` resources + content hash (Tasks 2-3), tissue-vocabulary hygiene / drop `""` from the public surface (Tasks 2,4), citation surface (Task 1), concurrency documented in capabilities (Task 2), MCP revision 2025-11-25 reported (Task 2), institutionalized eval (Task 5).
- **Type consistency:** `valid_tissues`, `build_capabilities`, `capabilities_version`, `register_metadata_tools`, `register_capability_resources` consistent across tasks. The lite profile now includes `get_server_capabilities`.
- **Vocabulary note:** the internal `TissueSiteDetailId` enum retains `""` only for request-omission compatibility (the service converts `""`→omit); it is no longer advertised (`valid_tissues()` filters it) and is rejected as input on the tissue-required tool.
- **Cross-PR dimension outcome:** with PR1-PR4 merged, all six review dimensions reach ≥9 — correctness (PR1), token efficiency (PR3), observability (PR2), consistency (PR1-PR2 envelope), discoverability (PR4), speed (fewer round-trips across PR1/PR3 + cached `n`).
