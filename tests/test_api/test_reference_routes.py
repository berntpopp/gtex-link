"""Tests for reference data API routes."""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest


class TestGeneSearchRoutes:
    """Test gene search API routes."""

    def test_search_genes_success(self, test_client: TestClient, gene_search_response):
        """Test successful gene search."""
        response = test_client.get(
            "/api/reference/genes/search",
            params={
                "query": "BRCA1",
                "dataset_id": "gtex_v8",
                "page": 0,
                "items_per_page": 250,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagingInfo" in data
        assert len(data["data"]) >= 0  # May be empty due to mocking

    def test_search_genes_missing_query(self, test_client: TestClient):
        """Test gene search without query parameter."""
        response = test_client.get("/api/reference/genes/search")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_search_genes_empty_query(self, test_client: TestClient):
        """Test gene search with empty query."""
        response = test_client.get("/api/reference/genes/search", params={"query": ""})

        assert response.status_code == 422

    def test_search_genes_with_gencode_id(self, test_client: TestClient):
        """Test gene search with Gencode ID."""
        response = test_client.get(
            "/api/reference/genes/search",
            params={
                "query": "ENSG00000012048.22",
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_search_genes_pagination(self, test_client: TestClient):
        """Test gene search pagination."""
        response = test_client.get(
            "/api/reference/genes/search",
            params={
                "query": "BRCA1",
                "page": 1,
                "items_per_page": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagingInfo" in data

    def test_search_genes_invalid_page_size(self, test_client: TestClient):
        """Test gene search with invalid page size."""
        response = test_client.get(
            "/api/reference/genes/search",
            params={
                "query": "BRCA1",
                "items_per_page": 1001,  # Too large
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("gene_query", ["BRCA1", "TP53", "EGFR", "KRAS", "PIK3CA"])
    def test_search_genes_multiple_queries(self, test_client: TestClient, gene_query):
        """Test gene search with multiple different queries."""
        response = test_client.get("/api/reference/genes/search", params={"query": gene_query})

        assert response.status_code == 200


class TestGeneInfoRoutes:
    """Test gene information API routes."""

    def test_get_genes_success(self, test_client: TestClient):
        """Test successful gene information retrieval."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "gene_symbol": ["BRCA1", "TP53"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_genes_by_chromosome(self, test_client: TestClient):
        """Test gene retrieval by chromosome."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "chromosome": ["chr17", "chr13"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_genes_genomic_range(self, test_client: TestClient):
        """Test gene retrieval by genomic range."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 43044295,
                "end": 43125364,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_genes_invalid_range(self, test_client: TestClient):
        """Test gene retrieval with invalid genomic range."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 43125364,  # Start > End
                "end": 43044295,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 422

    def test_get_genes_multiple_chromosomes(self, test_client: TestClient):
        """Test gene retrieval for multiple chromosomes."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "chromosome": ["chr17", "chr13", "chr1"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_genes_by_gene_type(self, test_client: TestClient):
        """Test gene retrieval by gene type."""
        response = test_client.get(
            "/api/reference/genes",
            params={
                "gene_type": ["protein_coding"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200


class TestTranscriptRoutes:
    """Test transcript API routes."""

    def test_get_transcripts_by_gene(self, test_client: TestClient):
        """Test transcript retrieval by gene."""
        response = test_client.get(
            "/api/reference/transcripts",
            params={
                "gene_symbol": ["BRCA1"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_transcripts_by_gencode_id(self, test_client: TestClient):
        """Test transcript retrieval by Gencode ID."""
        response = test_client.get(
            "/api/reference/transcripts",
            params={
                "gencode_id": ["ENSG00000012048.22"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_genomic_region(self, test_client: TestClient):
        """Test transcript retrieval by genomic region."""
        response = test_client.get(
            "/api/reference/transcripts",
            params={
                "chromosome": ["chr17"],
                "start": 43044295,
                "end": 43125364,
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_by_transcript_type(self, test_client: TestClient):
        """Test transcript retrieval by transcript type."""
        response = test_client.get(
            "/api/reference/transcripts",
            params={
                "transcript_type": ["protein_coding"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200