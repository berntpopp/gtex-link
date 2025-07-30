"""Comprehensive tests for GTEx models with real-world data."""

from pydantic import ValidationError
import pytest

from gtex_link.models import (
    # Enums
    Chromosome,
    DatasetId,
    DonorSex,
    EqtlGene,
    GencodeVersion,
    # Response models
    Gene,
    GeneRequest,
    # Request models
    GeneSearchRequest,
    GenomeBuild,
    MedianGeneExpression,
    MedianGeneExpressionRequest,
    PaginatedGeneResponse,
    PaginationInfo,
    SingleTissueEqtl,
    SingleTissueEqtlRequest,
    Strand,
    Subject,
    TissueSiteDetail,
    TissueSiteDetailId,
    TopExpressedGenes,
    TopExpressedGenesRequest,
    Variant,
    VariantByLocationRequest,
)


class TestEnumValidationComprehensive:
    """Test enum validation with real GTEx values."""

    def test_chromosome_enum_all_values(self):
        """Test all chromosome enum values."""
        # Autosomes
        for i in range(1, 23):
            chrom = getattr(Chromosome, f"CHR{i}")
            assert chrom == f"chr{i}"

        # Sex chromosomes
        assert Chromosome.CHR_X == "chrX"
        assert Chromosome.CHR_Y == "chrY"
        assert Chromosome.CHR_M == "chrM"

    def test_tissue_site_detail_id_real_tissues(self):
        """Test tissue site detail IDs with real GTEx tissues."""
        real_tissues = [
            TissueSiteDetailId.WHOLE_BLOOD,
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.MUSCLE_SKELETAL,
            TissueSiteDetailId.BRAIN_CORTEX,
            TissueSiteDetailId.LIVER,
            TissueSiteDetailId.LUNG,
            TissueSiteDetailId.HEART_LEFT_VENTRICLE,
            TissueSiteDetailId.THYROID,
        ]

        expected_values = [
            "Whole_Blood",
            "Breast_Mammary_Tissue",
            "Muscle_Skeletal",
            "Brain_Cortex",
            "Liver",
            "Lung",
            "Heart_Left_Ventricle",
            "Thyroid",
        ]

        for tissue, expected in zip(real_tissues, expected_values):
            assert tissue.value == expected

    def test_dataset_id_versions(self):
        """Test dataset ID versions."""
        assert DatasetId.GTEX_V8.value == "gtex_v8"
        assert DatasetId.GTEX_V10.value == "gtex_v10"
        assert DatasetId.GTEX_SNRNASEQ_PILOT.value == "gtex_snrnaseq_pilot"

    def test_gencode_version_values(self):
        """Test Gencode version values."""
        assert GencodeVersion.V19.value == "v19"
        assert GencodeVersion.V26.value == "v26"
        assert GencodeVersion.V32.value == "v32"
        assert GencodeVersion.V43.value == "v43"


