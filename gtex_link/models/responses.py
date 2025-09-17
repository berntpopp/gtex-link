"""Response models for GTEx Portal API."""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue
from pydantic_core import core_schema

# Import original enums for runtime validation but use Literal types for schema
from .gtex import (
    Chromosome as _Chromosome,
)
from .gtex import (
    DatasetId as _DatasetId,
)
from .gtex import (
    DonorSex as _DonorSex,
)
from .gtex import (
    GencodeVersion as _GencodeVersion,
)
from .gtex import (
    GenomeBuild as _GenomeBuild,
)
from .gtex import (
    HardyScale as _HardyScale,
)
from .gtex import (
    Sex as _Sex,
)
from .gtex import (
    Strand as _Strand,
)
from .gtex import (
    TissueSiteDetailId as _TissueSiteDetailId,
)

# Define Literal types for MCP compatibility
Chromosome = Literal[
    "chr1",
    "chr2",
    "chr3",
    "chr4",
    "chr5",
    "chr6",
    "chr7",
    "chr8",
    "chr9",
    "chr10",
    "chr11",
    "chr12",
    "chr13",
    "chr14",
    "chr15",
    "chr16",
    "chr17",
    "chr18",
    "chr19",
    "chr20",
    "chr21",
    "chr22",
    "chrX",
    "chrY",
    "chrM",
]

DatasetId = Literal["gtex_v8", "gtex_snrnaseq_pilot", "gtex_v10"]

GencodeVersion = Literal["v19", "v26", "v32", "v43"]

GenomeBuild = Literal["GRCh37", "GRCh38", "GRCh38/hg38"]

Strand = Literal["+", "-"]

Sex = Literal["Male", "Female"]

DonorSex = Literal["M", "F"]

HardyScale = Literal["0", "1", "2", "3", "4"]

TissueSiteDetailId = Literal[
    "",
    "Whole_Blood",
    "Brain_Cortex",
    "Muscle_Skeletal",
    "Liver",
    "Lung",
    "Breast_Mammary_Tissue",
    "Heart_Left_Ventricle",
    "Thyroid",
    "Adipose_Subcutaneous",
    "Skin_Sun_Exposed_Lower_leg",
    "Adipose_Visceral_Omentum",
    "Adrenal_Gland",
    "Artery_Aorta",
    "Artery_Coronary",
    "Artery_Tibial",
    "Bladder",
    "Brain_Amygdala",
    "Brain_Anterior_cingulate_cortex_BA24",
    "Brain_Caudate_basal_ganglia",
    "Brain_Cerebellar_Hemisphere",
    "Brain_Cerebellum",
    "Brain_Frontal_Cortex_BA9",
    "Brain_Hippocampus",
    "Brain_Hypothalamus",
    "Brain_Nucleus_accumbens_basal_ganglia",
    "Brain_Putamen_basal_ganglia",
    "Brain_Spinal_cord_cervical_c-1",
    "Brain_Substantia_nigra",
    "Cells_Cultured_fibroblasts",
    "Cells_EBV-transformed_lymphocytes",
    "Cervix_Ectocervix",
    "Cervix_Endocervix",
    "Colon_Sigmoid",
    "Colon_Transverse",
    "Esophagus_Gastroesophageal_Junction",
    "Esophagus_Mucosa",
    "Esophagus_Muscularis",
    "Fallopian_Tube",
    "Heart_Atrial_Appendage",
    "Kidney_Cortex",
    "Kidney_Medulla",
    "Minor_Salivary_Gland",
    "Nerve_Tibial",
    "Ovary",
    "Pancreas",
    "Pituitary",
    "Prostate",
    "Skin_Not_Sun_Exposed_Suprapubic",
    "Small_Intestine_Terminal_Ileum",
    "Spleen",
    "Stomach",
    "Testis",
    "Uterus",
    "Vagina",
]

T = TypeVar("T")


class MCPCompatibleJsonSchema(GenerateJsonSchema):
    """Custom JSON schema generator for MCP compatibility.

    This generator ensures that enum schemas are always inlined without
    $ref or $defs references, which is a requirement for MCP compatibility.
    """

    def enum_schema(self, schema: core_schema.EnumSchema) -> JsonSchemaValue:
        """Generate inline enum schema without $ref references."""
        enum_values = [member.value for member in schema["members"]]

        # Return inline enum schema instead of $ref
        result: JsonSchemaValue = {
            "type": "string",
            "enum": enum_values,
        }

        # Add title if available
        if "schema_ref" in schema and schema["schema_ref"]:
            result["title"] = schema["schema_ref"]

        return result


