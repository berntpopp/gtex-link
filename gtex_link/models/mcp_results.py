"""Gene-grouped MCP result models (token-efficient; invariants hoisted)."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from gtex_link.mcp.untrusted_content import UntrustedText
from gtex_link.models.responses import (
    BaseResponse,
    Chromosome,
    GencodeVersion,
    GenomeBuild,
    PaginationInfo,
    Strand,
)


class MCPGene(BaseResponse):
    """Gene information with the upstream GENCODE `description` fenced (v1.1).

    Mirrors `gtex_link.models.responses.Gene` field-for-field except
    `description`, which is a typed `UntrustedText` object (or None) instead of
    a bare string -- this is the MCP-facing shape only; the internal `Gene`
    model (also used by the REST API) is untouched.
    """

    chromosome: Chromosome
    data_source: str = Field(alias="dataSource")
    description: UntrustedText | None = None
    end: int
    entrez_gene_id: int | None = Field(alias="entrezGeneId")
    gencode_id: str = Field(alias="gencodeId")
    gencode_version: GencodeVersion = Field(alias="gencodeVersion")
    gene_status: str = Field(alias="geneStatus")
    gene_symbol: str = Field(alias="geneSymbol")
    gene_symbol_upper: str = Field(alias="geneSymbolUpper")
    gene_type: str = Field(alias="geneType")
    genome_build: GenomeBuild = Field(alias="genomeBuild")
    start: int
    strand: Strand
    tss: int


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
