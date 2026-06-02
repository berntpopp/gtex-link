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
    PaginatedTissueSiteDetailResponse,
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

    assert payload["success"] is False
    assert payload["error_code"] == "rate_limited"
    assert "rate limit" in payload["message"].lower()


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
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
    )

    with patch_service(mock_service):
        payload = await _call_tool(
            "get_median_expression_levels",
            {"gencode_id": ["ENSG00000012048.22"]},
        )

    assert payload["genes"][0]["tissues"][0]["median"] == 12.5436
    request = mock_service.get_median_gene_expression.call_args.args[0]
    assert request.tissue_site_detail_id == ""


@pytest.mark.asyncio
async def test_get_median_expression_levels_passes_tissue_when_given() -> None:
    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[], pagingInfo=_paging(0))
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
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

    assert payload["results"] == [
        {
            "id": "gene:ENSG00000012048.22",
            "title": "BRCA1 - BRCA1 DNA repair associated",
            "url": "https://gtexportal.org/home/gene/BRCA1",
        }
    ]


@pytest.mark.asyncio
async def test_search_tool_returns_structured_error_on_upstream_failure() -> None:
    mock_service = AsyncMock()
    mock_service.search_genes = AsyncMock(side_effect=RuntimeError("upstream down"))

    with patch_service(mock_service):
        payload = await _call_tool("search", {"query": "BRCA1"})

    assert payload["success"] is False
    assert payload["error_code"] == "internal_error"


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
        payload = await _call_tool("fetch", {"id": "gene:"})

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


@pytest.mark.asyncio
async def test_search_natural_language_query_finds_gene() -> None:
    # The NL query tokenizes to [umod, kidney, expression]; only "umod" resolves.
    umod = Gene.model_validate(
        {
            "chromosome": "chr16",
            "dataSource": "GENCODE",
            "description": "uromodulin",
            "end": 2,
            "entrezGeneId": 7369,
            "gencodeId": "ENSG00000169344.15",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "UMOD",
            "geneSymbolUpper": "UMOD",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 1,
            "strand": "-",
            "tss": 2,
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
                "datasetId": "gtex_v8",
                "ontologyId": "X",
                "gencodeId": "ENSG00000169344.15",
                "geneSymbol": "UMOD",
                "median": value,
                "numSamples": None,
                "tissueSiteDetailId": tissue,
                "unit": "TPM",
            }
        )

    umod = _brca1_gene().model_copy(
        update={"gene_symbol": "UMOD", "gencode_id": "ENSG00000169344.15"}
    )
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
    umod = _brca1_gene().model_copy(
        update={"gene_symbol": "UMOD", "gencode_id": "ENSG00000169344.15"}
    )
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


@pytest.mark.asyncio
async def test_median_populates_num_samples_from_tissue_map() -> None:
    from gtex_link.models.responses import (
        PaginatedTissueSiteDetailResponse,
        TissueSiteDetail,
    )

    def _tissue(tid: str, n: int) -> TissueSiteDetail:
        return TissueSiteDetail.model_validate(
            {
                "tissueSiteDetailId": tid,
                "colorHex": "0",
                "colorRgb": "0",
                "datasetId": "gtex_v8",
                "eGeneCount": None,
                "expressedGeneCount": 1,
                "hasEGenes": False,
                "hasSGenes": False,
                "mappedInHubmap": False,
                "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "sGeneCount": None,
                "samplingSite": "x",
                "tissueSite": "x",
                "tissueSiteDetail": "x",
                "tissueSiteDetailAbbr": "x",
                "ontologyId": "UBERON:1",
                "ontologyIri": "http://x",
            }
        )

    row = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:1",
            "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD",
            "median": 2116.02,
            "numSamples": None,
            "tissueSiteDetailId": "Kidney_Medulla",
            "unit": "TPM",
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

    assert payload["genes"][0]["tissues"][0]["n"] == 4


@pytest.mark.asyncio
async def test_median_include_spread_attaches_distribution() -> None:
    row = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:1",
            "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD",
            "median": 2116.02,
            "numSamples": None,
            "tissueSiteDetailId": "Kidney_Medulla",
            "unit": "TPM",
        }
    )
    expr = GeneExpression.model_validate(
        {
            "data": [1224.0, 1837.0, 2395.0, 3766.0],
            "datasetId": "gtex_v8",
            "tissueSiteDetailId": "Kidney_Medulla",
            "ontologyId": "UBERON:1",
            "subsetGroup": None,
            "gencodeId": "ENSG00000169344.15",
            "geneSymbol": "UMOD",
            "unit": "TPM",
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

    spread = payload["genes"][0]["tissues"][0]["spread"]
    assert spread["min"] == 1224.0 and spread["max"] == 3766.0
    assert spread["iqr"] >= 0


@pytest.mark.asyncio
async def test_median_returns_gene_grouped_shape_with_next_commands() -> None:
    from gtex_link.models.responses import PaginatedTissueSiteDetailResponse, TissueSiteDetail

    def _t(tid: str, n: int) -> TissueSiteDetail:
        return TissueSiteDetail.model_validate(
            {
                "tissueSiteDetailId": tid,
                "colorHex": "0",
                "colorRgb": "0",
                "datasetId": "gtex_v8",
                "eGeneCount": None,
                "expressedGeneCount": 1,
                "hasEGenes": False,
                "hasSGenes": False,
                "mappedInHubmap": False,
                "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}},
                "sGeneCount": None,
                "samplingSite": "x",
                "tissueSite": "x",
                "tissueSiteDetail": "x",
                "tissueSiteDetailAbbr": "x",
                "ontologyId": "UBERON:1",
                "ontologyIri": "http://x",
            }
        )

    def _m(tissue: str, value: float) -> MedianGeneExpression:
        return MedianGeneExpression.model_validate(
            {
                "datasetId": "gtex_v8",
                "ontologyId": "UBERON:1",
                "gencodeId": "ENSG00000169344.15",
                "geneSymbol": "UMOD",
                "median": value,
                "numSamples": None,
                "tissueSiteDetailId": tissue,
                "unit": "TPM",
            }
        )

    mock_service = AsyncMock()
    mock_service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(
            data=[_m("Adipose_Subcutaneous", 0.0), _m("Kidney_Medulla", 2116.02)],
            pagingInfo=_paging(2),
        )
    )
    mock_service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(
            data=[_t("Kidney_Medulla", 4)], pagingInfo=_paging(1)
        )
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
