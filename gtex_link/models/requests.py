"""Request models for GTEx Portal API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from pydantic import ValidationInfo

from .gtex import (
    Chromosome,
    DatasetId,
    GencodeVersion,
    GenomeBuild,
    SortDirection,
    TissueSiteDetailId,
    VariantSortBy,
)


class BaseRequest(BaseModel):
    """Base request model with common pagination fields."""

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    page: int = Field(default=0, ge=0, description="Page number (0-based)")
    items_per_page: int = Field(
        default=250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page (1-1000)",
    )


class GeneSearchRequest(BaseRequest):
    """Request for gene search endpoint."""

    gene_id: str = Field(
        alias="geneId",
        min_length=1,
        description="A gene symbol, versioned gencodeId, or unversioned gencodeId",
        examples=["BRCA1", "ENSG00000012048.20", "ENSG00000012048"],
    )
    gencode_version: GencodeVersion | None = Field(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
        examples=["v26", "v32"],
    )
    genome_build: GenomeBuild | None = Field(
        None, alias="genomeBuild", description="Genome build version", examples=["GRCh38", "GRCh37"]
    )


class GeneRequest(BaseRequest):
    """Request for gene endpoint."""

    gene_id: list[str] = Field(
        alias="geneId",
        min_length=1,
        max_length=50,
        description="List of gene symbols, versioned or unversioned GENCODE IDs",
        examples=[["BRCA1", "TP53"], ["ENSG00000012048.20", "ENSG00000141510.11"]],
    )
    gencode_version: GencodeVersion | None = Field(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
        examples=["v26", "v32"],
    )
    genome_build: GenomeBuild | None = Field(
        None, alias="genomeBuild", description="Genome build version", examples=["GRCh38", "GRCh37"]
    )


class TranscriptRequest(BaseRequest):
    """Request for transcript endpoint."""

    gencode_id: str = Field(
        alias="gencodeId",
        description="A versioned GENCODE ID of a gene, e.g. ENSG00000065613.9",
        examples=["ENSG00000012048.20", "ENSG00000141510.11"],
    )
    gencode_version: GencodeVersion | None = Field(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
        examples=["v26", "v32"],
    )
    genome_build: GenomeBuild | None = Field(
        None, alias="genomeBuild", description="Genome build version", examples=["GRCh38", "GRCh37"]
    )


class MedianGeneExpressionRequest(BaseRequest):
    """Request for median gene expression endpoint."""

    gencode_id: list[str] = Field(
        alias="gencodeId",
        description="List of versioned GENCODE IDs (e.g. ENSG00000012048.20)",
        min_length=1,
        max_length=50,
        examples=[["ENSG00000012048.20", "ENSG00000141510.11"]],
    )
    tissue_site_detail_id: TissueSiteDetailId = Field(
        default="",
        alias="tissueSiteDetailId",
        description="Tissue filter. Use 'ALL' (empty) for all tissues, or specific tissue name for single tissue.",
        examples=["", "Whole_Blood", "Brain_Cortex"],
    )
    dataset_id: DatasetId = Field(
        default="gtex_v8",
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
        examples=["gtex_v8"],
    )


class GeneExpressionRequest(BaseRequest):
    """Request for gene expression endpoint."""

    gencode_id: list[str] = Field(
        alias="gencodeId",
        description="List of versioned GENCODE IDs (e.g. ENSG00000012048.20)",
        min_length=1,
        max_length=50,
        examples=[["ENSG00000012048.20"]],
    )
    tissue_site_detail_id: TissueSiteDetailId = Field(
        default="",
        alias="tissueSiteDetailId",
        description="Tissue filter. Use 'ALL' (empty) for all tissues, or specific tissue name for single tissue.",
        examples=["", "Whole_Blood", "Brain_Cortex"],
    )
    attribute_subset: str | None = Field(
        None,
        alias="attributeSubset",
        description="Donor attribute to subset data by",
        examples=["sex", "age"],
    )
    dataset_id: DatasetId = Field(
        default="gtex_v8",
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
        examples=["gtex_v8"],
    )


class VariantRequest(BaseRequest):
    """Request for variant endpoint."""

    variant_id: list[str] | None = Field(None, alias="variantId", description="List of variant IDs")
    chromosome: list[Chromosome] | None = Field(None, description="List of chromosomes")
    start: int | None = Field(None, ge=0, description="Start position")
    end: int | None = Field(None, ge=0, description="End position")
    dataset_id: DatasetId = Field(default="gtex_v8", alias="datasetId", description="Dataset ID")
    sort_by: VariantSortBy = Field(
        default=VariantSortBy.CHROMOSOME, alias="sortBy", description="Sort field"
    )
    sort_direction: SortDirection = Field(
        default=SortDirection.ASC, alias="sortDirection", description="Sort direction"
    )


class VariantByLocationRequest(BaseRequest):
    """Request for variant by location endpoint."""

    chromosome: Chromosome = Field(description="Chromosome")
    start: int = Field(ge=0, description="Start position")
    end: int = Field(ge=0, description="End position")
    dataset_id: DatasetId = Field(default="gtex_v8", alias="datasetId", description="Dataset ID")

    @field_validator("end")
    @classmethod
    def validate_end_after_start(cls, v: int, info: ValidationInfo) -> int:
        """Validate that end position is after start position."""
        if "start" in info.data and v <= info.data["start"]:
            msg = "End position must be greater than start position"
            raise ValueError(msg)
        return v


class TopExpressedGenesRequest(BaseRequest):
    """Request for top expressed genes endpoint."""

    tissue_site_detail_id: TissueSiteDetailId = Field(
        alias="tissueSiteDetailId",
        description="Tissue site detail ID for top gene analysis",
        examples=["Whole_Blood", "Brain_Cortex", "Muscle_Skeletal"],
    )
    filter_mt_gene: bool = Field(
        default=True,
        alias="filterMtGene",
        description="Exclude mitochondrial genes from results",
        examples=[True, False],
    )
    dataset_id: DatasetId = Field(
        default="gtex_v8",
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
        examples=["gtex_v8"],
    )


class TissueSiteDetailRequest(BaseRequest):
    """Request for tissue site detail endpoint."""

    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(default="gtex_v8", alias="datasetId", description="Dataset ID")


class SubjectRequest(BaseRequest):
    """Request for subject endpoint."""

    subject_id: list[str] | None = Field(None, alias="subjectId", description="List of subject IDs")
    dataset_id: DatasetId = Field(default="gtex_v8", alias="datasetId", description="Dataset ID")


class DatasetSampleRequest(BaseRequest):
    """Request for dataset sample endpoint."""

    sample_id: list[str] | None = Field(None, alias="sampleId", description="List of sample IDs")
    subject_id: list[str] | None = Field(None, alias="subjectId", description="List of subject IDs")
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(default="gtex_v8", alias="datasetId", description="Dataset ID")


# Rebuild all models to resolve forward references
for cls in [
    BaseRequest,
    GeneSearchRequest,
    GeneRequest,
    TranscriptRequest,
    VariantByLocationRequest,
    VariantRequest,
    SubjectRequest,
    TissueSiteDetailRequest,
    MedianGeneExpressionRequest,
    GeneExpressionRequest,
    TopExpressedGenesRequest,
    DatasetSampleRequest,
]:
    if hasattr(cls, "model_rebuild"):
        cls.model_rebuild()