class BaseResponse(BaseModel):
    """Base response model with common configuration."""

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
        json_schema_mode_override="serialization",
    )

    @classmethod
    def model_json_schema(
        cls, by_alias: bool = True, ref_template: str = "#/$defs/{model}"
    ) -> dict[str, Any]:
        """Generate JSON schema using MCP-compatible generator."""
        return super().model_json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=MCPCompatibleJsonSchema,
        )


class PaginationInfo(BaseResponse):
    """Pagination information."""

    number_of_pages: int = Field(alias="numberOfPages")
    page: int
    max_items_per_page: int = Field(alias="maxItemsPerPage")
    total_number_of_items: int = Field(alias="totalNumberOfItems")


class PaginatedResponse(BaseResponse, Generic[T]):
    """Generic paginated response wrapper."""

    data: list[T]
    paging_info: PaginationInfo = Field(alias="pagingInfo")


class Organization(BaseResponse):
    """Information about the organization providing this service."""

    name: str
    url: str


class ServiceInfo(BaseResponse):
    """Service information response."""

    id: str
    name: str
    version: str
    organization: Organization
    description: str | None = None
    contact_url: str | None = Field(None, alias="contactUrl")
    documentation_url: str | None = Field(None, alias="documentationUrl")
    environment: str | None = None


class ErrorResponse(BaseResponse):
    """Response model for API errors."""

    error: str = Field(
        ...,
        description="Error type",
        json_schema_extra={"example": "ValidationError"},
    )
    message: str = Field(
        ...,
        description="Error message",
        json_schema_extra={"example": "Invalid gene identifier"},
    )
    status_code: int | None = Field(
        None,
        description="HTTP status code",
        json_schema_extra={"example": 400},
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Additional error details",
        json_schema_extra={"example": {"field": "gencodeId", "value": ""}},
    )


class Gene(BaseResponse):
    """Gene information."""

    chromosome: Chromosome
    data_source: str = Field(alias="dataSource")
    description: str | None = None
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


class Transcript(BaseResponse):
    """Transcript information."""

    start: int
    end: int
    feature_type: str = Field(alias="featureType")
    genome_build: str = Field(alias="genomeBuild")
    transcript_id: str = Field(alias="transcriptId")
    source: str
    chromosome: str
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    gencode_version: str = Field(alias="gencodeVersion")
    strand: str


class Exon(BaseResponse):
    """Exon information."""

    chromosome: Chromosome
    end: int
    exon_id: str = Field(alias="exonId")
    exon_number: int = Field(alias="exonNumber")
    gencode_version: GencodeVersion = Field(alias="gencodeVersion")
    genome_build: GenomeBuild = Field(alias="genomeBuild")
    start: int
    strand: Strand
    transcript_id: str = Field(alias="transcriptId")


class SampleSummary(BaseResponse):
    """Sample summary statistics."""

    total_count: int = Field(alias="totalCount")
    female: dict[str, int | float]
    male: dict[str, int | float]


class TissueSiteDetail(BaseResponse):
    """Tissue site detail information."""

    tissue_site_detail_id: str = Field(alias="tissueSiteDetailId")
    color_hex: str = Field(alias="colorHex")
    color_rgb: str = Field(alias="colorRgb")
    dataset_id: str = Field(alias="datasetId")
    e_gene_count: int | None = Field(alias="eGeneCount")
    expressed_gene_count: int = Field(alias="expressedGeneCount")
    has_e_genes: bool = Field(alias="hasEGenes")
    has_s_genes: bool = Field(alias="hasSGenes")
    mapped_in_hubmap: bool = Field(alias="mappedInHubmap")
    eqtl_sample_summary: SampleSummary = Field(alias="eqtlSampleSummary")
    rna_seq_sample_summary: SampleSummary = Field(alias="rnaSeqSampleSummary")
    s_gene_count: int | None = Field(alias="sGeneCount")
    sampling_site: str = Field(alias="samplingSite")
    tissue_site: str = Field(alias="tissueSite")
    tissue_site_detail: str = Field(alias="tissueSiteDetail")
    tissue_site_detail_abbr: str = Field(alias="tissueSiteDetailAbbr")
    ontology_id: str = Field(alias="ontologyId")
    ontology_iri: str = Field(alias="ontologyIri")


class Subject(BaseResponse):
    """Subject information."""

    age_bracket: str = Field(alias="ageBracket")
    bmi: float | None = None
    death_classification: int = Field(alias="deathClassification")
    hardy_scale: HardyScale = Field(alias="hardyScale")
    sex: DonorSex
    subject_id: str = Field(alias="subjectId")


