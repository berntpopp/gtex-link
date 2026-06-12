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


def test_gencode_version_for_dataset_maps_known_datasets() -> None:
    from gtex_link.mcp.search_match import gencode_version_for_dataset

    assert gencode_version_for_dataset("gtex_v8") == "v26"
    assert gencode_version_for_dataset("gtex_v10") == "v39"
    # Unknown datasets fall back to the upstream default release.
    assert gencode_version_for_dataset("something_else") == "v26"


@pytest.mark.asyncio
async def test_resolve_gene_ids_resolves_against_dataset_version() -> None:
    # gtex_v10 uses GENCODE v39: a v26 id (.19) must be stripped and re-resolved to
    # the dataset's id (.20), and the upstream query must carry gencodeVersion=v39.
    captured: dict[str, object] = {}

    async def fake_get_genes(request: object) -> PaginatedGeneResponse:
        captured["request"] = request
        return PaginatedGeneResponse(
            data=[_gene("PKD1", "ENSG00000008710.20")],
            pagingInfo=PaginationInfo(
                numberOfPages=1, page=0, maxItemsPerPage=50, totalNumberOfItems=1
            ),
        )

    service = AsyncMock()
    service.get_genes = AsyncMock(side_effect=fake_get_genes)
    resolved = await resolve_gene_ids(service, ["ENSG00000008710.19"], gencode_version="v39")
    assert resolved == ["ENSG00000008710.20"]
    req = captured["request"]
    assert req.gencode_version == "v39"
    assert req.gene_id == ["ENSG00000008710"]


@pytest.mark.asyncio
async def test_resolve_gene_ids_v26_versioned_passes_through() -> None:
    # The default release keeps the no-API fast path for already-versioned ids.
    service = AsyncMock()
    resolved = await resolve_gene_ids(service, ["ENSG00000169344.15"], gencode_version="v26")
    assert resolved == ["ENSG00000169344.15"]
    service.get_genes.assert_not_awaited()


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


def test_gtex_v10_uses_gencode_v39_regression() -> None:
    """Regression: gtex_v10 must map to GENCODE v39, not v26.

    Before fix (8c48b7c), gencode_version_for_dataset did not exist; all
    datasets silently used the gtex_v8/GENCODE-v26 default, so a PKD1 lookup
    on gtex_v10 returned .19 (v26) instead of .20 (v39) and expression
    queries came back empty.  This test proves the root cause is fixed.
    """
    from gtex_link.models.gtex import gencode_version_for_dataset

    assert gencode_version_for_dataset("gtex_v10") == "v39", (
        "gtex_v10 must resolve genes against GENCODE v39 (not the v8/v26 default)"
    )
