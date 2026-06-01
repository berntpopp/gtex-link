# PR3 — Token Efficiency & Chaining Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut median-expression payload tokens ~50-60%, remove the pagination-splits-a-gene footgun, answer "where is this expressed most?" in one small call, and emit chaining hints + a one-line headline — all under a typed `output_schema`.

**Architecture:** Introduce gene-grouped typed result models (`MedianExpressionResult` → `GeneMedianGroup` → `TissueMedian`) that hoist invariants (`datasetId`/`unit`/`geneSymbol`/`gencodeId`) to the gene parent so per-tissue rows carry only `tissue`/`median`/`n` (+ optional `ontologyId`/`spread` in `full`). The median tool fetches all tissues for the requested (bounded ≤50) genes, groups by gene, applies `sort`/`top_n` per gene, slices the **gene list** for pagination (never a gene's tissues), attaches a `headline` and `_meta.next_commands`, and publishes a relaxed `output_schema`.

**Tech Stack:** Python 3.12, Pydantic v2 (`BaseResponse` MCP-compatible schema), FastMCP `output_schema`.

**Spec:** `docs/superpowers/specs/2026-06-01-mcp-excellence-design.md` (PR3 + MCP Semantics: typed outputs, relaxed schema, page-based result pagination, app-level `_meta`). Depends on PR1 + PR2.

**Supersedes:** PR2's flat `numSamples`/`spread` enrichment of `data[]` rows — the same values now live in the grouped shape. PR2's `data[]` shape is replaced.

---

## File Structure

- Create `gtex_link/models/mcp_results.py` — `TissueMedian`, `GeneMedianGroup`, `MedianExpressionResult`. (~70 lines)
- Create `gtex_link/mcp/shaping.py` — `group_median(...)` (rows → `MedianExpressionResult`) and `median_headline(...)`. (~110 lines)
- Create `gtex_link/mcp/next_commands.py` — `cmd()` + builders. (~40 lines)
- Create `gtex_link/mcp/schema_relax.py` — `relax_output_schema` (port from `../gnomad-link`). (~60 lines)
- Modify `gtex_link/mcp/tools/expression.py` — median tool returns the grouped result + `sort`/`top_n`/`response_mode` params + `output_schema` + `next_commands`; `search_gtex_genes` (in reference.py) gets `next_commands`.
- Modify `gtex_link/mcp/tools/reference.py` — attach `next_commands` to `search_gtex_genes` / `get_gene_information`.
- Tests: `tests/test_mcp/test_shaping.py`, `tests/test_mcp/test_next_commands.py`, `tests/test_mcp/test_schema_relax.py` (new); update `tests/test_mcp/test_tool_bodies.py` median assertions.

---

## Task 1: Gene-grouped result models

**Files:**
- Create: `gtex_link/models/mcp_results.py`
- Test: `tests/test_models/test_mcp_results.py`

- [ ] **Step 1: Write a failing test**

Create `tests/test_models/test_mcp_results.py`:

```python
"""Tests for gene-grouped MCP result models."""

from __future__ import annotations

from gtex_link.models.mcp_results import GeneMedianGroup, MedianExpressionResult, TissueMedian
from gtex_link.models.responses import PaginationInfo


def test_grouped_result_serializes_camel_case() -> None:
    result = MedianExpressionResult(
        headline="UMOD: highest median in Kidney_Medulla (2116.02 TPM, n=4).",
        genes=[
            GeneMedianGroup(
                gencodeId="ENSG00000169344.15", geneSymbol="UMOD", datasetId="gtex_v8", unit="TPM",
                tissues=[TissueMedian(tissue="Kidney_Medulla", median=2116.02, n=4)],
                tissuesReturned=1, tissuesTotal=54,
            )
        ],
        pagingInfo=PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=50, totalNumberOfItems=1),
    )
    dumped = result.model_dump(by_alias=True)
    assert dumped["genes"][0]["gencodeId"] == "ENSG00000169344.15"
    assert dumped["genes"][0]["tissues"][0]["n"] == 4
    assert "headline" in dumped
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_models/test_mcp_results.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `gtex_link/models/mcp_results.py`**

```python
"""Gene-grouped MCP result models (token-efficient; invariants hoisted)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from gtex_link.models.responses import BaseResponse, PaginationInfo


class TissueMedian(BaseResponse):
    """One tissue's median for a gene. Invariants live on the parent group."""

    tissue: str
    median: float
    n: int | None = None
    ontology_id: str | None = Field(None, alias="ontologyId")
    spread: dict[str, Any] | None = None


class GeneMedianGroup(BaseResponse):
    """All requested tissues for one gene, with hoisted invariant fields."""

    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    dataset_id: str = Field(alias="datasetId")
    unit: str
    tissues: list[TissueMedian]
    tissues_returned: int = Field(alias="tissuesReturned")
    tissues_total: int = Field(alias="tissuesTotal")


class MedianExpressionResult(BaseResponse):
    """Top-level median-expression result: headline + gene groups + gene-list paging."""

    headline: str
    genes: list[GeneMedianGroup]
    paging_info: PaginationInfo = Field(alias="pagingInfo")
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_models/test_mcp_results.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/models/mcp_results.py tests/test_models/test_mcp_results.py
git commit -m "feat(models): gene-grouped MCP result models"
```

---

## Task 2: Shaping function (group + sort + top_n + headline)

**Files:**
- Create: `gtex_link/mcp/shaping.py`
- Test: `tests/test_mcp/test_shaping.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp/test_shaping.py`:

```python
"""Tests for median-row grouping/shaping."""

from __future__ import annotations

from gtex_link.mcp.shaping import group_median
from gtex_link.models.responses import MedianGeneExpression


def _row(tissue: str, value: float, gene: str = "UMOD", gencode: str = "ENSG00000169344.15") -> MedianGeneExpression:
    return MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8", "ontologyId": "UBERON:1", "gencodeId": gencode,
            "geneSymbol": gene, "median": value, "numSamples": None,
            "tissueSiteDetailId": tissue, "unit": "TPM",
        }
    )


