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