class TestRequestModelsWithRealData:
    """Test request models with realistic GTEx parameters."""

    def test_gene_search_request_real_queries(self):
        """Test gene search with real gene queries."""
        real_queries = ["BRCA1", "TP53", "EGFR", "KRAS", "PIK3CA"]

        for query in real_queries:
            request = GeneSearchRequest(
                query=query,
                dataset_id=DatasetId.GTEX_V8,
                page=0,
                items_per_page=250,
            )
            assert request.query == query
            assert request.dataset_id == DatasetId.GTEX_V8

    def test_gene_search_request_gencode_ids(self):
        """Test gene search with Gencode IDs."""
        gencode_ids = [
            "ENSG00000012048.22",  # BRCA1
            "ENSG00000141510.17",  # TP53
            "ENSG00000146648.24",  # EGFR
        ]

        for gencode_id in gencode_ids:
            request = GeneSearchRequest(query=gencode_id)
            assert request.query == gencode_id

    def test_gene_request_multiple_filters(self):
        """Test gene request with multiple filters."""
        request = GeneRequest(
            geneSymbol=["BRCA1", "BRCA2", "TP53"],
            chromosome=[Chromosome.CHR17, Chromosome.CHR13, Chromosome.CHR17],
            start=40000000,
            end=50000000,
            datasetId=DatasetId.GTEX_V8,
        )

        assert len(request.gene_symbol) == 3
        assert len(request.chromosome) == 3
        assert request.start == 40000000
        assert request.end == 50000000

    def test_median_expression_request_tissue_filtering(self):
        """Test median expression request with tissue filtering."""
        tissues = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.WHOLE_BLOOD,
            TissueSiteDetailId.BRAIN_CORTEX,
        ]

        request = MedianGeneExpressionRequest(
            gene_symbol=["BRCA1"],
            tissue_site_detail_id=tissues,
            dataset_id=DatasetId.GTEX_V8,
        )

        assert request.gene_symbol == ["BRCA1"]
        assert len(request.tissue_site_detail_id) == 3

    def test_single_tissue_eqtl_request_pvalue_threshold(self):
        """Test eQTL request with p-value threshold."""
        request = SingleTissueEqtlRequest(
            gene_symbol=["BRCA1"],
            tissue_site_detail_id=[TissueSiteDetailId.BREAST_MAMMARY_TISSUE],
            pvalue_threshold=1e-5,
            dataset_id=DatasetId.GTEX_V8,
        )

        assert request.pvalue_threshold == 1e-5
        assert request.gene_symbol == ["BRCA1"]

    def test_variant_by_location_request_real_regions(self):
        """Test variant by location with real genomic regions."""
        # BRCA1 locus
        request = VariantByLocationRequest(
            chromosome=Chromosome.CHR17,
            start=43044295,
            end=43125364,
            dataset_id=DatasetId.GTEX_V8,
        )

        assert request.chromosome == Chromosome.CHR17
        assert request.start == 43044295
        assert request.end == 43125364

    def test_top_expressed_genes_request_all_tissues(self, tissue_id):
        """Test top expressed genes for different tissues."""
        request = TopExpressedGenesRequest(
            tissue_site_detail_id=getattr(TissueSiteDetailId, tissue_id.upper()),
            dataset_id=DatasetId.GTEX_V8,
        )

        assert request.tissue_site_detail_id.value == tissue_id

    def test_pagination_edge_cases(self):
        """Test pagination with edge cases."""
        # Maximum items per page
        request = GeneRequest(items_per_page=1000)
        assert request.items_per_page == 1000

        # Large page number
        request = GeneRequest(page=999)
        assert request.page == 999

    def test_request_validation_errors(self):
        """Test request validation errors."""
        # Items per page too large
        with pytest.raises(ValidationError) as exc_info:
            GeneRequest(items_per_page=1001)
        assert "less than or equal to 1000" in str(exc_info.value)

        # Negative page
        with pytest.raises(ValidationError):
            GeneRequest(page=-1)

        # Empty query
        with pytest.raises(ValidationError):
            GeneSearchRequest(query="")

        # Invalid p-value
        with pytest.raises(ValidationError):
            SingleTissueEqtlRequest(pvalue_threshold=1.5)  # > 1.0

        # Invalid genomic range
        with pytest.raises(ValidationError):
            VariantByLocationRequest(
                chromosome=Chromosome.CHR17,
                start=50000000,
                end=40000000,  # end < start
            )


