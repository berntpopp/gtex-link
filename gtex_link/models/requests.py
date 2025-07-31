"""Request models for GTEx Portal API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from pydantic import ValidationInfo

from .gtex import (
    Chromosome,
    DatasetId,
    SortBy,
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

    query: str = Field(min_length=1, description="Gene search query")
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


class GeneRequest(BaseRequest):
    """Request for gene endpoint."""

    gencode_id: list[str] | None = Field(
        None,
        alias="geneId",
        description="List of gene IDs (gene symbols, versioned or unversioned GENCODE IDs)",
    )
    gene_symbol: list[str] | None = Field(
        None, alias="geneSymbol", description="List of gene symbols"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )
    chromosome: list[Chromosome] | None = Field(None, description="List of chromosomes")
    start: int | None = Field(None, ge=0, description="Start position")
    end: int | None = Field(None, ge=0, description="End position")
    sort_by: SortBy = Field(default=SortBy.GENE_SYMBOL, alias="sortBy", description="Sort field")
    sort_direction: SortDirection = Field(
        default=SortDirection.ASC, alias="sortDirection", description="Sort direction"
    )


class TranscriptRequest(BaseRequest):
    """Request for transcript endpoint."""

    gencode_id: list[str] | None = Field(None, alias="gencodeId", description="List of Gencode IDs")
    transcript_id: list[str] | None = Field(
        None, alias="transcriptId", description="List of transcript IDs"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )
    chromosome: list[Chromosome] | None = Field(None, description="List of chromosomes")


class MedianGeneExpressionRequest(BaseRequest):
    """Request for median gene expression endpoint."""

    gencode_id: list[str] | None = Field(None, alias="gencodeId", description="List of Gencode IDs")
    gene_symbol: list[str] | None = Field(
        None, alias="geneSymbol", description="List of gene symbols"
    )
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )

    @field_validator("gencode_id", mode="after")
    @classmethod
    def validate_gene_identifiers(
        cls, v: list[str] | None, info: ValidationInfo
    ) -> list[str] | None:
        """Validate that either gencode_id or gene_symbol is provided."""
        gene_symbol = info.data.get("gene_symbol")

        if not v and not gene_symbol:
            raise ValueError("Either gencodeId or geneSymbol must be provided")

        return v


class GeneExpressionRequest(BaseRequest):
    """Request for gene expression endpoint."""

    gencode_id: list[str] = Field(
        alias="gencodeId", description="List of Gencode IDs", min_length=1
    )
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


class VariantRequest(BaseRequest):
    """Request for variant endpoint."""

    variant_id: list[str] | None = Field(None, alias="variantId", description="List of variant IDs")
    chromosome: list[Chromosome] | None = Field(None, description="List of chromosomes")
    start: int | None = Field(None, ge=0, description="Start position")
    end: int | None = Field(None, ge=0, description="End position")
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )
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
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )

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
        alias="tissueSiteDetailId", description="Tissue site detail ID"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


class TissueSiteDetailRequest(BaseRequest):
    """Request for tissue site detail endpoint."""

    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


class SubjectRequest(BaseRequest):
    """Request for subject endpoint."""

    subject_id: list[str] | None = Field(None, alias="subjectId", description="List of subject IDs")
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


class DatasetSampleRequest(BaseRequest):
    """Request for dataset sample endpoint."""

    sample_id: list[str] | None = Field(None, alias="sampleId", description="List of sample IDs")
    subject_id: list[str] | None = Field(None, alias="subjectId", description="List of subject IDs")
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Field(
        None, alias="tissueSiteDetailId", description="List of tissue site detail IDs"
    )
    dataset_id: DatasetId = Field(
        default=DatasetId.GTEX_V8, alias="datasetId", description="Dataset ID"
    )


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
    cls.model_rebuild()
