"""End-to-end provenance guarantees, driven through the REAL MCP facade.

Unit tests that hand `_provenance_meta` a synthetic `McpErrorContext` prove the
envelope *can* report the right release -- they do NOT prove the tools actually
pass their `dataset_id` into that context. Remove `dataset_id=dataset_id` from a
tool's `McpErrorContext` and those unit tests still pass while the bug is back.
So the provenance contract is pinned here, through `mcp.call_tool`:

  1. every dataset-scoped tool reports the release it was ASKED for;
  2. an unknown dataset_id is rejected BEFORE any upstream call (an unknown
     dataset must never be silently resolved against the default GENCODE
     release -- that is the same defect class as the false release stamp);
  3. exactly which tools carry a provenance `_meta` at all (`fetch` returns the
     flat Apps SDK document shape and carries none), AND that docs/data.md's
     `_meta` table says the same thing -- the table is parsed here and compared
     against live tool behaviour, so the docs genuinely cannot rot.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.metadata import _ALL_TOOLS
from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.models.responses import (
    Gene,
    GeneExpression,
    MedianGeneExpression,
    PaginatedGeneExpressionResponse,
    PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTissueSiteDetailResponse,
    PaginatedTopExpressedGenesResponse,
    PaginatedTranscriptResponse,
    PaginationInfo,
    TopExpressedGenes,
    Transcript,
)

# The v39 (gtex_v10) id for BRCA1; the v26 (gtex_v8) id is ENSG00000012048.22.
BRCA1_V39 = "ENSG00000012048.20"


@contextmanager
def patch_service(mock_service: AsyncMock) -> Iterator[None]:
    targets = [
        "gtex_link.mcp.service_adapters.get_gtex_service",
        "gtex_link.mcp.tools.reference.get_gtex_service",
        "gtex_link.mcp.tools.expression.get_gtex_service",
        "gtex_link.mcp.tools.search_fetch.get_gtex_service",
    ]
    with (
        patch(targets[0], return_value=mock_service),
        patch(targets[1], return_value=mock_service),
        patch(targets[2], return_value=mock_service),
        patch(targets[3], return_value=mock_service),
    ):
        yield


async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    result = await mcp.call_tool(name, arguments)
    return json.loads(result.content[0].text)


def _paging(total: int) -> PaginationInfo:
    return PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=total)


def _v10_service() -> AsyncMock:
    """A service whose every expression route answers with gtex_v10 rows."""
    gene = Gene.model_validate(
        {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated",
            "end": 43125364,
            "entrezGeneId": 672,
            "gencodeId": BRCA1_V39,
            "gencodeVersion": "v39",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1",
            "geneSymbolUpper": "BRCA1",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 43044295,
            "strand": "-",
            "tss": 43125364,
        }
    )
    median = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v10",
            "ontologyId": "UBERON:0000178",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "median": 12.5,
            "numSamples": 183,
            "tissueSiteDetailId": "Whole_Blood",
            "unit": "TPM",
        }
    )
    individual = GeneExpression.model_validate(
        {
            "data": [1.0, 2.0],
            "datasetId": "gtex_v10",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "subsetGroup": None,
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "unit": "TPM",
        }
    )
    top = TopExpressedGenes.model_validate(
        {
            "datasetId": "gtex_v10",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "median": 12.5,
            "unit": "TPM",
        }
    )
    transcript = Transcript.model_validate(
        {
            "start": 43044295,
            "end": 43125364,
            "featureType": "transcript",
            "genomeBuild": "GRCh38",
            "transcriptId": "ENST00000357654.7",
            "source": "ENSEMBL",
            "chromosome": "chr17",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "gencodeVersion": "v39",
            "strand": "-",
        }
    )
    service = AsyncMock()
    service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[gene], pagingInfo=_paging(1))
    )
    service.get_transcripts = AsyncMock(
        return_value=PaginatedTranscriptResponse(data=[transcript], pagingInfo=_paging(1))
    )
    service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[gene], pagingInfo=_paging(1))
    )
    service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[median], pagingInfo=_paging(1))
    )
    service.get_gene_expression = AsyncMock(
        return_value=PaginatedGeneExpressionResponse(data=[individual], pagingInfo=_paging(1))
    )
    service.get_top_expressed_genes = AsyncMock(
        return_value=PaginatedTopExpressedGenesResponse(data=[top], pagingInfo=_paging(1))
    )
    service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
    )
    return service


# Every dataset-scoped tool, with the arguments that reach its happy path.
DATASET_SCOPED: dict[str, dict[str, Any]] = {
    "get_median_expression_levels": {"gencode_id": ["BRCA1"]},
    "get_individual_expression_data": {"gencode_id": ["BRCA1"]},
    "get_top_expressed_genes_by_tissue": {"tissue_site_detail_id": "Whole_Blood"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_dataset_scoped_tool_reports_the_release_it_was_asked_for(tool: str) -> None:
    """The tool must WIRE its dataset_id into the envelope, not just be able to.

    Drop `dataset_id=dataset_id` from this tool's `McpErrorContext` and this test
    fails (verified by reverting it) -- which is the whole point: it pins the
    behaviour, not the implementation.
    """
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, {**DATASET_SCOPED[tool], "dataset_id": "gtex_v10"})

    assert payload["success"] is True, payload
    assert payload["_meta"]["dataset_id"] == "gtex_v10"
    assert payload["_meta"]["gtex_release"] == "gtex_v10"
    assert payload["_meta"]["gencode_version"] == "v39"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_dataset_free_default_still_reports_the_server_default(tool: str) -> None:
    """Omitting dataset_id keeps the gtex_v8 / v26 provenance."""
    service = _v10_service()
    with patch_service(service):
        payload = await _call_tool(tool, DATASET_SCOPED[tool])

    assert payload["success"] is True, payload
    assert payload["_meta"]["gtex_release"] == "gtex_v8"
    assert payload["_meta"]["gencode_version"] == "v26"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_unknown_dataset_id_is_rejected_before_any_upstream_call(tool: str) -> None:
    """An unknown dataset must not be silently treated as the default release.

    `gencode_version_for_dataset` used to default an UNKNOWN dataset to v26, and
    the gene-id resolution ran BEFORE request validation -- so
    `dataset_id="not_a_dataset"` resolved genes against v26 upstream and only
    then failed. Reject unknown datasets at the top of the tool: no upstream call,
    and the caller's dataset_id is never echoed into the error message.
    """
    service = _v10_service()
    with patch_service(service):
        payload = await _call_tool(tool, {**DATASET_SCOPED[tool], "dataset_id": "not_a_dataset"})

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
    assert "not_a_dataset" not in payload["message"]
    assert payload["_meta"]["gtex_release"] == "gtex_v8"  # the default, never the caller's text

    for route in (
        service.get_genes,
        service.get_median_gene_expression,
        service.get_gene_expression,
        service.get_top_expressed_genes,
        service.get_tissue_site_details,
    ):
        route.assert_not_awaited()


# Which tools carry a provenance `_meta` -- and which deliberately do NOT.
# `fetch` returns the flat OpenAI Apps-SDK / deep-research document shape
# ({id, title, text, url, metadata}), which is contractual and has no `_meta`
# slot; `get_server_capabilities` IS the provenance document. Any other tool
# goes through `run_mcp_tool` and therefore carries `_meta`.
PROVENANCE_META_TOOLS = {
    "search",
    "search_genes",
    "get_gene_information",
    "get_transcript_information",
    "get_median_expression_levels",
    "get_individual_expression_data",
    "get_top_expressed_genes_by_tissue",
}
NO_PROVENANCE_META_TOOLS = {"fetch", "get_server_capabilities"}

_MINIMAL_ARGS: dict[str, dict[str, Any]] = {
    "search": {"query": "BRCA1"},
    "fetch": {"id": "gene:ENSG00000012048.22"},
    "search_genes": {"query": "BRCA1"},
    "get_gene_information": {"gene_id": ["BRCA1"]},
    "get_transcript_information": {"gencode_id": "ENSG00000012048.22"},
    "get_server_capabilities": {},
    **DATASET_SCOPED,
}


def test_the_meta_partition_covers_every_registered_tool() -> None:
    """A new tool must be classified, not silently inherit a docs claim."""
    assert set(_ALL_TOOLS) == PROVENANCE_META_TOOLS | NO_PROVENANCE_META_TOOLS
    assert not PROVENANCE_META_TOOLS & NO_PROVENANCE_META_TOOLS
    assert set(_MINIMAL_ARGS) == set(_ALL_TOOLS)


# docs/data.md's "Which tools carry `_meta`" table: | `tool` | yes/no | ... |
DATA_DOC = Path(__file__).resolve().parents[2] / "docs" / "data.md"
_META_ROW_RE = re.compile(r"^\|\s*`(\w+)`\s*\|\s*(yes|no)\s*\|", re.MULTILINE)


def _documented_meta_table() -> dict[str, bool]:
    """Parse the docs table into {tool: carries_meta}."""
    text = DATA_DOC.read_text(encoding="utf-8")
    start = text.index("#### Which tools carry `_meta`")
    end = text.index("\n## ", start)
    return {tool: flag == "yes" for tool, flag in _META_ROW_RE.findall(text[start:end])}


def test_docs_meta_table_is_actually_owned_by_this_test() -> None:
    """The docs table must match the LIVE classification -- not just exist.

    Claiming a fact is machine-checked while nothing checks it is worse than not
    claiming it. `docs/data.md` says this test owns that table, so it must: flip
    `fetch` to `yes` there and this test (plus the live-behaviour test below,
    which the table drives) fails.
    """
    documented = _documented_meta_table()

    assert set(documented) == set(_ALL_TOOLS), (
        "docs/data.md's `_meta` table has drifted from the registered tools: "
        f"doc={sorted(documented)} code={sorted(_ALL_TOOLS)}"
    )
    expected = {tool: tool in PROVENANCE_META_TOOLS for tool in _ALL_TOOLS}
    assert documented == expected, (
        "docs/data.md's `_meta` table disagrees with the live classification: "
        f"doc={documented} code={expected}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(_ALL_TOOLS))
async def test_each_tool_matches_what_the_docs_table_claims(tool: str) -> None:
    """Drive the DOCUMENTED claim against the real MCP facade, tool by tool.

    This closes the loop: the table is compared to what the server actually
    returns, so a wrong `yes`/`no` in docs/data.md fails CI.
    """
    documented_has_meta = _documented_meta_table()[tool]

    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert ("_meta" in payload) is documented_has_meta, (
        f"docs/data.md claims {tool} "
        f"{'has' if documented_has_meta else 'has no'} `_meta`, but the live tool "
        f"{'has one' if '_meta' in payload else 'has none'}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(PROVENANCE_META_TOOLS))
async def test_tool_carries_provenance_meta(tool: str) -> None:
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert "_meta" in payload, f"{tool} must carry a provenance _meta"
    assert payload["_meta"]["gtex_release"] in {"gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"}
    assert payload["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(NO_PROVENANCE_META_TOOLS))
async def test_tool_carries_no_provenance_meta(tool: str) -> None:
    """Pins the honest half of the docs claim: these two carry NO `_meta`.

    Do not "fix" this by bolting `_meta` onto `fetch` -- its flat document shape
    is fixed by the Apps SDK contract. The docs must say so instead.
    """
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert "_meta" not in payload, f"{tool} unexpectedly grew a provenance _meta"
    assert "gtex_release" not in payload.get("metadata", {})