class TestResponseModelsWithRealData:
    """Test response models with real GTEx data."""

    def test_gene_model_brca1(self, sample_gene_data):
        """Test Gene model with real BRCA1 data."""
        gene = Gene(**sample_gene_data)

        assert gene.gene_symbol == "BRCA1"
        assert gene.chromosome == Chromosome.CHR17
        assert gene.gencode_id == "ENSG00000012048.22"
        assert gene.description == "BRCA1 DNA repair associated"
        assert gene.gene_type == "protein_coding"
        assert gene.strand == Strand.NEGATIVE
        assert gene.start == 43044295
        assert gene.end == 43125364
        assert gene.start < gene.end
        assert gene.entrez_gene_id == 672

    def test_gene_model_pseudogene(self):
        """Test Gene model with pseudogene data."""
        pseudogene_data = {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated, pseudogene 1",
            "end": 43125509,
            "entrezGeneId": None,  # Pseudogenes may not have Entrez IDs
            "gencodeId": "ENSG00000283441.1",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1P1",
            "geneSymbolUpper": "BRCA1P1",
            "geneType": "processed_pseudogene",
            "genomeBuild": "GRCh38",
            "start": 43125280,
            "strand": "-",
            "tss": 43125509,
        }

        gene = Gene(**pseudogene_data)
        assert gene.gene_symbol == "BRCA1P1"
        assert gene.gene_type == "processed_pseudogene"
        assert gene.entrez_gene_id is None

    def test_median_gene_expression_model(self, sample_expression_data):
        """Test MedianGeneExpression model with real data."""
        expression = MedianGeneExpression(**sample_expression_data)

        assert expression.gene_symbol == "BRCA1"
        assert expression.gencode_id == "ENSG00000012048.22"
        assert expression.tissue_site_detail_id == TissueSiteDetailId.BREAST_MAMMARY_TISSUE
        assert expression.median == 12.5436
        assert expression.num_samples == 183
        assert expression.unit == "TPM"
        assert expression.data_source == "GTEx_v8"

    def test_single_tissue_eqtl_model(self, sample_eqtl_data):
        """Test SingleTissueEqtl model with real data."""
        eqtl = SingleTissueEqtl(**sample_eqtl_data)

        assert eqtl.gene_symbol == "BRCA1"
        assert eqtl.gencode_id == "ENSG00000012048.22"
        assert eqtl.variant_id == "chr17_43051071_T_C_b38"
        assert eqtl.tissue_site_detail_id == TissueSiteDetailId.BREAST_MAMMARY_TISSUE
        assert eqtl.beta == -0.485326
        assert eqtl.pvalue == 1.23e-12
        assert eqtl.qvalue == 2.45e-10
        assert eqtl.maf == 0.295918

    def test_variant_model(self, sample_variant_data):
        """Test Variant model with real data."""
        variant = Variant(**sample_variant_data)

        assert variant.chromosome == Chromosome.CHR17
        assert variant.position == 43051071
        assert variant.ref == "T"
        assert variant.alt == "C"
        assert variant.variant_id == "chr17_43051071_T_C_b38"
        assert variant.rs_id == "rs8176318"
        assert variant.allele_frequency == 0.295918
        assert variant.num_alt_per_site == 1

    def test_tissue_site_detail_model(self, sample_tissue_data):
        """Test TissueSiteDetail model with real data."""
        tissue = TissueSiteDetail(**sample_tissue_data)

        assert tissue.tissue_site_detail_id == TissueSiteDetailId.ADIPOSE_SUBCUTANEOUS
        assert tissue.tissue_site_detail == "Adipose - Subcutaneous"
        assert tissue.tissue_site_detail_abbr == "ADPSBQ"
        assert tissue.color_hex == "#FF6600"
        assert tissue.tissue_site_ontology_id == "UBERON:0002190"

    def test_top_expressed_genes_model(self):
        """Test TopExpressedGenes model with real data."""
        top_gene_data = {
            "gencodeId": "ENSG00000210082.2",
            "geneSymbol": "MT-RNR2",
            "medianTpm": 89543.2,
            "tissueSiteDetailId": "Whole_Blood",
        }

        top_gene = TopExpressedGenes(**top_gene_data)
        assert top_gene.gene_symbol == "MT-RNR2"
        assert top_gene.gencode_id == "ENSG00000210082.2"
        assert top_gene.median_tpm == 89543.2
        assert top_gene.tissue_site_detail_id == TissueSiteDetailId.WHOLE_BLOOD

    def test_egene_model(self):
        """Test EqtlGene (eGene) model with real data."""
        egene_data = {
            "geneSymbol": "BRCA1",
            "gencodeId": "ENSG00000012048.22",
            "numSignificantVariants": 234,
            "pValueThreshold": 1.2e-5,
            "qValue": 0.023,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
        }

        egene = EqtlGene(**egene_data)
        assert egene.gene_symbol == "BRCA1"
        assert egene.num_significant_variants == 234
        assert egene.pvalue_threshold == 1.2e-5
        assert egene.qvalue == 0.023

    def test_subject_model(self):
        """Test Subject model with real data."""
        subject_data = {
            "ageBracket": "60-69",
            "bmi": 28.4,
            "deathClassification": 0,
            "hardyScale": "0",
            "sex": "M",
            "subjectId": "GTEX-1117F",
        }

        subject = Subject(**subject_data)
        assert subject.age_bracket == "60-69"
        assert subject.bmi == 28.4
        assert subject.sex == DonorSex.M
        assert subject.subject_id == "GTEX-1117F"

    def test_paginated_response_model(self, gene_search_response):
        """Test PaginatedResponse model with real data."""
        response = PaginatedGeneResponse(**gene_search_response)

        assert len(response.data) == 2
        assert response.paging_info.total_number_of_items == 2
        assert response.paging_info.page == 0
        assert response.paging_info.max_items_per_page == 250
        assert response.paging_info.number_of_pages == 1

        # Test first gene
        first_gene = response.data[0]
        assert first_gene.gene_symbol == "BRCA1"
        assert first_gene.gene_type == "protein_coding"

    def test_pagination_info_model(self):
        """Test PaginationInfo model."""
        pagination_data = {
            "numberOfPages": 10,
            "page": 5,
            "maxItemsPerPage": 100,
            "totalNumberOfItems": 1000,
        }

        pagination = PaginationInfo(**pagination_data)
        assert pagination.number_of_pages == 10
        assert pagination.page == 5
        assert pagination.max_items_per_page == 100
        assert pagination.total_number_of_items == 1000

    def test_field_aliases_conversion(self):
        """Test field alias conversion from camelCase to snake_case."""
        gene_data = {
            "chromosome": "chr17",
            "dataSource": "GENCODE",  # camelCase
            "gencodeId": "ENSG123",  # camelCase
            "geneSymbol": "TEST",  # camelCase
            "end": 100,
            "gencodeVersion": "v26",  # camelCase
            "geneStatus": "KNOWN",  # camelCase
            "geneSymbolUpper": "TEST",  # camelCase
            "geneType": "protein_coding",  # camelCase
            "genomeBuild": "GRCh38",  # camelCase
            "start": 50,
            "strand": "+",
            "tss": 75,
        }

        gene = Gene(**gene_data)
        # Verify snake_case attributes
        assert gene.data_source == "GENCODE"
        assert gene.gencode_id == "ENSG123"
        assert gene.gene_symbol == "TEST"
        assert gene.gene_status == "KNOWN"
        assert gene.gene_symbol_upper == "TEST"
        assert gene.gene_type == "protein_coding"
        assert gene.genome_build == GenomeBuild.GRCH38


