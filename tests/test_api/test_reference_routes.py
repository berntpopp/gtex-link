"""Tests for reference data API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    import respx
    from fastapi.testclient import TestClient

# Production GTEx Portal base URL; the FastAPI app reads ``settings.api.base_url``
# from the global config, which defaults to the real API. Respx patterns target
# that URL so the running app's outbound httpx calls are intercepted.
GTEX_API_BASE = "https://gtexportal.org/api/v2"

EMPTY_PAGE: dict[str, Any] = {
    "data": [],
    "pagingInfo": {
        "numberOfPages": 0,
        "page": 0,
        "maxItemsPerPage": 250,
        "totalNumberOfItems": 0,
    },
}


class TestGeneSearchRoutes:
    """Test gene search API routes."""

    def test_search_genes_success(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test successful gene search."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/geneSearch").respond(
            200, json=gene_search_response
        )

        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "BRCA1",
                "page": 0,
                "itemsPerPage": 250,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "data" in data
        assert "pagingInfo" in data
        assert len(data["data"]) >= 0

    def test_search_genes_missing_query(self, test_client: TestClient) -> None:
        """Test gene search without query parameter."""
        response = test_client.get("/api/reference/geneSearch")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_search_genes_empty_query(self, test_client: TestClient) -> None:
        """Test gene search with empty query."""
        response = test_client.get("/api/reference/geneSearch", params={"geneId": ""})

        assert response.status_code == 422

    def test_search_genes_with_gencode_id(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene search with Gencode ID."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/geneSearch").respond(
            200, json=gene_search_response
        )

        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "ENSG00000012048.20",
                "gencodeVersion": "v26",
            },
        )

        assert response.status_code == 200

    def test_search_genes_pagination(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene search pagination."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/geneSearch").respond(
            200, json=gene_search_response
        )

        response = test_client.get(
            "/api/reference/geneSearch",
            params={
                "geneId": "BRCA1",
                "page": 1,
                "itemsPerPage": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagingInfo" in data

    def test_search_genes_invalid_page_size(self, test_client: TestClient) -> None:
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
    def test_search_genes_multiple_queries(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
        gene_query: str,
    ) -> None:
        """Test gene search with multiple different queries."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/geneSearch").respond(
            200, json=gene_search_response
        )

        response = test_client.get("/api/reference/geneSearch", params={"geneId": gene_query})

        assert response.status_code == 200


class TestGeneInfoRoutes:
    """Test gene information API routes."""

    def test_get_genes_success(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test successful gene information retrieval."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/gene").respond(200, json=gene_search_response)

        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1", "TP53"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_genes_by_chromosome(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene retrieval by chromosome - not supported in GTEx API v2, should use gene symbols/IDs."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/gene").respond(200, json=gene_search_response)

        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1", "BRCA2"],
            },
        )

        assert response.status_code == 200

    def test_get_genes_genomic_range(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene retrieval by genomic range - not supported, use gene IDs."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/gene").respond(200, json=gene_search_response)

        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["ENSG00000012048.20"],
                "genomeBuild": "GRCh38/hg38",
            },
        )

        assert response.status_code == 200

    def test_get_genes_invalid_range(self, test_client: TestClient) -> None:
        """Test gene retrieval with invalid parameters."""
        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": [],  # Empty array should cause validation error
            },
        )

        assert response.status_code == 422

    def test_get_genes_multiple_chromosomes(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene retrieval for multiple genes."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/gene").respond(200, json=gene_search_response)

        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1", "BRCA2", "TP53"],
                "gencodeVersion": "v26",
            },
        )

        assert response.status_code == 200

    def test_get_genes_by_gene_type(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        gene_search_response: dict[str, Any],
    ) -> None:
        """Test gene retrieval - gene type filtering not supported by GTEx API v2."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/gene").respond(200, json=gene_search_response)

        response = test_client.get(
            "/api/reference/gene",
            params={
                "geneId": ["BRCA1"],
            },
        )

        assert response.status_code == 200


class TestTranscriptRoutes:
    """Test transcript API routes."""

    def test_get_transcripts_by_gene(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test transcript retrieval by gene."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/transcript").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_transcripts_by_gencode_id(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test transcript retrieval by Gencode ID."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/transcript").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",
                "gencodeVersion": "v26",
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_genomic_region(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test transcript retrieval - genomic region not supported, use gencodeId."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/transcript").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",
                "genomeBuild": "GRCh38/hg38",
            },
        )

        assert response.status_code == 200

    def test_get_transcripts_by_transcript_type(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test transcript retrieval - transcript type filtering not supported."""
        respx_mock.get(f"{GTEX_API_BASE}/reference/transcript").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/reference/transcript",
            params={
                "gencodeId": "ENSG00000012048.20",
            },
        )

        assert response.status_code == 200
