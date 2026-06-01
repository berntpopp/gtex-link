# PR2 — Observability & Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every median row carries the sample count behind it, failures become richly recoverable, and every tool is honestly annotated as read-only.

**Architecture:** Populate `numSamples` from a cached, gene-independent per-tissue map sourced from `dataset/tissueSiteDetail.rnaSeqSampleSummary.totalCount` (one cold call per dataset; the service's `get_tissue_site_details` is already cached). Add opt-in spread (`include_spread`, default off) derived from `geneExpression` per-sample arrays. Enrich the PR1 error envelope with `retryable`, `recovery_action`, and `field_errors`. Apply `READ_ONLY_OPEN_WORLD` annotations + `title` + `tags` to every tool.

**Tech Stack:** Python 3.12, FastMCP `ToolAnnotations`, Pydantic v2, statistics (stdlib), pytest.

**Spec:** `docs/superpowers/specs/2026-06-01-mcp-excellence-design.md` (PR2). Depends on PR1 (envelope, `run_mcp_tool`).

**Deviation from spec note:** `output_schema` (spec PR2 bullet) is intentionally deferred to **PR3**, where the gene-grouped typed response models are defined — deriving a schema in PR2 for shapes that PR3 immediately replaces would be wasted work. PR2 ships annotations + the error taxonomy + observability data; PR3 adds `output_schema` against the final models.

---

## File Structure

- Create `gtex_link/mcp/tissue_stats.py` — `sample_count_map(service, dataset_id)` and `compute_spread(values)`. One responsibility: tissue sample-size lookup + per-tissue distribution stats. (~80 lines)
- Create `gtex_link/mcp/annotations.py` — `READ_ONLY_OPEN_WORLD`. (~12 lines)
- Modify `gtex_link/mcp/envelope.py` — extend `_classify` to also yield `retryable`/`recovery_action`; add `field_errors` for Pydantic errors.
- Modify `gtex_link/mcp/tools/expression.py` — `n` enrichment + `include_spread` on the median tool; annotations on all three tools.
- Modify `gtex_link/mcp/tools/reference.py`, `gtex_link/mcp/tools/search_fetch.py` — annotations + `title`.
- Tests: `tests/test_mcp/test_tissue_stats.py` (new); extend `tests/test_mcp/test_envelope.py`, `tests/test_mcp/test_tool_bodies.py`, `tests/test_mcp/test_tools_search_fetch.py`.

---

## Task 1: Tissue sample-count map + spread stats

**Files:**
- Create: `gtex_link/mcp/tissue_stats.py`
- Test: `tests/test_mcp/test_tissue_stats.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp/test_tissue_stats.py`:

```python
"""Tests for tissue sample-count map and spread stats."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gtex_link.mcp.tissue_stats import compute_spread, sample_count_map
from gtex_link.models.responses import (
    PaginatedTissueSiteDetailResponse,
    PaginationInfo,
    TissueSiteDetail,
)


def _tissue(tid: str, n: int) -> TissueSiteDetail:
    return TissueSiteDetail.model_validate(
        {
            "tissueSiteDetailId": tid, "colorHex": "000000", "colorRgb": "0,0,0",
            "datasetId": "gtex_v8", "eGeneCount": None, "expressedGeneCount": 1,
            "hasEGenes": False, "hasSGenes": False, "mappedInHubmap": False,
            "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
            "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}},
            "sGeneCount": None, "samplingSite": "x", "tissueSite": "x",
            "tissueSiteDetail": "x", "tissueSiteDetailAbbr": "x",
            "ontologyId": "UBERON:1", "ontologyIri": "http://x",
        }
    )


@pytest.mark.asyncio
async def test_sample_count_map_builds_tissue_to_n() -> None:
    service = AsyncMock()
    service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(
            data=[_tissue("Kidney_Medulla", 4), _tissue("Muscle_Skeletal", 803)],
            pagingInfo=PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=2),
        )
    )

    result = await sample_count_map(service, "gtex_v8")

    assert result == {"Kidney_Medulla": 4, "Muscle_Skeletal": 803}


def test_compute_spread_quartiles() -> None:
    spread = compute_spread([1224.0, 1837.0, 2395.0, 3766.0])
    assert spread["n"] == 4
    assert spread["min"] == 1224.0
    assert spread["max"] == 3766.0
    assert spread["q1"] <= spread["median"] <= spread["q3"]
    assert spread["iqr"] == pytest.approx(spread["q3"] - spread["q1"])


def test_compute_spread_empty_is_none() -> None:
    assert compute_spread([]) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tissue_stats.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `gtex_link/mcp/tissue_stats.py`**

```python
"""Tissue sample-size lookup and per-tissue distribution stats.

Per-tissue RNA-seq sample count is a dataset-level constant from
dataset/tissueSiteDetail.rnaSeqSampleSummary.totalCount (gene-independent),
so one cached call per dataset feeds `numSamples` on every median row with no
per-query round trip. Spread (min/max/quartiles/IQR) has no precomputed GTEx
endpoint and is derived from geneExpression per-sample arrays on demand.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Any

from gtex_link.models import TissueSiteDetailRequest

if TYPE_CHECKING:
    from gtex_link.services.gtex_service import GTExService


async def sample_count_map(service: GTExService, dataset_id: str) -> dict[str, int]:
    """Return {tissueSiteDetailId: rnaSeqSampleSummary.totalCount} for *dataset_id*.

    Backed by the service's already-cached get_tissue_site_details, so repeated
    calls within the cache TTL cost nothing.
    """
    request = TissueSiteDetailRequest.model_validate({"datasetId": dataset_id})
    result = await service.get_tissue_site_details(request)
    return {
        row.tissue_site_detail_id: row.rna_seq_sample_summary.total_count
        for row in result.data
    }


def compute_spread(values: list[float]) -> dict[str, Any] | None:
    """Return distribution stats for a per-sample value list, or None if empty."""
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n >= 2:
        quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
        q1, _med, q3 = quartiles[0], quartiles[1], quartiles[2]
    else:
        q1 = q3 = ordered[0]
    return {
        "n": n,
        "min": ordered[0],
        "max": ordered[-1],
        "q1": round(q1, 4),
        "median": round(statistics.median(ordered), 4),
        "q3": round(q3, 4),
        "iqr": round(q3 - q1, 4),
    }
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tissue_stats.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tissue_stats.py tests/test_mcp/test_tissue_stats.py
git commit -m "feat(mcp): tissue sample-count map + spread stats"
```

---

## Task 2: Populate `numSamples` on median rows

**Files:**
- Modify: `gtex_link/mcp/tools/expression.py` (median tool `call()` body)
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_median_populates_num_samples_from_tissue_map() -> None:
    from gtex_link.models.responses import (
        PaginatedTissueSiteDetailResponse,
        TissueSiteDetail,
    )

    def _tissue(tid: str, n: int) -> TissueSiteDetail:
        return TissueSiteDetail.model_validate(
            {
                "tissueSiteDetailId": tid, "colorHex": "0", "colorRgb": "0",
                "datasetId": "gtex_v8", "eGeneCount": None, "expressedGeneCount": 1,
                "hasEGenes": False, "hasSGenes": False, "mappedInHubmap": False,
                "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "sGeneCount": None, "samplingSite": "x", "tissueSite": "x",
                "tissueSiteDetail": "x", "tissueSiteDetailAbbr": "x",
                "ontologyId": "UBERON:1", "ontologyIri": "http://x",
            }
        )

    row = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8", "ontologyId": "UBERON:1", "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD", "median": 2116.02, "numSamples": None,
            "tissueSiteDetailId": "Kidney_Medulla", "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[row], pagingInfo=_paging(1))
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(
            data=[_tissue("Kidney_Medulla", 4)], pagingInfo=_paging(1)
        )
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_median_expression_levels", {"gencode_id": ["ENSG00000169344.15"]}
        )

    assert payload["data"][0]["numSamples"] == 4
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py::test_median_populates_num_samples_from_tissue_map -v`
Expected: FAIL — `numSamples` is `None`.

- [ ] **Step 3: Enrich the median `call()` body**

In `gtex_link/mcp/tools/expression.py`, add the import:

```python
from gtex_link.mcp.tissue_stats import compute_spread, sample_count_map
```

Replace the median tool's `call()` body (return statement region) with:

```python
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
                data = result.model_dump(by_alias=True)

                counts = await sample_count_map(service, dataset_id)
                for row in data["data"]:
                    row["numSamples"] = counts.get(row["tissueSiteDetailId"])
                return data
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "median" -v`
Expected: PASS (including the existing median tests — they don't assert numSamples and the tissue map call returns an empty mock-safe map when `get_tissue_site_details` is unset; ensure those mocks set it or accept `None`).

> If a pre-existing median test's `mock_service` lacks `get_tissue_site_details`, set it to return an empty `PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))` so `counts` is `{}` and `numSamples` stays `None`.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): populate numSamples from cached tissue map"
```

---

## Task 3: Opt-in spread on the median tool

**Files:**
- Modify: `gtex_link/mcp/tools/expression.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_median_include_spread_attaches_distribution() -> None:
    row = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8", "ontologyId": "UBERON:1", "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD", "median": 2116.02, "numSamples": None,
            "tissueSiteDetailId": "Kidney_Medulla", "unit": "TPM",
        }
    )
    expr = GeneExpression.model_validate(
        {
            "data": [1224.0, 1837.0, 2395.0, 3766.0], "datasetId": "gtex_v8",
            "tissueSiteDetailId": "Kidney_Medulla", "ontologyId": "UBERON:1",
            "subsetGroup": None, "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD", "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[row], pagingInfo=_paging(1))
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
    )
    mock_service.get_gene_expression = AsyncMock(
        return_value=PaginatedGeneExpressionResponse(data=[expr], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_median_expression_levels",
            {"gencode_id": ["ENSG00000169344.15"], "include_spread": True},
        )

    spread = payload["data"][0]["spread"]
    assert spread["min"] == 1224.0 and spread["max"] == 3766.0
    assert spread["iqr"] >= 0


@pytest.mark.asyncio
async def test_median_default_omits_spread() -> None:
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[], pagingInfo=_paging(0))
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        await _call_tool("get_median_expression_levels", {"gencode_id": ["ENSG00000169344.15"]})

    mock_service.get_gene_expression.assert_not_awaited()
```

Add the needed import at the top of the test module if missing: `PaginatedTissueSiteDetailResponse`, `GeneExpression`, `PaginatedGeneExpressionResponse` (some already imported).

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "spread" -v`
Expected: FAIL — `include_spread` param does not exist.

- [ ] **Step 3: Add `include_spread` to the median tool**

Change the median tool signature to add `include_spread: bool = False` (after `page_size`), update the description to mention it, and append spread enrichment after the `numSamples` loop in `call()`:

```python
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            page: int = 0,
            page_size: int = 100,
            include_spread: bool = False,
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
                data = result.model_dump(by_alias=True)

                counts = await sample_count_map(service, dataset_id)
                for row in data["data"]:
                    row["numSamples"] = counts.get(row["tissueSiteDetailId"])

                if include_spread and data["data"]:
                    spread_payload: dict[str, object] = {
                        "gencodeId": resolved,
                        "datasetId": dataset_id,
                        "page": 0,
                        "itemsPerPage": 1000,
                    }
                    if tissue_site_detail_id is not None:
                        spread_payload["tissueSiteDetailId"] = tissue_site_detail_id
                    expr = await service.get_gene_expression(
                        GeneExpressionRequest.model_validate(spread_payload)
                    )
                    by_key = {(r.gencode_id, r.tissue_site_detail_id): r.data for r in expr.data}
                    for row in data["data"]:
                        values = by_key.get((row["gencodeId"], row["tissueSiteDetailId"]), [])
                        row["spread"] = compute_spread(values)
                return data
```

(The description should add: " Set `include_spread=true` for per-tissue min/max/quartiles/IQR (one extra upstream call).")

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "spread or median" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): opt-in per-tissue spread on median tool"
```

---

## Task 4: Enrich the error envelope (retryable, recovery_action, field_errors)

**Files:**
- Modify: `gtex_link/mcp/envelope.py`
- Test: `tests/test_mcp/test_envelope.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_mcp/test_envelope.py`:

```python
@pytest.mark.asyncio
async def test_rate_limited_is_retryable_with_backoff() -> None:
    async def call() -> dict[str, object]:
        raise RateLimitError("slow")

    result = await run_mcp_tool("demo", call)
    assert result["retryable"] is True
    assert result["recovery_action"] == "retry_backoff"


@pytest.mark.asyncio
async def test_invalid_input_is_not_retryable_reformulate() -> None:
    async def call() -> dict[str, object]:
        raise ValidationError("bad", field="gencode_id")

    result = await run_mcp_tool("demo", call)
    assert result["retryable"] is False
    assert result["recovery_action"] == "reformulate_input"


@pytest.mark.asyncio
async def test_pydantic_error_lists_field_errors() -> None:
    from gtex_link.models import MedianGeneExpressionRequest

    async def call() -> dict[str, object]:
        MedianGeneExpressionRequest.model_validate({"gencodeId": []})  # min_length=1 violation
        return {}

    result = await run_mcp_tool("demo", call)
    assert result["error_code"] == "invalid_input"
    assert isinstance(result["field_errors"], list)
    assert result["field_errors"][0]["field"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_envelope.py -k "retryable or reformulate or field_errors" -v`
Expected: FAIL — keys absent.

- [ ] **Step 3: Extend `_classify` and `_error_envelope` in `gtex_link/mcp/envelope.py`**

Replace `_classify` to also return `retryable`, and add helpers + `field_errors`:

```python
def _classify(exc: BaseException) -> tuple[str, str, bool]:
    """Return (error_code, client_safe_message, retryable)."""
    if isinstance(exc, McpToolError):
        return exc.error_code, exc.message, exc.error_code in {"rate_limited", "upstream_unavailable"}
    if isinstance(exc, RateLimitError):
        return "rate_limited", "GTEx Portal rate limit exceeded. Try again shortly.", True
    if isinstance(exc, ServiceUnavailableError):
        return "upstream_unavailable", "GTEx Portal is temporarily unavailable. Try again later.", True
    if isinstance(exc, PydanticValidationError):
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"]) or "input"
        return "invalid_input", f"Invalid input -- `{loc}`: {first['msg']}", False
    if isinstance(exc, ValidationError):
        field = f"`{exc.field}`: " if exc.field else ""
        return "invalid_input", f"Invalid input -- {field}{exc.message}", False
    if isinstance(exc, GTExAPIError):
        return "upstream_unavailable", "GTEx Portal returned an error. Verify the request inputs.", True
    return "internal_error", "An internal error occurred. The request was not completed.", False


def _recovery_action(error_code: str, retryable: bool) -> str:
    if retryable:
        return "retry_backoff"
    if error_code in {"invalid_input", "validation_failed"}:
        return "reformulate_input"
    return "switch_tool"


def _field_errors(exc: BaseException) -> list[dict[str, str]] | None:
    if not isinstance(exc, PydanticValidationError):
        return None
    return [
        {"field": ".".join(str(p) for p in e["loc"]) or "input", "reason": e["msg"]}
        for e in exc.errors()
    ]


def _error_envelope(exc: BaseException, context: McpErrorContext) -> dict[str, Any]:
    error_code, message, retryable = _classify(exc)
    envelope: dict[str, Any] = {
        "success": False,
        "error_code": error_code,
        "message": message,
        "retryable": retryable,
        "recovery_action": _recovery_action(error_code, retryable),
        "_meta": {"tool": context.tool_name, **_provenance_meta(context)},
    }
    field_errors = _field_errors(exc)
    if field_errors is not None:
        envelope["field_errors"] = field_errors
    return envelope
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_envelope.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/envelope.py tests/test_mcp/test_envelope.py
git commit -m "feat(mcp): enrich error envelope with retryable/recovery_action/field_errors"
```

---

## Task 5: Read-only tool annotations + titles

**Files:**
- Create: `gtex_link/mcp/annotations.py`
- Modify: `gtex_link/mcp/tools/{reference,expression,search_fetch}.py`
- Test: `tests/test_mcp/test_tools_search_fetch.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_tools_search_fetch.py`:

```python
@pytest.mark.asyncio
async def test_tools_are_annotated_read_only() -> None:
    from gtex_link.mcp.facade import create_gtex_mcp

    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    tools = {t.name: t for t in await mcp.list_tools()}
    median = tools["get_median_expression_levels"]
    assert median.annotations is not None
    assert median.annotations.readOnlyHint is True
    assert median.annotations.openWorldHint is True
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tools_search_fetch.py::test_tools_are_annotated_read_only -v`
Expected: FAIL — `annotations` is None.

- [ ] **Step 3: Create `gtex_link/mcp/annotations.py`**

```python
"""Shared MCP tool annotations for GTEx-Link (read-only research server)."""

from __future__ import annotations

from mcp.types import ToolAnnotations

READ_ONLY_OPEN_WORLD = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=True,
)
```

- [ ] **Step 4: Apply annotations + title to every `@mcp.tool`**

In each of the three tool modules, add the import:

```python
from gtex_link.mcp.annotations import READ_ONLY_OPEN_WORLD
```

Then add `annotations=READ_ONLY_OPEN_WORLD` and a `title` + `tags` to each decorator. Example for the median tool:

```python
        @mcp.tool(
            name="get_median_expression_levels",
            title="Get Median Expression Levels",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"expression"},
            description=(...),  # unchanged
        )
```

Apply analogously (matching `title`/`tags`) to: `search` (`tags={"search"}`), `fetch` (`tags={"search"}`), `search_gtex_genes` (`tags={"reference","search"}`), `get_gene_information` (`tags={"reference"}`), `get_transcript_information` (`tags={"reference"}`), `get_individual_expression_data` (`tags={"expression"}`), `get_top_expressed_genes_by_tissue` (`tags={"expression"}`).

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_mcp/ -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/annotations.py gtex_link/mcp/tools/*.py tests/test_mcp/test_tools_search_fetch.py
git commit -m "feat(mcp): read-only annotations + titles + tags on all tools"
```

---

## Task 6: Full verification

- [ ] **Step 1:** Run `make ci-local` — expect PASS (coverage >= 90%).
- [ ] **Step 2:** Live smoke: `get_median_expression_levels(["UMOD"])` rows carry `numSamples` (Kidney_Medulla = 4); add `include_spread=true` and confirm `spread` with min/max/iqr; trigger a validation error and confirm `error_code`/`retryable`/`recovery_action`/`field_errors`.
- [ ] **Step 3:** Commit any fixups.

---

## Self-Review Notes

- **Spec coverage:** real `n` (Task 1-2), opt-in spread (Task 3), error taxonomy + field_errors (Task 4), annotations + `_meta` provenance — provenance already injected by PR1's `run_mcp_tool` and unchanged here (Task 5). `output_schema` deferred to PR3 (documented above).
- **Type consistency:** `sample_count_map`, `compute_spread`, `READ_ONLY_OPEN_WORLD`, `_classify` (now 3-tuple), `_recovery_action`, `_field_errors` used consistently. Note `_classify` signature changed from PR1's 2-tuple to a 3-tuple — `_error_envelope` updated in the same task.
- **`n` semantics:** `numSamples` is the tissue sample denominator from the cached map; `include_spread`'s `compute_spread(...)["n"]` is the per-gene array length and may legitimately differ — both are reported, neither overwrites the other.
