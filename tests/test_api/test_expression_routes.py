"""Tests for expression API routes."""

from fastapi.testclient import TestClient
import pytest


class TestMedianExpressionRoutes:
    """Test median gene expression API routes."""

    def test_get_median_expression_basic(self, test_client: TestClient):
        """Test basic median expression retrieval."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_median_expression_multiple_genes(self, test_client: TestClient):
        """Test median expression for multiple genes."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1", "BRCA2", "TP53"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_by_gencode_id(self, test_client: TestClient):
        """Test median expression by Gencode ID."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencode_id": ["ENSG00000012048.22"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_missing_parameters(self, test_client: TestClient):
        """Test median expression without required parameters."""
        response = test_client.get("/api/expression/median-gene-expression")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


class TestTopExpressedGenesRoutes:
    """Test top expressed genes API routes."""

    def test_get_top_expressed_genes_basic(self, test_client: TestClient):
        """Test basic top expressed genes retrieval."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Whole_Blood",
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_top_expressed_genes_missing_tissue(self, test_client: TestClient):
        """Test top expressed genes without tissue parameter."""
        response = test_client.get("/api/expression/top-expressed-genes")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_get_top_expressed_genes_invalid_tissue(self, test_client: TestClient):
        """Test top expressed genes with invalid tissue."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Invalid_Tissue",
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 422


class TestIndividualExpressionRoutes:  
    """Test individual gene expression API routes."""

    def test_get_individual_expression_missing_gene(self, test_client: TestClient):
        """Test individual expression without gene parameter."""
        response = test_client.get("/api/expression/gene-expression")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


class TestAsyncExpressionRoutes:
    """Test async expression routes."""

    @pytest.mark.asyncio
    async def test_async_median_expression(self, async_client):
        """Test async median expression retrieval."""
        if async_client is None:
            pytest.skip("Async client not available")

        response = await async_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestExpressionRouteErrorHandling:
    """Test error handling in expression routes."""

    def test_median_expression_validation_error(self, test_client: TestClient):
        """Test median expression with validation error."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": [],  # Empty list should cause validation error
                "tissue_site_detail_id": ["Whole_Blood"],
            },
        )

        assert response.status_code == 422

    def test_top_genes_invalid_sort_field(self, test_client: TestClient):
        """Test top genes with invalid sort field."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Whole_Blood",
                "sort_by": "invalid_field",
            },
        )

        assert response.status_code == 422

    def test_individual_expression_invalid_page_size(self, test_client: TestClient):
        """Test individual expression with invalid page size."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gencode_id": ["ENSG00000012048.22"],
                "page": 0,
                "items_per_page": 1001,  # Too large
            },
        )

        assert response.status_code == 422