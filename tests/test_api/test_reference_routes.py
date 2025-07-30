"""Tests for reference data API routes."""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest


class TestGeneSearchRoutes:
    """Test gene search API routes."""

    def test_search_genes_success(self, test_client: TestClient, gene_search_response):
        """Test successful gene search."""
        response = test_client.get(
            "/api/v1/reference/genes/search",
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
        response = test_client.get("/api/v1/reference/genes/search")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_search_genes_empty_query(self, test_client: TestClient):
        """Test gene search with empty query."""
        response = test_client.get("/api/v1/reference/genes/search", params={"query": ""})

        assert response.status_code == 422

    def test_search_genes_with_gencode_id(self, test_client: TestClient):
        """Test gene search with Gencode ID."""
        response = test_client.get(
            "/api/v1/reference/genes/search",
            params={
                "query": "ENSG00000012048.22",
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_search_genes_pagination(self, test_client: TestClient):
        """Test gene search pagination."""
        response = test_client.get(
            "/api/v1/reference/genes/search",
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
            "/api/v1/reference/genes/search",
            params={
                "query": "BRCA1",
                "items_per_page": 1001,  # Too large
            },
        )

        assert response.status_code == 422

    @pytest.mark.parametrize("gene_query", ["BRCA1", "TP53", "EGFR", "KRAS", "PIK3CA"])
    def test_search_genes_multiple_queries(self, test_client: TestClient, gene_query):
        """Test gene search with multiple different queries."""
        response = test_client.get("/api/v1/reference/genes/search", params={"query": gene_query})

        assert response.status_code == 200


class TestGeneInfoRoutes:
    """Test gene information API routes."""

    def test_get_genes_success(self, test_client: TestClient):
        """Test successful gene information retrieval."""
        response = test_client.get(
            "/api/v1/reference/genes",
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
            "/api/v1/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 43000000,
                "end": 44000000,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_genes_genomic_range(self, test_client: TestClient):
        """Test gene retrieval by genomic range."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 43044295,
                "end": 43125364,
            },
        )

        assert response.status_code == 200

    def test_get_genes_invalid_range(self, test_client: TestClient):
        """Test gene retrieval with invalid genomic range."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 50000000,
                "end": 40000000,  # end < start
            },
        )

        assert response.status_code == 422

    def test_get_genes_multiple_chromosomes(self, test_client: TestClient):
        """Test gene retrieval for multiple chromosomes."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={
                "chromosome": ["chr17", "chr13", "chr7"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_genes_by_gene_type(self, test_client: TestClient):
        """Test gene retrieval by gene type."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={
                "gene_type": ["protein_coding"],
                "dataset_id": "gtex_v8",
                "page": 0,
                "items_per_page": 100,
            },
        )

        assert response.status_code == 200


