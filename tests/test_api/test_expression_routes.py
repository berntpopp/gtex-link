"""Tests for expression data API routes."""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest


class TestMedianExpressionRoutes:
    """Test median gene expression API routes."""

    def test_get_median_expression_basic(self, test_client: TestClient):
        """Test basic median expression retrieval."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
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
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_multiple_tissues(self, test_client: TestClient):
        """Test median expression across multiple tissues."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": [
                    "Breast_Mammary_Tissue",
                    "Whole_Blood",
                    "Brain_Cortex",
                    "Liver",
                ],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_by_gencode_id(self, test_client: TestClient):
        """Test median expression by Gencode ID."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gencodeId": ["ENSG00000012048.22"],
                "tissueSiteDetailId": ["Breast_Mammary_Tissue"],
                "datasetId": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_all_tissues(self, test_client: TestClient):
        """Test median expression across all tissues."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_with_pagination(self, test_client: TestClient):
        """Test median expression with pagination."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1", "BRCA2", "TP53"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "page": 0,
                "items_per_page": 50,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagingInfo" in data

    def test_get_median_expression_filtering(self, test_client: TestClient):
        """Test median expression with filtering options."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "min_expression": 1.0,
                "sort_by": "median",
                "sort_direction": "desc",
            },
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "tissue_id", ["Whole_Blood", "Breast_Mammary_Tissue", "Brain_Cortex", "Liver", "Lung"]
    )
    def test_get_median_expression_individual_tissues(self, test_client: TestClient, tissue_id):
        """Test median expression for individual tissues."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": [tissue_id],
            },
        )

        assert response.status_code == 200

    def test_get_median_expression_missing_parameters(self, test_client: TestClient):
        """Test median expression with missing required parameters."""
        response = test_client.get("/api/expression/median-gene-expression")

        assert response.status_code == 422

    def test_get_median_expression_invalid_tissue(self, test_client: TestClient):
        """Test median expression with invalid tissue ID."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Invalid_Tissue"],
            },
        )

        # Should return 422 for invalid enum value
        assert response.status_code == 422


class TestTopExpressedGenesRoutes:
    """Test top expressed genes API routes."""

    def test_get_top_expressed_genes_basic(self, test_client: TestClient):
        """Test basic top expressed genes retrieval."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissueSiteDetailId": "Whole_Blood",
                "datasetId": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_top_expressed_genes_with_limit(self, test_client: TestClient):
        """Test top expressed genes with limit."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Breast_Mammary_Tissue",
                "filter_mt_genes": True,
                "sort_by": "median_tpm",
                "sort_direction": "desc",
                "page": 0,
                "items_per_page": 50,
            },
        )

        assert response.status_code == 200

    def test_get_top_expressed_genes_filter_mt(self, test_client: TestClient):
        """Test top expressed genes with mitochondrial gene filtering."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Brain_Cortex",
                "filter_mt_genes": True,
            },
        )

        assert response.status_code == 200

    def test_get_top_expressed_genes_include_mt(self, test_client: TestClient):
        """Test top expressed genes including mitochondrial genes."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Muscle_Skeletal",
                "filter_mt_genes": False,
            },
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "tissue_id",
        [
            "Whole_Blood",
            "Breast_Mammary_Tissue",
            "Brain_Cortex",
            "Liver",
            "Lung",
            "Muscle_Skeletal",
        ],
    )
    def test_get_top_expressed_genes_multiple_tissues(self, test_client: TestClient, tissue_id):
        """Test top expressed genes for multiple tissues."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": tissue_id,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_top_expressed_genes_with_sorting(self, test_client: TestClient):
        """Test top expressed genes with different sorting options."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={
                "tissue_site_detail_id": "Liver",
                "sort_by": "gene_symbol",
                "sort_direction": "asc",
            },
        )

        assert response.status_code == 200

    def test_get_top_expressed_genes_missing_tissue(self, test_client: TestClient):
        """Test top expressed genes without tissue parameter."""
        response = test_client.get("/api/expression/top-expressed-genes")

        assert response.status_code == 422

    def test_get_top_expressed_genes_invalid_tissue(self, test_client: TestClient):
        """Test top expressed genes with invalid tissue."""
        response = test_client.get(
            "/api/expression/top-expressed-genes",
            params={"tissue_site_detail_id": "Invalid_Tissue"},
        )

        assert response.status_code == 422


