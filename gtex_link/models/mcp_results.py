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