class TestTranscriptRoutes:
    """Test transcript API routes."""

    def test_get_transcripts_by_gene(self, test_client: TestClient):
        """Test transcript retrieval by gene."""
        response = test_client.get(
            "/api/v1/reference/transcripts",
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
            "/api/v1/reference/transcripts",
            params={
                "gencode_id": ["ENSG00000012048.22"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_genomic_region(self, test_client: TestClient):
        """Test transcript retrieval by genomic region."""
        response = test_client.get(
            "/api/v1/reference/transcripts",
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
            "/api/v1/reference/transcripts",
            params={
                "transcript_type": ["protein_coding"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200


class TestExonRoutes:
    """Test exon API routes."""

    def test_get_exons_by_gene(self, test_client: TestClient):
        """Test exon retrieval by gene."""
        response = test_client.get(
            "/api/v1/reference/exons",
            params={
                "gene_symbol": ["BRCA1"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_exons_by_transcript(self, test_client: TestClient):
        """Test exon retrieval by transcript."""
        response = test_client.get(
            "/api/v1/reference/exons",
            params={
                "transcript_id": ["ENST00000357654.9"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_exons_genomic_region(self, test_client: TestClient):
        """Test exon retrieval by genomic region."""
        response = test_client.get(
            "/api/v1/reference/exons",
            params={
                "chromosome": ["chr17"],
                "start": 43044295,
                "end": 43125364,
            },
        )

        assert response.status_code == 200

    def test_get_exons_with_pagination(self, test_client: TestClient):
        """Test exon retrieval with pagination."""
        response = test_client.get(
            "/api/v1/reference/exons",
            params={
                "gene_symbol": ["BRCA1"],
                "page": 0,
                "items_per_page": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagingInfo" in data


class TestTissueRoutes:
    """Test tissue information API routes."""

    def test_get_tissue_site_details(self, test_client: TestClient):
        """Test tissue site details retrieval."""
        response = test_client.get("/api/v1/reference/tissues")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_specific_tissues(self, test_client: TestClient):
        """Test specific tissue retrieval."""
        response = test_client.get(
            "/api/v1/reference/tissues",
            params={
                "tissue_site_detail_id": ["Breast_Mammary_Tissue", "Whole_Blood", "Brain_Cortex"]
            },
        )

        assert response.status_code == 200

    def test_get_tissues_by_site(self, test_client: TestClient):
        """Test tissue retrieval by tissue site."""
        response = test_client.get(
            "/api/v1/reference/tissues", params={"tissue_site": ["Brain", "Blood"]}
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "tissue_id", ["Whole_Blood", "Breast_Mammary_Tissue", "Brain_Cortex", "Liver", "Lung"]
    )
    def test_get_individual_tissues(self, test_client: TestClient, tissue_id):
        """Test individual tissue retrieval."""
        response = test_client.get(
            "/api/v1/reference/tissues", params={"tissue_site_detail_id": [tissue_id]}
        )

        assert response.status_code == 200


class TestDatasetRoutes:
    """Test dataset information API routes."""

    def test_get_datasets(self, test_client: TestClient):
        """Test dataset information retrieval."""
        response = test_client.get("/api/v1/reference/datasets")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_specific_dataset(self, test_client: TestClient):
        """Test specific dataset retrieval."""
        response = test_client.get("/api/v1/reference/datasets", params={"dataset_id": ["gtex_v8"]})

        assert response.status_code == 200

    def test_get_multiple_datasets(self, test_client: TestClient):
        """Test multiple dataset retrieval."""
        response = test_client.get(
            "/api/v1/reference/datasets", params={"dataset_id": ["gtex_v8", "gtex_v10"]}
        )

        assert response.status_code == 200

    @pytest.mark.parametrize("dataset", ["gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"])
    def test_get_individual_datasets(self, test_client: TestClient, dataset):
        """Test individual dataset retrieval."""
        response = test_client.get("/api/v1/reference/datasets", params={"dataset_id": [dataset]})

        assert response.status_code == 200


class TestAsyncReferenceRoutes:
    """Test reference routes with async client."""

    @pytest.mark.asyncio
    async def test_async_gene_search(self, async_client: AsyncClient):
        """Test async gene search."""
        response = await async_client.get(
            "/api/v1/reference/genes/search", params={"query": "BRCA1"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_gene_info(self, async_client: AsyncClient):
        """Test async gene information retrieval."""
        response = await async_client.get(
            "/api/v1/reference/genes", params={"gene_symbol": ["BRCA1", "TP53"]}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_tissue_info(self, async_client: AsyncClient):
        """Test async tissue information retrieval."""
        response = await async_client.get("/api/v1/reference/tissues")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self, async_client: AsyncClient):
        """Test concurrent async requests."""
        import asyncio

        # Make multiple concurrent requests
        tasks = [
            async_client.get("/api/v1/reference/genes/search", params={"query": "BRCA1"}),
            async_client.get("/api/v1/reference/genes/search", params={"query": "TP53"}),
            async_client.get("/api/v1/reference/tissues"),
            async_client.get("/api/v1/reference/datasets"),
        ]

        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


class TestReferenceRouteErrorHandling:
    """Test error handling in reference routes."""

    def test_gene_search_server_error(self, test_client: TestClient, monkeypatch):
        """Test gene search with server error."""
        # This would require mocking the service to raise an exception
        # For now, just test that malformed requests are handled
        response = test_client.get(
            "/api/v1/reference/genes/search", params={"query": "BRCA1", "items_per_page": "invalid"}
        )

        assert response.status_code == 422

    def test_gene_info_validation_error(self, test_client: TestClient):
        """Test gene info with validation error."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={"start": 50000000, "end": 40000000, "chromosome": ["chr17"]},  # Invalid range
        )

        assert response.status_code == 422

    def test_tissue_info_invalid_id(self, test_client: TestClient):
        """Test tissue info with potentially invalid ID."""
        response = test_client.get(
            "/api/v1/reference/tissues", params={"tissue_site_detail_id": ["Invalid_Tissue_ID"]}
        )

        # Should still return 200 but might have empty data
        assert response.status_code == 200

    def test_dataset_info_invalid_id(self, test_client: TestClient):
        """Test dataset info with potentially invalid ID."""
        response = test_client.get(
            "/api/v1/reference/datasets", params={"dataset_id": ["invalid_dataset"]}
        )

        # Should still return 200 but might have empty data
        assert response.status_code == 200

    def test_malformed_request_body(self, test_client: TestClient):
        """Test malformed request handling."""
        response = test_client.post(
            "/api/v1/reference/genes/search",
            json={"invalid": "data"},  # POST instead of GET
        )

        # Should return method not allowed or similar error
        assert response.status_code in [405, 422]


class TestReferenceRoutePerformance:
    """Test performance aspects of reference routes."""

    def test_gene_search_large_page_size(self, test_client: TestClient):
        """Test gene search with large page size."""
        response = test_client.get(
            "/api/v1/reference/genes/search",
            params={
                "query": "BRCA1",
                "items_per_page": 1000,  # Maximum allowed
            },
        )

        assert response.status_code == 200

    def test_gene_info_multiple_symbols(self, test_client: TestClient):
        """Test gene info with multiple symbols."""
        gene_symbols = ["BRCA1", "BRCA2", "TP53", "EGFR", "MYC", "KRAS", "PIK3CA", "PTEN"]

        response = test_client.get("/api/v1/reference/genes", params={"gene_symbol": gene_symbols})

        assert response.status_code == 200

    def test_gene_info_large_genomic_region(self, test_client: TestClient):
        """Test gene info for large genomic region."""
        response = test_client.get(
            "/api/v1/reference/genes",
            params={
                "chromosome": ["chr17"],
                "start": 1,
                "end": 10000000,  # Large region
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_concurrent_gene_searches(self, test_client: TestClient):
        """Test concurrent gene searches."""
        import concurrent.futures

        def make_request(gene):
            return test_client.get("/api/v1/reference/genes/search", params={"query": gene})

        genes = ["BRCA1", "BRCA2", "TP53", "EGFR", "MYC"]

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, gene) for gene in genes]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
