"""Response models for GTEx Portal API."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from .gtex import (
    Chromosome,
    DatasetId,
    DonorSex,
    GencodeVersion,
    GenomeBuild,
    HardyScale,
    Sex,
    Strand,
    TissueSiteDetailId,
)

T = TypeVar("T")


class PaginationInfo(BaseModel):
    """Pagination information."""

    number_of_pages: int = Field(alias="numberOfPages")
    page: int
    max_items_per_page: int = Field(alias="maxItemsPerPage")
    total_number_of_items: int = Field(alias="totalNumberOfItems")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: list[T]
    paging_info: PaginationInfo


class Organization(BaseModel):
    """Information about the organization providing this service."""

    name: str
    url: str


class ServiceInfo(BaseModel):
    """Service information response."""

    id: str
    name: str
    version: str
    organization: Organization
    description: str | None = None
    contact_url: str | None = Field(None, alias="contactUrl")
    documentation_url: str | None = Field(None, alias="documentationUrl")
    environment: str | None = None


class Gene(BaseModel):
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


class Transcript(BaseModel):
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


class Exon(BaseModel):
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


class SampleSummary(BaseModel):
    """Sample summary statistics."""
    
    total_count: int = Field(alias="totalCount")
    female: dict[str, int | float]
    male: dict[str, int | float]


class TissueSiteDetail(BaseModel):
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


class Subject(BaseModel):
    """Subject information."""

    age_bracket: str = Field(alias="ageBracket")
    bmi: float | None = None
    death_classification: int = Field(alias="deathClassification")
    hardy_scale: HardyScale = Field(alias="hardyScale")
    sex: DonorSex
    subject_id: str = Field(alias="subjectId")


class DatasetSample(BaseModel):
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


class Variant(BaseModel):
    """Variant information."""

    allele_frequency: float | None = Field(alias="alleleFrequency")
    alt: str
    chromosome: Chromosome
    num_alt_per_site: int = Field(alias="numAltPerSite")
    position: int
    ref: str
    rs_id: str | None = Field(alias="rsId")
    variant_id: str = Field(alias="variantId")


class MedianGeneExpression(BaseModel):
    """Median gene expression data."""

    median: float
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    unit: str


class GeneExpression(BaseModel):
    """Gene expression data."""

    data: list[float]
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    unit: str
    subset_group: str | None = Field(None, alias="subsetGroup")


class SingleTissueEqtl(BaseModel):
    """Single tissue eQTL data."""

    snp_id: str = Field(alias="snpId")
    pos: int
    snp_id_upper: str = Field(alias="snpIdUpper")
    variant_id: str = Field(alias="variantId")
    gene_symbol: str = Field(alias="geneSymbol")
    p_value: float = Field(alias="pValue")
    gene_symbol_upper: str = Field(alias="geneSymbolUpper")
    dataset_id: str = Field(alias="datasetId")
    tissue_site_detail_id: str = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    chromosome: str
    gencode_id: str = Field(alias="gencodeId")
    nes: float


class SingleTissueSqtl(BaseModel):
    """Single tissue sQTL data."""

    beta: float
    intron_cluster: str = Field(alias="intronCluster")
    maf: float
    nes: float
    phenotype_id: str = Field(alias="phenotypeId")
    pvalue: float = Field(alias="pValue")
    qvalue: float = Field(alias="qValue")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    variant_id: str = Field(alias="variantId")


class TopExpressedGenes(BaseModel):
    """Top expressed genes data."""

    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    ontology_id: str = Field(alias="ontologyId")
    dataset_id: str = Field(alias="datasetId")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    median: float
    unit: str


class EqtlGene(BaseModel):
    """eQTL gene data."""

    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    num_significant_variants: int = Field(alias="numSignificantVariants")
    pvalue_threshold: float = Field(alias="pValueThreshold")
    qvalue: float = Field(alias="qValue")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class SGene(BaseModel):
    """sGene (sQTL gene) data."""

    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    num_significant_variants: int = Field(alias="numSignificantVariants")
    pvalue_threshold: float = Field(alias="pValueThreshold")
    qvalue: float = Field(alias="qValue")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class IndependentEqtl(BaseModel):
    """Independent eQTL data."""

    beta: float
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    log10_pvalue: float = Field(alias="log10PValue")
    maf: float
    pip: float
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    variant_id: str = Field(alias="variantId")


class MetaSoft(BaseModel):
    """MetaSoft analysis data."""

    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    m_value: float = Field(alias="mValue")
    pvalue_fe: float = Field(alias="pValueFe")
    pvalue_re2: float = Field(alias="pValueRe2")
    variant_id: str = Field(alias="variantId")


class FineMapping(BaseModel):
    """Fine mapping data."""

    cs_id: str | None = Field(alias="csId")
    cs_index: int | None = Field(alias="csIndex")
    cs_log10bf: float | None = Field(alias="csLog10bf")
    cs_min_r2: float | None = Field(alias="csMinR2")
    cs_size: int | None = Field(alias="csSize")
    gencode_id: str = Field(alias="gencodeId")
    gene_symbol: str = Field(alias="geneSymbol")
    pip: float
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")
    variant_id: str = Field(alias="variantId")


class SingleNucleusGeneExpressionResult(BaseModel):
    """Single nucleus gene expression result."""

    cell_type: str = Field(alias="cellType")
    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    log2_cpm: float = Field(alias="log2Cpm")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


class SingleNucleusGeneExpressionSummary(BaseModel):
    """Single nucleus gene expression summary."""

    cell_type: str = Field(alias="cellType")
    gene_symbol: str = Field(alias="geneSymbol")
    gencode_id: str = Field(alias="gencodeId")
    mean_log2_cpm: float = Field(alias="meanLog2Cpm")
    num_expressed_samples: int = Field(alias="numExpressedSamples")
    num_samples: int = Field(alias="numSamples")
    tissue_site_detail_id: TissueSiteDetailId = Field(alias="tissueSiteDetailId")


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
PaginatedSingleTissueEqtlResponse = PaginatedResponse[SingleTissueEqtl]
PaginatedSingleTissueSqtlResponse = PaginatedResponse[SingleTissueSqtl]
PaginatedTopExpressedGenesResponse = PaginatedResponse[TopExpressedGenes]
PaginatedEqtlGeneResponse = PaginatedResponse[EqtlGene]
PaginatedSGeneResponse = PaginatedResponse[SGene]
PaginatedIndependentEqtlResponse = PaginatedResponse[IndependentEqtl]
PaginatedMetaSoftResponse = PaginatedResponse[MetaSoft]
PaginatedFineMappingResponse = PaginatedResponse[FineMapping]
PaginatedSingleNucleusGeneExpressionResultResponse = PaginatedResponse[
    SingleNucleusGeneExpressionResult
]
PaginatedSingleNucleusGeneExpressionSummaryResponse = PaginatedResponse[
    SingleNucleusGeneExpressionSummary
]

# Rebuild all models to resolve forward references
for cls in [
    PaginationInfo,
    PaginatedResponse,
    ServiceInfo,
    Gene,
    Transcript,
    Exon,
    TissueSiteDetail,
    Subject,
    DatasetSample,
    Variant,
    MedianGeneExpression,
    GeneExpression,
    SingleTissueEqtl,
    SingleTissueSqtl,
    TopExpressedGenes,
    EqtlGene,
    SGene,
    IndependentEqtl,
    MetaSoft,
    FineMapping,
    SingleNucleusGeneExpressionResult,
    SingleNucleusGeneExpressionSummary,
]:
    cls.model_rebuild()