def test_group_sorts_descending_and_applies_top_n() -> None:
    rows = [_row("Adipose_Subcutaneous", 0.0), _row("Kidney_Medulla", 2116.02), _row("Kidney_Cortex", 190.1)]
    result = group_median(
        rows, counts={"Kidney_Medulla": 4, "Kidney_Cortex": 85, "Adipose_Subcutaneous": 663},
        sort="desc", top_n=2, response_mode="compact", spread_by_key={},
    )
    group = result.genes[0]
    assert [t.tissue for t in group.tissues] == ["Kidney_Medulla", "Kidney_Cortex"]
    assert group.tissues[0].n == 4
    assert group.tissues_returned == 2
    assert group.tissues_total == 3
    assert "Kidney_Medulla" in result.headline and "2116.02" in result.headline


def test_compact_omits_ontology_full_includes_it() -> None:
    rows = [_row("Kidney_Medulla", 2116.02)]
    compact = group_median(rows, counts={}, sort="desc", top_n=None, response_mode="compact", spread_by_key={})
    full = group_median(rows, counts={}, sort="desc", top_n=None, response_mode="full", spread_by_key={})
    assert compact.genes[0].tissues[0].ontology_id is None
    assert full.genes[0].tissues[0].ontology_id == "UBERON:1"


