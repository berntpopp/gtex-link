"""Integration tests for MCP tool bodies.

Each tool is exercised via `mcp.call_tool(...)` with a mocked GTExService so
the closure body, request-model construction, success path, and error path
are all covered.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from gtex_link.exceptions import RateLimitError
from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.models.responses import (
    Gene,
    GeneExpression,
    MedianGeneExpression,
    PaginatedGeneExpressionResponse,
    PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTopExpressedGenesResponse,
    PaginatedTranscriptResponse,
    PaginationInfo,
    TopExpressedGenes,
    Transcript,
)


@contextmanager
def patch_service(mock_service: AsyncMock) -> Iterator[None]:
    """Patch `get_gtex_service` everywhere it is imported by tool modules."""
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
    """Invoke a tool through the facade and return the parsed JSON payload."""
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    result = await mcp.call_tool(name, arguments)
    return json.loads(result.content[0].text)


def _brca1_gene() -> Gene:
    return Gene.model_validate(
        {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated",
            "end": 43125364,
            "entrezGeneId": 672,
            "gencodeId": "ENSG00000012048.22",
            "gencodeVersion": "v26",
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


def _paging(total: int) -> PaginationInfo:
    return PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=total)


@pytest.mark.asyncio
async def test_search_gtex_genes_happy_path() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool("search_gtex_genes", {"query": "BRCA1"})

    assert payload["data"][0]["geneSymbol"] == "BRCA1"
    assert payload["data"][0]["gencodeId"] == "ENSG00000012048.22"
    mock_service.search_genes.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_gtex_genes_error_path_returns_friendly_message() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(side_effect=RateLimitError("limit"))

    with patch_service(mock_service):
        payload = await _call_tool("search_gtex_genes", {"query": "BRCA1"})

    assert "rate limit" in payload["error"].lower()


@pytest.mark.asyncio
async def test_get_gene_information_happy_path() -> None:
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool("get_gene_information", {"gene_id": ["BRCA1"]})

    assert payload["data"][0]["entrezGeneId"] == 672
    mock_service.get_genes.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_transcript_information_happy_path() -> None:
    transcript = Transcript.model_validate(
        {
            "start": 43044295,
            "end": 43125364,
            "featureType": "transcript",
            "genomeBuild": "GRCh38",
            "transcriptId": "ENST00000357654.7",
            "source": "ENSEMBL",
            "chromosome": "chr17",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "gencodeVersion": "v26",
            "strand": "-",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_transcripts = AsyncMock(
        return_value=PaginatedTranscriptResponse(data=[transcript], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_transcript_information",
            {"gencode_id": "ENSG00000012048.22"},
        )

    assert payload["data"][0]["transcriptId"] == "ENST00000357654.7"
    mock_service.get_transcripts.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_median_expression_levels_omits_tissue_when_none() -> None:
    expr = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:0001911",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 12.5436,
            "numSamples": 183,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
            "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[expr], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_median_expression_levels",
            {"gencode_id": ["ENSG00000012048.22"]},
        )

    assert payload["data"][0]["median"] == 12.5436
    request = mock_service.get_median_gene_expression.call_args.args[0]
    assert request.tissue_site_detail_id == ""


@pytest.mark.asyncio
async def test_get_median_expression_levels_passes_tissue_when_given() -> None:
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        await _call_tool(
            "get_median_expression_levels",
            {
                "gencode_id": ["ENSG00000012048.22"],
                "tissue_site_detail_id": "Whole_Blood",
            },
        )

    request = mock_service.get_median_gene_expression.call_args.args[0]
    assert request.tissue_site_detail_id == "Whole_Blood"


@pytest.mark.asyncio
async def test_get_individual_expression_data_happy_path() -> None:
    expr = GeneExpression.model_validate(
        {
            "data": [1.0, 2.0],
            "datasetId": "gtex_v8",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "subsetGroup": None,
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_gene_expression = AsyncMock(
        return_value=PaginatedGeneExpressionResponse(data=[expr], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_individual_expression_data",
            {
                "gencode_id": ["ENSG00000012048.22"],
                "tissue_site_detail_id": "Whole_Blood",
            },
        )

    assert payload["data"][0]["geneSymbol"] == "BRCA1"
    mock_service.get_gene_expression.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_top_expressed_genes_by_tissue_happy_path() -> None:
    row = TopExpressedGenes.model_validate(
        {
            "datasetId": "gtex_v8",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 12.5436,
            "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_top_expressed_genes = AsyncMock(
        return_value=PaginatedTopExpressedGenesResponse(data=[row], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_top_expressed_genes_by_tissue",
            {"tissue_site_detail_id": "Whole_Blood"},
        )

    assert payload["data"][0]["geneSymbol"] == "BRCA1"
    request = mock_service.get_top_expressed_genes.call_args.args[0]
    assert request.tissue_site_detail_id == "Whole_Blood"
    assert request.filter_mt_gene is True


@pytest.mark.asyncio
async def test_search_tool_returns_chatgpt_shape() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool("search", {"query": "BRCA1"})

    assert payload == {
        "results": [
            {
                "id": "gene:ENSG00000012048.22",
                "title": "BRCA1 - BRCA1 DNA repair associated",
                "url": "https://gtexportal.org/home/gene/BRCA1",
            }
        ]
    }


@pytest.mark.asyncio
async def test_search_tool_returns_empty_on_error() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(side_effect=RuntimeError("upstream down"))

    with patch_service(mock_service):
        payload = await _call_tool("search", {"query": "BRCA1"})

    assert payload == {"results": []}


@pytest.mark.asyncio
async def test_fetch_tool_returns_gene_document() -> None:
    expr = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:0001911",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 12.5436,
            "numSamples": 183,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
            "unit": "TPM",
        }
    )
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[expr], pagingInfo=_paging(1))
    )

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "gene:ENSG00000012048.22"})

    assert payload["id"] == "gene:ENSG00000012048.22"
    assert payload["title"].startswith("BRCA1 - ")
    assert "Gene Symbol: BRCA1" in payload["text"]
    assert "Entrez Gene ID: 672" in payload["text"]
    assert "Breast_Mammary_Tissue" in payload["text"]
    assert payload["metadata"]["entrez_id"] == 672
    assert payload["metadata"]["type"] == "gene"


@pytest.mark.asyncio
async def test_fetch_tool_handles_expression_failure_gracefully() -> None:
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[_brca1_gene()], pagingInfo=_paging(1))
    )
    mock_service.get_median_gene_expression = AsyncMock(side_effect=RuntimeError("boom"))

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "gene:ENSG00000012048.22"})

    assert payload["title"].startswith("BRCA1 - ")
    assert "Expression Data" not in payload["text"]


@pytest.mark.asyncio
async def test_fetch_tool_returns_error_doc_for_unsupported_id() -> None:
    mock_service = AsyncMock()

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "transcript:ENST123"})

    assert payload["metadata"]["type"] == "error"
    assert "Unsupported resource type" in payload["title"]


@pytest.mark.asyncio
async def test_fetch_tool_returns_not_found_when_gene_missing() -> None:
    mock_service = AsyncMock()
    mock_service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        payload = await _call_tool("fetch", {"id": "gene:ENSG99999999.1"})

    assert payload["metadata"]["type"] == "error"
    assert "not found" in payload["title"].lower()
