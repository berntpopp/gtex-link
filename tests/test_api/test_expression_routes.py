"""Tests for expression API routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    import respx
    from fastapi.testclient import TestClient
    from httpx import AsyncClient

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


class TestMedianExpressionRoutes:
    """Test median gene expression API routes."""

    def test_get_median_expression_basic(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        median_expression_response: dict[str, Any],
    ) -> None:
        """Test basic median expression retrieval."""
        respx_mock.get(f"{GTEX_API_BASE}/expression/medianGeneExpression").respond(
            200, json=median_expression_response
        )

        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": ["ENSG00000012048.20"],
                "tissueSiteDetailId": "Whole_Blood",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_median_expression_multiple_genes(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        median_expression_response: dict[str, Any],
    ) -> None:
        """Test median expression for multiple genes."""
        respx_mock.get(f"{GTEX_API_BASE}/expression/medianGeneExpression").respond(
            200, json=median_expression_response
        )

        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": [
                    "ENSG00000012048.20",
                    "ENSG00000139618.13",
                    "ENSG00000141510.11",
                ],
                "tissueSiteDetailId": "Whole_Blood",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_by_gencode_id(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
        median_expression_response: dict[str, Any],
    ) -> None:
        """Test median expression by Gencode ID."""
        respx_mock.get(f"{GTEX_API_BASE}/expression/medianGeneExpression").respond(
            200, json=median_expression_response
        )

        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": ["ENSG00000012048.20"],
                "tissueSiteDetailId": "Whole_Blood",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_missing_parameters(self, test_client: TestClient) -> None:
        """Test median expression without required parameters."""
        response = test_client.get("/api/expression/median-gene-expression")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


class TestTopExpressedGenesRoutes:
    """Test top expressed genes API routes."""

    def test_get_top_expressed_genes_basic(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test basic top expressed genes retrieval."""
        # ``TOP_EXPRESSED_GENES_RESPONSE`` fixture omits fields required by the
        # response model (ontologyId, datasetId, unit, median). Returning an
        # empty page keeps the response shape valid without inventing data.
        respx_mock.get(f"{GTEX_API_BASE}/expression/topExpressedGene").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissueSiteDetailId": "Whole_Blood",
                "filterMtGene": True,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagingInfo" in data

    def test_get_top_expressed_genes_missing_tissue(self, test_client: TestClient) -> None:
        """Test top expressed genes without tissue parameter."""
        response = test_client.get("/api/expression/top-expressed-genes")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    def test_get_top_expressed_genes_invalid_tissue(self, test_client: TestClient) -> None:
        """Test top expressed genes with invalid tissue."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissueSiteDetailId": "Invalid_Tissue",
            },
        )

        assert response.status_code == 422


class TestIndividualExpressionRoutes:
    """Test individual gene expression API routes."""

    def test_get_individual_expression_missing_gene(self, test_client: TestClient) -> None:
        """Test individual expression without gene parameter."""
        response = test_client.get("/api/expression/gene-expression")

        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data


class TestAsyncExpressionRoutes:
    """Test async expression routes."""

    @pytest.mark.asyncio
    async def test_async_median_expression(
        self,
        async_client: AsyncClient,
        respx_mock: respx.MockRouter,
        median_expression_response: dict[str, Any],
    ) -> None:
        """Test async median expression retrieval."""
        if async_client is None:
            pytest.skip("Async client not available")

        respx_mock.get(f"{GTEX_API_BASE}/expression/medianGeneExpression").respond(
            200, json=median_expression_response
        )

        response = await async_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": ["ENSG00000012048.20"],
                "tissueSiteDetailId": "Whole_Blood",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestExpressionRouteErrorHandling:
    """Test error handling in expression routes."""

    def test_median_expression_validation_error(self, test_client: TestClient) -> None:
        """Test median expression with validation error."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": [],  # Empty list should cause validation error
                "tissueSiteDetailId": "Whole_Blood",
            },
        )

        assert response.status_code == 422

    def test_top_genes_invalid_sort_field(
        self,
        test_client: TestClient,
        respx_mock: respx.MockRouter,
    ) -> None:
        """Test top genes with invalid sort field."""
        respx_mock.get(f"{GTEX_API_BASE}/expression/topExpressedGene").respond(200, json=EMPTY_PAGE)

        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissueSiteDetailId": "Whole_Blood",
                "sort_by": "invalid_field",  # This parameter doesn't exist anymore
            },
        )

        # This should still return 200 since sort_by is ignored
        assert response.status_code == 200

    def test_individual_expression_invalid_page_size(self, test_client: TestClient) -> None:
        """Test individual expression with invalid page size."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gencodeId": ["ENSG00000012048.20"],
                "page": 0,
                "itemsPerPage": 1001,  # Too large - should cause validation error
            },
        )

        assert response.status_code == 422
