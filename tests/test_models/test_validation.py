"""Test Pydantic model validation."""

from pydantic import ValidationError
import pytest

from gtex_link.models import (
    Chromosome,
    DatasetId,
    Gene,
    GeneRequest,
    GeneSearchRequest,
    MedianGeneExpression,
    PaginatedGeneResponse,
    TissueSiteDetailId,
    VariantByLocationRequest,
)


class TestEnumValidation:
    """Test enum validation."""

    def test_chromosome_enum_valid(self):
        """Test valid chromosome values."""
        # Test that Literal types work correctly
        from typing import get_args

        valid_chromosomes = get_args(Chromosome)
        assert "chr1" in valid_chromosomes
        assert "chrX" in valid_chromosomes
        assert "chrM" in valid_chromosomes

    def test_dataset_id_enum_valid(self):
        """Test valid dataset ID values."""
        from typing import get_args

        valid_datasets = get_args(DatasetId)
        assert "gtex_v8" in valid_datasets
        assert "gtex_v10" in valid_datasets

    def test_tissue_site_detail_id_enum_valid(self):
        """Test valid tissue site detail ID values."""
        from typing import get_args

        valid_tissues = get_args(TissueSiteDetailId)
        assert "Whole_Blood" in valid_tissues
        assert "Brain_Cortex" in valid_tissues


class TestRequestModels:
    """Test request model validation."""

    def test_gene_search_request_valid(self):
        """Test valid gene search request."""
        request = GeneSearchRequest(
            gene_id="BRCA1",  # Updated field name
            page=0,
            items_per_page=250,
        )
        assert request.gene_id == "BRCA1"

    def test_gene_search_request_invalid_query(self):
        """Test invalid gene search request with empty query."""
        with pytest.raises(ValidationError) as exc_info:
            GeneSearchRequest(gene_id="")  # Updated field name

        assert "String should have at least 1 character" in str(exc_info.value)

    def test_gene_request_valid(self):
        """Test valid gene request."""
        request = GeneRequest(
            gene_id=["BRCA1", "TP53"],  # Updated field name
        )
        assert request.gene_id == ["BRCA1", "TP53"]

    def test_variant_by_location_request_valid(self):
        """Test valid variant by location request."""
        request = VariantByLocationRequest(
            chromosome="chr17",
            start=43000000,
            end=44000000,
        )
        assert request.chromosome == "chr17"
        assert request.start == 43000000
        assert request.end == 44000000

    def test_variant_by_location_request_invalid_range(self):
        """Test invalid variant by location request with end <= start."""
        with pytest.raises(ValidationError) as exc_info:
            VariantByLocationRequest(
                chromosome="chr17",
                start=44000000,
                end=43000000,  # end <= start
            )

        assert "End position must be greater than start position" in str(exc_info.value)

    def test_pagination_limits(self):
        """Test pagination parameter limits."""
        # Valid pagination
        request = GeneRequest(gene_id=["BRCA1"], items_per_page=1000)  # Required field
        assert request.items_per_page == 1000

        # Invalid - too large (GTEx API limit is 100000)
        with pytest.raises(ValidationError):
            GeneRequest(gene_id=["BRCA1"], items_per_page=100001)

        # Invalid - too small
        with pytest.raises(ValidationError):
            GeneRequest(gene_id=["BRCA1"], items_per_page=0)

        # Invalid - negative page
        with pytest.raises(ValidationError):
            GeneRequest(gene_id=["BRCA1"], page=-1)


class TestResponseModels:
    """Test response model validation."""

    def test_gene_model_valid(self):
        """Test valid gene model."""
        gene_data = {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated",
            "end": 43125364,
            "entrezGeneId": 672,
            "gencodeId": "ENSG00000012048.22",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1",
            "geneSymbolUpper": "BRCA1",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 43044295,
            "strand": "-",
            "tss": 43125364,
        }

        gene = Gene(**gene_data)
        assert gene.gene_symbol == "BRCA1"
        assert gene.chromosome == "chr17"
        assert gene.start < gene.end

    def test_median_gene_expression_valid(self):
        """Test valid median gene expression model."""
        expression_data = {
            "median": 1.48181,
            "tissueSiteDetailId": "Adipose_Subcutaneous",
            "ontologyId": "UBERON:0002190",
            "datasetId": "gtex_v8",
            "gencodeId": "ENSG00000012048.20",
            "geneSymbol": "BRCA1",
            "unit": "TPM",
        }

        expression = MedianGeneExpression(**expression_data)
        assert expression.gene_symbol == "BRCA1"
        assert expression.median == 1.48181
        assert expression.tissue_site_detail_id == "Adipose_Subcutaneous"

    def test_paginated_response_valid(self):
        """Test valid paginated response."""
        response_data = {
            "data": [
                {
                    "chromosome": "chr17",
                    "dataSource": "HAVANA",
                    "description": "BRCA1, DNA repair associated [Source:HGNC Symbol;Acc:HGNC:1100]",
                    "end": 43170245,
                    "entrezGeneId": 672,
                    "gencodeId": "ENSG00000012048.20",
                    "gencodeVersion": "v26",
                    "geneStatus": "",
                    "geneSymbol": "BRCA1",
                    "geneSymbolUpper": "BRCA1",
                    "geneType": "protein coding",
                    "genomeBuild": "GRCh38/hg38",
                    "start": 43044295,
                    "strand": "-",
                    "tss": 43170245,
                }
            ],
            "paging_info": {
                "numberOfPages": 1,
                "page": 0,
                "maxItemsPerPage": 5,
                "totalNumberOfItems": 1,
            },
        }

        response = PaginatedGeneResponse(**response_data)
        assert len(response.data) == 1
        assert response.data[0].gene_symbol == "BRCA1"
        assert response.paging_info.total_number_of_items == 1

    def test_field_aliases(self):
        """Test that field aliases work correctly."""
        # Test camelCase to snake_case conversion
        gene_data = {
            "chromosome": "chr17",
            "dataSource": "HAVANA",  # Should map to data_source
            "description": "BRCA1, DNA repair associated [Source:HGNC Symbol;Acc:HGNC:1100]",
            "end": 43170245,
            "entrezGeneId": 672,
            "gencodeId": "ENSG00000012048.20",  # Should map to gencode_id
            "gencodeVersion": "v26",
            "geneStatus": "",
            "geneSymbol": "BRCA1",  # Should map to gene_symbol
            "geneSymbolUpper": "BRCA1",
            "geneType": "protein coding",
            "genomeBuild": "GRCh38/hg38",
            "start": 43044295,
            "strand": "-",
            "tss": 43170245,
        }

        gene = Gene(**gene_data)
        assert gene.data_source == "HAVANA"
        assert gene.gencode_id == "ENSG00000012048.20"
        assert gene.gene_symbol == "BRCA1"
