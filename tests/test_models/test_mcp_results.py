"""Tests for gene-grouped MCP result models."""

from __future__ import annotations

from gtex_link.models.mcp_results import GeneMedianGroup, MedianExpressionResult, TissueMedian
from gtex_link.models.responses import PaginationInfo


def test_grouped_result_serializes_camel_case() -> None:
    result = MedianExpressionResult(
        headline="UMOD: highest median in Kidney_Medulla (2116.02 TPM, n=4).",
        genes=[
            GeneMedianGroup(
                gencodeId="ENSG00000169344.15",
                geneSymbol="UMOD",
                datasetId="gtex_v8",
                unit="TPM",
                tissues=[TissueMedian(tissue="Kidney_Medulla", median=2116.02, n=4)],
                tissuesReturned=1,
                tissuesTotal=54,
            )
        ],
        pagingInfo=PaginationInfo(
            numberOfPages=1, page=0, maxItemsPerPage=50, totalNumberOfItems=1
        ),
    )
    dumped = result.model_dump(by_alias=True)
    assert dumped["genes"][0]["gencodeId"] == "ENSG00000169344.15"
    assert dumped["genes"][0]["tissues"][0]["n"] == 4
    assert "headline" in dumped