class TestModelEdgeCases:
    """Test model edge cases and boundary conditions."""

    def test_gene_model_optional_fields(self):
        """Test Gene model with optional fields as None."""
        gene_data = {
            "chromosome": "chrX",
            "dataSource": "GENCODE",
            "description": None,  # Optional field
            "end": 154531,
            "entrezGeneId": None,  # Optional field
            "gencodeId": "ENSG00000000003.15",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "TSPAN6",
            "geneSymbolUpper": "TSPAN6",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 100627,
            "strand": "-",
            "tss": 154531,
        }

        gene = Gene(**gene_data)
        assert gene.description is None
        assert gene.entrez_gene_id is None
        assert gene.gene_symbol == "TSPAN6"

    def test_empty_paginated_response(self):
        """Test paginated response with no data."""
        empty_response = {
            "data": [],
            "pagingInfo": {
                "numberOfPages": 0,
                "page": 0,
                "maxItemsPerPage": 250,
                "totalNumberOfItems": 0,
            },
        }

        response = PaginatedGeneResponse(**empty_response)
        assert len(response.data) == 0
        assert response.paging_info.total_number_of_items == 0

    def test_large_numeric_values(self):
        """Test models with large numeric values."""
        large_expression_data = {
            "dataSource": "GTEx_v8",
            "gencodeId": "ENSG00000210082.2",
            "geneSymbol": "MT-RNR2",
            "median": 999999.99,  # Very high expression
            "numSamples": 50000,  # Large sample size
            "tissueSiteDetailId": "Whole_Blood",
            "unit": "TPM",
        }

        expression = MedianGeneExpression(**large_expression_data)
        assert expression.median == 999999.99
        assert expression.num_samples == 50000

    def test_scientific_notation_values(self):
        """Test models with scientific notation values."""
        eqtl_data = {
            "beta": -1.23e-5,
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "maf": 1.5e-4,
            "nes": -1.23e-5,
            "pValue": 1.23e-50,  # Very small p-value
            "qValue": 2.45e-48,  # Very small q-value
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
            "variantId": "chr17_43051071_T_C_b38",
        }

        eqtl = SingleTissueEqtl(**eqtl_data)
        assert eqtl.pvalue == 1.23e-50
        assert eqtl.qvalue == 2.45e-48
        assert eqtl.beta == -1.23e-5