def test_multiple_genes_grouped_separately() -> None:
    rows = [
        _row("Kidney_Medulla", 2116.0, "UMOD", "ENSG00000169344.15"),
        _row("Whole_Blood", 5.0, "BRCA1", "ENSG00000012048.22"),
    ]
    result = group_median(rows, counts={}, sort="desc", top_n=None, response_mode="compact", spread_by_key={})
    assert {g.gene_symbol for g in result.genes} == {"UMOD", "BRCA1"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_shaping.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `gtex_link/mcp/shaping.py`**

```python
"""Group flat median rows into the token-efficient gene-grouped result."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gtex_link.models.mcp_results import GeneMedianGroup, MedianExpressionResult, TissueMedian
from gtex_link.models.responses import PaginationInfo

if TYPE_CHECKING:
    from gtex_link.models.responses import MedianGeneExpression

SortMode = Literal["desc", "asc", "none"]
ResponseMode = Literal["compact", "full"]


def median_headline(genes: list[GeneMedianGroup]) -> str:
    """One-line plain-English answer placed first; null-safe, never raises."""
    if not genes:
        return "No median expression found for the requested gene(s)."
    first = genes[0]
    if not first.tissues:
        head = f"{first.gene_symbol}: no expression rows returned."
    else:
        top = first.tissues[0]
        n_txt = f", n={top.n}" if top.n is not None else ""
        head = (
            f"{first.gene_symbol}: highest median in {top.tissue} "
            f"({top.median:.2f} {first.unit}{n_txt})."
        )
    if len(genes) > 1:
        head += f" (+{len(genes) - 1} more gene(s))"
    return head


def group_median(
    rows: list[MedianGeneExpression],
    *,
    counts: dict[str, int],
    sort: SortMode,
    top_n: int | None,
    response_mode: ResponseMode,
    spread_by_key: dict[tuple[str, str], dict[str, Any] | None],
    page: int = 0,
    page_size: int = 50,
) -> MedianExpressionResult:
    """Group rows by gene, sort/top_n tissues, hoist invariants, paginate by gene."""
    # Preserve first-seen gene order.
    order: list[str] = []
    buckets: dict[str, list[MedianGeneExpression]] = {}
    for row in rows:
        if row.gencode_id not in buckets:
            buckets[row.gencode_id] = []
            order.append(row.gencode_id)
        buckets[row.gencode_id].append(row)

    groups: list[GeneMedianGroup] = []
    for gencode_id in order:
        gene_rows = buckets[gencode_id]
        if sort != "none":
            gene_rows = sorted(gene_rows, key=lambda r: r.median, reverse=(sort == "desc"))
        total = len(gene_rows)
        selected = gene_rows[:top_n] if top_n else gene_rows
        tissues = [
            TissueMedian(
                tissue=r.tissue_site_detail_id,
                median=r.median,
                n=counts.get(r.tissue_site_detail_id),
                ontologyId=r.ontology_id if response_mode == "full" else None,
                spread=spread_by_key.get((r.gencode_id, r.tissue_site_detail_id)),
            )
            for r in selected
        ]
        first = gene_rows[0]
        groups.append(
            GeneMedianGroup(
                gencodeId=gencode_id,
                geneSymbol=first.gene_symbol,
                datasetId=first.dataset_id,
                unit=first.unit,
                tissues=tissues,
                tissuesReturned=len(tissues),
                tissuesTotal=total,
            )
        )

    # Paginate the GENE list -- never split a gene's tissues across a page.
    total_genes = len(groups)
    start = page * page_size
    page_groups = groups[start : start + page_size]
    number_of_pages = (total_genes + page_size - 1) // page_size if page_size else 1
    return MedianExpressionResult(
        headline=median_headline(page_groups),
        genes=page_groups,
        pagingInfo=PaginationInfo(
            numberOfPages=number_of_pages,
            page=page,
            maxItemsPerPage=page_size,
            totalNumberOfItems=total_genes,
        ),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_shaping.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/shaping.py tests/test_mcp/test_shaping.py
git commit -m "feat(mcp): gene-grouped median shaping with sort/top_n/headline"
```

---

## Task 3: next_commands builders + schema relax helper

**Files:**
- Create: `gtex_link/mcp/next_commands.py`
- Create: `gtex_link/mcp/schema_relax.py`
- Test: `tests/test_mcp/test_next_commands.py`, `tests/test_mcp/test_schema_relax.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp/test_next_commands.py`:

```python
from __future__ import annotations

from gtex_link.mcp.next_commands import after_gene_search, after_median, cmd


def test_cmd_shape() -> None:
    assert cmd("get_gene_information", gene_id=["UMOD"]) == {
        "tool": "get_gene_information", "arguments": {"gene_id": ["UMOD"]}
    }


def test_after_gene_search_points_at_gene_info_then_median() -> None:
    cmds = after_gene_search(["ENSG00000169344.15"])
    tools = [c["tool"] for c in cmds]
    assert tools == ["get_gene_information", "get_median_expression_levels"]


def test_after_median_points_at_top_expressed_for_top_tissue() -> None:
    cmds = after_median("Kidney_Medulla")
    assert cmds[0]["tool"] == "get_top_expressed_genes_by_tissue"
    assert cmds[0]["arguments"]["tissue_site_detail_id"] == "Kidney_Medulla"
```

Create `tests/test_mcp/test_schema_relax.py`:

```python
from __future__ import annotations

from gtex_link.mcp.schema_relax import relax_output_schema


def test_relax_strips_required_and_opens_objects() -> None:
    schema = {
        "type": "object",
        "required": ["headline", "genes"],
        "additionalProperties": False,
        "properties": {"headline": {"type": "string"}},
    }
    relaxed = relax_output_schema(schema)
    assert "required" not in relaxed
    assert relaxed["additionalProperties"] is True
    assert relaxed["properties"]["headline"] == {"type": "string"}
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_next_commands.py tests/test_mcp/test_schema_relax.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `gtex_link/mcp/next_commands.py`**

```python
"""Builders for _meta.next_commands entries: {tool, arguments} (never empty)."""

from __future__ import annotations

from typing import Any


def cmd(tool: str, **arguments: Any) -> dict[str, Any]:
    """One ready-to-call next step."""
    return {"tool": tool, "arguments": arguments}


def after_gene_search(gencode_ids: list[str]) -> list[dict[str, Any]]:
    """After resolving genes: fetch detail, then median expression."""
    return [
        cmd("get_gene_information", gene_id=gencode_ids),
        cmd("get_median_expression_levels", gencode_id=gencode_ids),
    ]


def after_median(top_tissue: str | None) -> list[dict[str, Any]]:
    """After median expression: pivot to what else is expressed in the top tissue."""
    if not top_tissue:
        return []
    return [cmd("get_top_expressed_genes_by_tissue", tissue_site_detail_id=top_tissue)]
```

- [ ] **Step 4: Implement `gtex_link/mcp/schema_relax.py`**

Port from `../gnomad-link/gnomad_link/mcp/schema_relax.py`:

```python
"""Loosen output JSON Schemas so injected envelope keys (success/_meta) pass.

The MCP SDK validates tool responses against the declared output schema. Our
run_mcp_tool injects success/_meta, so strict success schemas would reject the
envelope. Stripping `required` and forcing additionalProperties=True keeps the
schema's discovery value while letting the envelope flow through.
"""

from __future__ import annotations

from typing import Any


def relax_output_schema(schema: Any) -> Any:
    """Deep-copy *schema* with `required` stripped and objects opened."""
    if not isinstance(schema, dict):
        return schema
    relaxed: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "required":
            continue
        if key == "additionalProperties":
            relaxed[key] = True
            continue
        if key == "properties" and isinstance(value, dict):
            relaxed[key] = {k: relax_output_schema(v) for k, v in value.items()}
            continue
        if key == "items":
            relaxed[key] = (
                [relax_output_schema(v) for v in value]
                if isinstance(value, list)
                else relax_output_schema(value)
            )
            continue
        if key in ("$defs", "definitions") and isinstance(value, dict):
            relaxed[key] = {k: relax_output_schema(v) for k, v in value.items()}
            continue
        if key in ("oneOf", "anyOf", "allOf") and isinstance(value, list):
            relaxed[key] = [relax_output_schema(v) for v in value]
            continue
        relaxed[key] = value
    if relaxed.get("type") == "object" and "additionalProperties" not in relaxed:
        relaxed["additionalProperties"] = True
    return relaxed
```

- [ ] **Step 5: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_next_commands.py tests/test_mcp/test_schema_relax.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add gtex_link/mcp/next_commands.py gtex_link/mcp/schema_relax.py tests/test_mcp/test_next_commands.py tests/test_mcp/test_schema_relax.py
git commit -m "feat(mcp): next_commands builders + output-schema relax helper"
```

---

## Task 4: Rewire the median tool to the grouped shape

**Files:**
- Modify: `gtex_link/mcp/tools/expression.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write failing tests for the new shape + params**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_median_returns_gene_grouped_shape_with_next_commands() -> None:
    from gtex_link.models.responses import PaginatedTissueSiteDetailResponse, TissueSiteDetail

    def _t(tid: str, n: int) -> TissueSiteDetail:
        return TissueSiteDetail.model_validate(
            {"tissueSiteDetailId": tid, "colorHex": "0", "colorRgb": "0", "datasetId": "gtex_v8",
             "eGeneCount": None, "expressedGeneCount": 1, "hasEGenes": False, "hasSGenes": False,
             "mappedInHubmap": False, "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
             "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}}, "sGeneCount": None,
             "samplingSite": "x", "tissueSite": "x", "tissueSiteDetail": "x",
             "tissueSiteDetailAbbr": "x", "ontologyId": "UBERON:1", "ontologyIri": "http://x"}
        )

    def _m(tissue: str, value: float) -> MedianGeneExpression:
        return MedianGeneExpression.model_validate(
            {"datasetId": "gtex_v8", "ontologyId": "UBERON:1", "gencodeId": "ENSG00000169344.15",
             "geneSymbol": "UMOD", "median": value, "numSamples": None,
             "tissueSiteDetailId": tissue, "unit": "TPM"}
        )

    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(
            data=[_m("Adipose_Subcutaneous", 0.0), _m("Kidney_Medulla", 2116.02)], pagingInfo=_paging(2)
        )
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[_t("Kidney_Medulla", 4)], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_median_expression_levels",
            {"gencode_id": ["ENSG00000169344.15"], "top_n": 1},
        )

    assert payload["success"] is True
    assert payload["genes"][0]["geneSymbol"] == "UMOD"
    assert payload["genes"][0]["tissues"][0]["tissue"] == "Kidney_Medulla"
    assert payload["genes"][0]["tissues"][0]["n"] == 4
    assert payload["headline"].startswith("UMOD: highest median in Kidney_Medulla")
    nc = payload["_meta"]["next_commands"]
    assert nc[0]["tool"] == "get_top_expressed_genes_by_tissue"
    assert nc[0]["arguments"]["tissue_site_detail_id"] == "Kidney_Medulla"
```

Update the two pre-existing median tests (`..._omits_tissue_when_none`, `..._passes_tissue_when_given`) to assert against the grouped shape: they should now read `payload["genes"]` (the request-introspection assertions on `mock_service.get_median_gene_expression.call_args` stay valid). For `..._omits_tissue_when_none` change `payload["data"][0]["median"]` to `payload["genes"][0]["tissues"][0]["median"] == 12.5436` and ensure its mock sets `get_tissue_site_details` to an empty response.

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "median" -v`
Expected: FAIL — tool still returns flat `data[]`, no `genes`/`headline`/`next_commands`.

- [ ] **Step 3: Rewrite the median tool**

In `gtex_link/mcp/tools/expression.py`, add imports:

```python
from typing import Literal
from gtex_link.mcp.next_commands import after_median
from gtex_link.mcp.schema_relax import relax_output_schema
from gtex_link.mcp.shaping import group_median
from gtex_link.models.mcp_results import MedianExpressionResult
```

Replace the median tool decorator + function with:

```python
        @mcp.tool(
            name="get_median_expression_levels",
            title="Get Median Expression Levels",
            annotations=READ_ONLY_OPEN_WORLD,
            tags={"expression"},
            output_schema=relax_output_schema(MedianExpressionResult.model_json_schema(by_alias=True)),
            description=(
                "Get median GTEx Portal expression (TPM) per tissue for one or "
                "more genes (GENCODE IDs or symbols; symbols are auto-resolved). "
                "Results are grouped per gene with invariant fields hoisted. Use "
                "`sort` + `top_n` to answer 'where is this expressed most?' in one "
                "call; `response_mode='full'` adds ontologyId; `include_spread=true` "
                "adds per-tissue min/max/quartiles/IQR (one extra upstream call)."
            ),
        )
        async def get_median_expression_levels(
            gencode_id: list[str],
            tissue_site_detail_id: str | None = None,
            dataset_id: str = "gtex_v8",
            sort: Literal["desc", "asc", "none"] = "desc",
            top_n: int | None = None,
            response_mode: Literal["compact", "full"] = "compact",
            include_spread: bool = False,
            page: int = 0,
            page_size: int = 50,
        ) -> dict[str, Any]:
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                resolved = await resolve_gene_ids(service, gencode_id)
                req: dict[str, object] = {
                    "gencodeId": resolved,
                    "datasetId": dataset_id,
                    "page": 0,
                    "itemsPerPage": max(60 * len(resolved), 100),
                }
                if tissue_site_detail_id is not None:
                    req["tissueSiteDetailId"] = tissue_site_detail_id
                result = await service.get_median_gene_expression(
                    MedianGeneExpressionRequest.model_validate(req)
                )
                counts = await sample_count_map(service, dataset_id)

                spread_by_key: dict[tuple[str, str], dict[str, Any] | None] = {}
                if include_spread and result.data:
                    spread_req: dict[str, object] = {
                        "gencodeId": resolved, "datasetId": dataset_id,
                        "page": 0, "itemsPerPage": 1000,
                    }
                    if tissue_site_detail_id is not None:
                        spread_req["tissueSiteDetailId"] = tissue_site_detail_id
                    expr = await service.get_gene_expression(
                        GeneExpressionRequest.model_validate(spread_req)
                    )
                    spread_by_key = {
                        (r.gencode_id, r.tissue_site_detail_id): compute_spread(r.data)
                        for r in expr.data
                    }

                shaped = group_median(
                    list(result.data), counts=counts, sort=sort, top_n=top_n,
                    response_mode=response_mode, spread_by_key=spread_by_key,
                    page=page, page_size=page_size,
                )
                payload = shaped.model_dump(by_alias=True)
                top_tissue = (
                    payload["genes"][0]["tissues"][0]["tissue"]
                    if payload["genes"] and payload["genes"][0]["tissues"]
                    else None
                )
                payload["_meta"] = {"next_commands": after_median(top_tissue)}
                return payload

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
```

> The `_meta.next_commands` set inside `call()` is merged (not overwritten) by `run_mcp_tool`, which adds provenance via `{**existing_meta, **_provenance_meta(ctx)}`.

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "median" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/expression.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): median tool returns grouped result + sort/top_n/response_mode/output_schema"
```

---

## Task 5: Chaining hints on the catalog tools

**Files:**
- Modify: `gtex_link/mcp/tools/reference.py`
- Test: `tests/test_mcp/test_tool_bodies.py`

- [ ] **Step 1: Write a failing test**

Add to `tests/test_mcp/test_tool_bodies.py`:

```python
@pytest.mark.asyncio
async def test_search_gtex_genes_emits_next_commands() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool("search_gtex_genes", {"query": "BRCA1"})

    nc = payload["_meta"]["next_commands"]
    assert nc[0]["tool"] == "get_gene_information"
    assert nc[0]["arguments"]["gene_id"] == ["ENSG00000012048.22"]
```

- [ ] **Step 2: Run to verify failure**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py::test_search_gtex_genes_emits_next_commands -v`
Expected: FAIL — no `next_commands`.

- [ ] **Step 3: Attach `next_commands` in `search_gtex_genes`**

In `gtex_link/mcp/tools/reference.py`, import `from gtex_link.mcp.next_commands import after_gene_search` and change the `search_gtex_genes` `call()` return to add `_meta`:

```python
            async def call() -> dict[str, Any]:
                service = get_gtex_service()
                result = await service.search_genes(
                    query=query, gencode_version=None, genome_build=None,
                    page=page, page_size=page_size,
                )
                payload = result.model_dump(by_alias=True)
                gencode_ids = [g["gencodeId"] for g in payload["data"]]
                if gencode_ids:
                    payload["_meta"] = {"next_commands": after_gene_search(gencode_ids)}
                return payload
```

- [ ] **Step 4: Run to verify pass**

Run: `uv run pytest tests/test_mcp/test_tool_bodies.py -k "search_gtex_genes" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/mcp/tools/reference.py tests/test_mcp/test_tool_bodies.py
git commit -m "feat(mcp): chaining hints on search_gtex_genes"
```

---

## Task 6: Full verification

- [ ] **Step 1:** `make ci-local` — expect PASS (coverage >= 90%).
- [ ] **Step 2:** Live smoke + token check: `get_median_expression_levels(["PKD1","UMOD"])` returns gene-grouped JSON; compare serialized byte size to the pre-PR3 flat shape and confirm a substantial reduction; `top_n=5, sort="desc"` returns 5 tissues/gene; `_meta.next_commands` is directly callable; a 2-gene query never splits a gene across the gene-list page boundary.
- [ ] **Step 3:** Commit fixups.

---

## Self-Review Notes

- **Spec coverage:** gene-grouping + hoisted invariants (Tasks 1-2,4), paginate-by-gene (Task 2 `group_median`), `response_mode` (Task 2,4), `top_n`+`sort` (Task 2,4), `next_commands` (Tasks 3,4,5), `headline` (Task 2,4), `output_schema` via relaxed model schema (Tasks 3-4). `geneSymbolUpper` is absent from the grouped shape (it was a `Gene`-only field, never in median output).
- **Type consistency:** `group_median`, `median_headline`, `MedianExpressionResult`/`GeneMedianGroup`/`TissueMedian`, `cmd`/`after_gene_search`/`after_median`, `relax_output_schema` consistent across tasks. `sort` values `desc|asc|none`; `response_mode` `compact|full`.
- **Pagination semantics:** `page`/`page_size` now index the **gene list**, not flat rows; documented in the tool description. A single gene's tissues are always returned atomically.