class TestIndividualExpressionRoutes:
    """Test individual sample expression API routes."""

    def test_get_individual_expression_basic(self, test_client: TestClient):
        """Test basic individual expression retrieval."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_individual_expression_by_subject(self, test_client: TestClient):
        """Test individual expression by subject ID."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "subject_id": ["GTEX-1117F", "GTEX-1128S"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    def test_get_individual_expression_by_sample(self, test_client: TestClient):
        """Test individual expression by sample ID."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "sample_id": ["GTEX-1117F-0226-SM-5GZZ7"],
            },
        )

        assert response.status_code == 200

    def test_get_individual_expression_with_demographics(self, test_client: TestClient):
        """Test individual expression with demographic filters."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "sex": ["F"],
                "age_bracket": ["50-59", "60-69"],
            },
        )

        assert response.status_code == 200

    def test_get_individual_expression_with_pagination(self, test_client: TestClient):
        """Test individual expression with pagination."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "page": 0,
                "items_per_page": 100,
            },
        )

        assert response.status_code == 200

    def test_get_individual_expression_missing_gene(self, test_client: TestClient):
        """Test individual expression without gene parameter."""
        response = test_client.get(
            "/api/expression/gene-expression", params={"tissue_site_detail_id": ["Whole_Blood"]}
        )

        assert response.status_code == 422


class TestExpressionComparisonRoutes:
    """Test expression comparison API routes."""

    def test_compare_expression_across_tissues(self, test_client: TestClient):
        """Test expression comparison across tissues."""
        response = test_client.get(
            "/api/expression/compare",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": [
                    "Breast_Mammary_Tissue",
                    "Ovary",
                    "Whole_Blood",
                ],
                "comparison_type": "tissue",
            },
        )

        assert response.status_code == 200

    def test_compare_expression_across_genes(self, test_client: TestClient):
        """Test expression comparison across genes."""
        response = test_client.get(
            "/api/expression/compare",
            params={
                "gene_symbol": ["BRCA1", "BRCA2", "TP53"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "comparison_type": "gene",
            },
        )

        assert response.status_code == 200

    def test_compare_expression_across_datasets(self, test_client: TestClient):
        """Test expression comparison across datasets."""
        response = test_client.get(
            "/api/expression/compare",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": ["gtex_v8", "gtex_v10"],
                "comparison_type": "dataset",
            },
        )

        assert response.status_code == 200

    def test_compare_expression_statistical_tests(self, test_client: TestClient):
        """Test expression comparison with statistical tests."""
        response = test_client.get(
            "/api/expression/compare",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue", "Ovary"],
                "comparison_type": "tissue",
                "statistical_test": "t_test",
                "include_statistics": True,
            },
        )

        assert response.status_code == 200


class TestAsyncExpressionRoutes:
    """Test expression routes with async client."""

    @pytest.mark.asyncio
    async def test_async_median_expression(self, async_client: AsyncClient):
        """Test async median expression retrieval."""
        response = await async_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_top_genes(self, async_client: AsyncClient):
        """Test async top expressed genes retrieval."""
        response = await async_client.get(
            "/api/expression/top-expressed-genes", params={"tissue_site_detail_id": "Whole_Blood"}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_individual_expression(self, async_client: AsyncClient):
        """Test async individual expression retrieval."""
        response = await async_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_concurrent_expression_requests(self, async_client: AsyncClient):
        """Test concurrent async expression requests."""
        import asyncio

        tasks = [
            async_client.get(
                "/api/expression/median-gene-expression",
                params={
                    "gene_symbol": ["BRCA1"],
                    "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                },
            ),
            async_client.get(
                "/api/expression/top-expressed-genes",
                params={"tissue_site_detail_id": "Whole_Blood"},
            ),
            async_client.get(
                "/api/expression/gene-expression",
                params={"gene_symbol": ["TP53"], "tissue_site_detail_id": ["Brain_Cortex"]},
            ),
        ]

        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200


class TestExpressionRouteErrorHandling:
    """Test error handling in expression routes."""

    def test_median_expression_validation_error(self, test_client: TestClient):
        """Test median expression with validation error."""
        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": [],  # Empty list
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
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "items_per_page": 1001,  # Too large
            },
        )

        assert response.status_code == 422

    def test_expression_comparison_missing_type(self, test_client: TestClient):
        """Test expression comparison without comparison type."""
        response = test_client.get(
            "/api/expression/compare",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue", "Ovary"],
            },
        )

        assert response.status_code == 422


class TestExpressionRoutePerformance:
    """Test performance aspects of expression routes."""

    def test_median_expression_large_gene_list(self, test_client: TestClient):
        """Test median expression with large gene list."""
        large_gene_list = [
            "BRCA1",
            "BRCA2",
            "TP53",
            "EGFR",
            "MYC",
            "KRAS",
            "PIK3CA",
            "PTEN",
            "AKT1",
            "BRAF",
            "CDKN2A",
            "ERBB2",
            "FGFR1",
            "IDH1",
            "MDM2",
            "NRAS",
        ]

        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": large_gene_list,
                "tissue_site_detail_id": ["Whole_Blood"],
            },
        )

        assert response.status_code == 200

    def test_median_expression_many_tissues(self, test_client: TestClient):
        """Test median expression across many tissues."""
        many_tissues = [
            "Whole_Blood",
            "Breast_Mammary_Tissue",
            "Brain_Cortex",
            "Liver",
            "Lung",
            "Muscle_Skeletal",
            "Heart_Left_Ventricle",
            "Thyroid",
            "Pancreas",
            "Kidney_Cortex",
            "Adipose_Subcutaneous",
            "Skin_Sun_Exposed",
        ]

        response = test_client.get(
            "/api/expression/median-gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": many_tissues,
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_individual_expression_large_dataset(self, test_client: TestClient):
        """Test individual expression with large dataset."""
        response = test_client.get(
            "/api/expression/gene-expression",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Whole_Blood"],
                "items_per_page": 1000,
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_concurrent_expression_requests(self, test_client: TestClient):
        """Test concurrent expression requests."""
        import concurrent.futures

        def make_request(params):
            return test_client.get("/api/expression/median-gene-expression", params=params)

        request_params = [
            {"gene_symbol": ["BRCA1"], "tissue_site_detail_id": ["Breast_Mammary_Tissue"]},
            {"gene_symbol": ["TP53"], "tissue_site_detail_id": ["Lung"]},
            {"gene_symbol": ["EGFR"], "tissue_site_detail_id": ["Brain_Cortex"]},
            {"gene_symbol": ["MYC"], "tissue_site_detail_id": ["Liver"]},
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_request, params) for params in request_params]
            responses = [future.result() for future in futures]

        for response in responses:
            assert response.status_code == 200
