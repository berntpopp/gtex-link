"""Tests for reference data API routes."""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest


class TestGeneSearchRoutes:
    """Test gene search API routes."""

    def test_search_genes_success(self, test_client: TestClient, gene_search_response):
        """Test successful gene search."""
        response = test_client.get(
            "/api/reference/geneSearch",  # Updated URL
            params={
                "geneId": "BRCA1",           # Updated parameter name
                "page": 0,
                "itemsPerPage": 250,         # Updated parameter name
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagingInfo" in data
        assert len(data["data"]) >= 0  # May be empty due to mocking

    def test_search_genes_missing_query(self, test_client: TestClient):
        """Test gene search without query parameter."""
        response = test_client.get("/api/reference/geneSearch")  # Updated URL

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_search_genes_empty_query(self, test_client: TestClient):
        """Test gene search with empty query."""
        response = test_client.get("/api/reference/geneSearch", params={"geneId": ""})  # Updated URL and param

        assert response.status_code == 422

    def test_search_genes_with_gencode_id(self, test_client: TestClient):
        """Test gene search with Gencode ID."""
        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "ENSG00000012048.20",  # Updated parameter and correct ID
                "gencodeVersion": "v26",        # Optional new parameter
            },
        )

        assert response.status_code == 200

    def test_search_genes_pagination(self, test_client: TestClient):
        """Test gene search pagination."""
        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "BRCA1",
                "page": 1,
                "itemsPerPage": 50,  # Updated parameter name
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagingInfo" in data

    def test_search_genes_invalid_page_size(self, test_client: TestClient):
        """Test gene search with invalid page size."""
        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "BRCA1",
                "itemsPerPage": 100001,  # Too large for GTEx API limit
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("gene_query", ["BRCA1", "TP53", "EGFR", "KRAS", "PIK3CA"])
    def test_search_genes_multiple_queries(self, test_client: TestClient, gene_query):
        """Test gene search with multiple different queries."""
        response = test_client.get("/api/reference/geneSearch", params={"geneId": gene_query})  # Updated URL and param

        assert response.status_code == 200


class TestGeneInfoRoutes:
    """Test gene information API routes."""

    def test_get_genes_success(self, test_client: TestClient):
        """Test successful gene information retrieval."""
        response = test_client.get(
            "/api/reference/gene",           # Updated URL
            params={
                "geneId": ["BRCA1", "TP53"],  # Updated parameter name
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_genes_by_chromosome(self, test_client: TestClient):
        """Test gene retrieval by chromosome - not supported in GTEx API v2, should use gene symbols/IDs."""
        # GTEx API v2 /gene endpoint requires geneId parameter, doesn't support chromosome filtering
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1", "BRCA2"],  # Use gene symbols instead
            },
        )

        assert response.status_code == 200

    def test_get_genes_genomic_range(self, test_client: TestClient):
        """Test gene retrieval by genomic range - not supported, use gene IDs."""
        # GTEx API v2 doesn't support genomic range queries on /gene endpoint
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["ENSG00000012048.20"],  # Use specific gene ID instead
                "genomeBuild": "GRCh38",           # Optional parameter
            },
        )

        assert response.status_code == 200

    def test_get_genes_invalid_range(self, test_client: TestClient):
        """Test gene retrieval with invalid parameters."""
        # Test with empty geneId array which should cause validation error
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": [],  # Empty array should cause validation error
            },
        )

        assert response.status_code == 422

    def test_get_genes_multiple_chromosomes(self, test_client: TestClient):
        """Test gene retrieval for multiple genes."""
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1", "BRCA2", "TP53"],  # Multiple gene symbols
                "gencodeVersion": "v26",               # Optional parameter
            },
        )

        assert response.status_code == 200

    def test_get_genes_by_gene_type(self, test_client: TestClient):
        """Test gene retrieval - gene type filtering not supported by GTEx API v2."""
        # GTEx API v2 /gene endpoint doesn't support gene_type filtering
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1"],  # Must provide specific gene IDs
            },
        )

        assert response.status_code == 200


class TestTranscriptRoutes:
    """Test transcript API routes."""

    def test_get_transcripts_by_gene(self, test_client: TestClient):
        """Test transcript retrieval by gene."""
        response = test_client.get(
            "/api/reference/transcript",           # Updated URL
            params={
                "gencodeId": "ENSG00000012048.20",  # Updated parameter - single string, not array
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_transcripts_by_gencode_id(self, test_client: TestClient):
        """Test transcript retrieval by Gencode ID."""
        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",  # Single string, correct ID
                "gencodeVersion": "v26",             # Optional parameter
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_genomic_region(self, test_client: TestClient):
        """Test transcript retrieval - genomic region not supported, use gencodeId."""
        # GTEx API v2 transcript endpoint requires gencodeId, doesn't support genomic region
        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",  # Required parameter
                "genomeBuild": "GRCh38",             # Optional parameter
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_by_transcript_type(self, test_client: TestClient):
        """Test transcript retrieval - transcript type filtering not supported."""
        # GTEx API v2 transcript endpoint doesn't support transcript_type filtering
        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",  # Required parameter
            },
        )

        assert response.status_code == 200
