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
    assert (
        classify_match("ensg00000169344", symbol="UMOD", gencode_id="ENSG00000169344.15")
        == "exact_ensembl_id"
    )
    assert classify_match("umo", symbol="UMOD", gencode_id="ENSG00000169344.15") == "prefix"
    assert classify_match("mod", symbol="UMOD", gencode_id="ENSG00000169344.15") == "substring"


def _gene(symbol: str, gencode: str) -> Gene:
    return Gene.model_validate(
        {
            "chromosome": "chr16",
            "dataSource": "GENCODE",
            "description": "x",
            "end": 2,
            "entrezGeneId": 1,
            "gencodeId": gencode,
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": symbol,
            "geneSymbolUpper": symbol.upper(),
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 1,
            "strand": "-",
            "tss": 2,
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
            pagingInfo=PaginationInfo(
                numberOfPages=1, page=0, maxItemsPerPage=50, totalNumberOfItems=1
            ),
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
            pagingInfo=PaginationInfo(
                numberOfPages=0, page=0, maxItemsPerPage=50, totalNumberOfItems=0
            ),
        )
    )
    with pytest.raises(McpToolError) as excinfo:
        await resolve_gene_ids(service, ["NOTAGENE123"])
    assert excinfo.value.error_code == "invalid_input"
    assert "NOTAGENE123" in excinfo.value.message