class DatasetSample(BaseResponse):
    """Dataset sample information."""

    dataset_id: DatasetId = Field(alias="datasetId")
    hardy_scale: HardyScale | None = Field(alias="hardyScale")
    ischemic_time_group: str | None = Field(alias="ischemicTimeGroup")
    ischemic_time_minutes: int | None = Field(alias="ischemicTimeMinutes")
    pathology_categories: list[str] | None = Field(alias="pathologyCategories")
    pathology_notes: str | None = Field(alias="pathologyNotes")
    rin: float | None = None
    rna_isolation_batch: str | None = Field(alias="rnaIsolationBatch")
    sample_id: str = Field(alias="sampleId")
    sex: Sex
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class Variant(BaseResponse):
    """Variant information."""

    allele_frequency: float | None = Field(alias="alleleFrequency")
    alt: str
    chromosome: Chromosome
    num_alt_per_site: int = Field(alias="numAltPerSite")
    position: int
    ref: str
    rs_id: str | None = Field(alias="rsId")
    variant_id: str = Field(alias="variantId")


class MedianGeneExpression(BaseResponse):
    """Median gene expression data."""

    median: float
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str | None = Field(None, alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    unit: str
    num_samples: int | None = Field(None, alias="numSamples")


class GeneExpression(BaseResponse):
    """Gene expression data."""

    data: list[float]
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    unit: str
    subset_group: str | None = Field(None, alias="subsetGroup")


class TopExpressedGenes(BaseResponse):
    """Top expressed genes data."""

    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    median: float
    unit: str


class SingleNucleusGeneExpressionResult(BaseResponse):
    """Single nucleus gene expression result."""

    cell_type: str = Field(alias="cellType")
    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    log2_cpm: float = Field(alias="log2Cpm")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class SingleNucleusGeneExpressionSummary(BaseResponse):
    """Single nucleus gene expression summary."""

    cell_type: str = Field(alias="cellType")
    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    mean_log2_cpm: float = Field(alias="meanLog2Cpm")
    num_expressed_samples: int = Field(alias="numExpressedSamples")
    num_samples: int = Field(alias="numSamples")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class HealthResponse(BaseResponse):
    """Response model for health check."""

    status: str = Field(
        ...,
        description="Overall health status",
        json_schema_extra={"example": "healthy"},
    )
    version: str = Field(
        ...,
        description="GTEx-Link version",
        json_schema_extra={"example": "0.1.0"},
    )
    gtex_api: str = Field(
        ...,
        description="GTEx Portal API status",
        json_schema_extra={"example": "available"},
    )
    cache: str = Field(
        ...,
        description="Cache system status",
        json_schema_extra={"example": "enabled"},
    )
    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Server uptime in seconds",
        json_schema_extra={"example": 3600.5},
    )


# Type aliases for paginated responses
PaginatedGeneResponse = PaginatedResponse[Gene]
PaginatedTranscriptResponse = PaginatedResponse[Transcript]
PaginatedExonResponse = PaginatedResponse[Exon]
PaginatedTissueSiteDetailResponse = PaginatedResponse[TissueSiteDetail]
PaginatedSubjectResponse = PaginatedResponse[Subject]
PaginatedDatasetSampleResponse = PaginatedResponse[DatasetSample]
PaginatedVariantResponse = PaginatedResponse[Variant]
PaginatedMedianGeneExpressionResponse = PaginatedResponse[MedianGeneExpression]
PaginatedGeneExpressionResponse = PaginatedResponse[GeneExpression]
PaginatedTopExpressedGenesResponse = PaginatedResponse[TopExpressedGenes]
PaginatedSingleNucleusGeneExpressionResultResponse = PaginatedResponse[
    SingleNucleusGeneExpressionResult
]
PaginatedSingleNucleusGeneExpressionSummaryResponse = PaginatedResponse[
    SingleNucleusGeneExpressionSummary
]

# Rebuild all models to resolve forward references
for cls in [
    BaseResponse,
    PaginationInfo,
    PaginatedResponse,
    ServiceInfo,
    ErrorResponse,
    Gene,
    Transcript,
    Exon,
    TissueSiteDetail,
    Subject,
    DatasetSample,
    Variant,
    MedianGeneExpression,
    GeneExpression,
    TopExpressedGenes,
    SingleNucleusGeneExpressionResult,
    SingleNucleusGeneExpressionSummary,
    HealthResponse,
]:
    if hasattr(cls, "model_rebuild"):
        cls.model_rebuild()
