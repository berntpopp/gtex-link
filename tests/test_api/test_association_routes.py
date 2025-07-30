"""Tests for association data API routes (eQTL, sQTL, etc.)."""

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest


class TestEQTLRoutes:
    """Test eQTL (expression quantitative trait loci) API routes."""

    def test_get_single_tissue_eqtl_basic(self, test_client: TestClient):
        """Test basic single tissue eQTL retrieval."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
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

    def test_get_single_tissue_eqtl_with_pvalue_threshold(self, test_client: TestClient):
        """Test single tissue eQTL with p-value threshold."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "pvalue_threshold": 1e-5,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_multiple_genes(self, test_client: TestClient):
        """Test single tissue eQTL for multiple genes."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1", "BRCA2", "TP53"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "pvalue_threshold": 1e-6,
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_by_variant(self, test_client: TestClient):
        """Test single tissue eQTL by variant ID."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "variant_id": ["chr17_43051071_T_C_b38"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_genomic_region(self, test_client: TestClient):
        """Test single tissue eQTL by genomic region."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "chromosome": "chr17",
                "start": 43000000,
                "end": 44000000,
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_with_sorting(self, test_client: TestClient):
        """Test single tissue eQTL with sorting options."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "sort_by": "pvalue",
                "sort_direction": "asc",
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_with_pagination(self, test_client: TestClient):
        """Test single tissue eQTL with pagination."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "page": 0,
                "items_per_page": 100,
            },
        )

        assert response.status_code == 200

    @pytest.mark.parametrize(
        "tissue_id", ["Breast_Mammary_Tissue", "Ovary", "Prostate", "Lung", "Colon_Transverse"]
    )
    def test_get_single_tissue_eqtl_cancer_tissues(self, test_client: TestClient, tissue_id):
        """Test single tissue eQTL for cancer-relevant tissues."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": [tissue_id],
                "pvalue_threshold": 1e-5,
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_eqtl_missing_parameters(self, test_client: TestClient):
        """Test single tissue eQTL with missing parameters."""
        response = test_client.get("/api/v1/association/eqtl/single-tissue")

        assert response.status_code == 422

    def test_get_single_tissue_eqtl_invalid_pvalue(self, test_client: TestClient):
        """Test single tissue eQTL with invalid p-value."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "pvalue_threshold": 1.5,  # Invalid: > 1.0
            },
        )

        assert response.status_code == 422


class TestMultiTissueEQTLRoutes:
    """Test multi-tissue eQTL API routes."""

    def test_get_multi_tissue_eqtl_basic(self, test_client: TestClient):
        """Test basic multi-tissue eQTL retrieval."""
        response = test_client.get(
            "/api/v1/association/eqtl/multi-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_multi_tissue_eqtl_tissue_subset(self, test_client: TestClient):
        """Test multi-tissue eQTL for tissue subset."""
        response = test_client.get(
            "/api/v1/association/eqtl/multi-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": [
                    "Breast_Mammary_Tissue",
                    "Ovary",
                    "Uterus",
                ],
                "meta_analysis_pvalue_threshold": 1e-8,
            },
        )

        assert response.status_code == 200

    def test_get_multi_tissue_eqtl_by_variant(self, test_client: TestClient):
        """Test multi-tissue eQTL by variant."""
        response = test_client.get(
            "/api/v1/association/eqtl/multi-tissue",
            params={
                "variant_id": ["chr17_43051071_T_C_b38"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_multi_tissue_eqtl_min_tissues(self, test_client: TestClient):
        """Test multi-tissue eQTL with minimum tissue requirement."""
        response = test_client.get(
            "/api/v1/association/eqtl/multi-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "min_tissues_with_effect": 3,
                "meta_analysis_pvalue_threshold": 1e-6,
            },
        )

        assert response.status_code == 200


class TestEGenesRoutes:
    """Test eGenes (genes with significant eQTLs) API routes."""

    def test_get_egenes_basic(self, test_client: TestClient):
        """Test basic eGenes retrieval."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_get_egenes_multiple_tissues(self, test_client: TestClient):
        """Test eGenes for multiple tissues."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "tissue_site_detail_id": [
                    "Breast_Mammary_Tissue",
                    "Ovary",
                    "Whole_Blood",
                ],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_egenes_by_gene_symbol(self, test_client: TestClient):
        """Test eGenes by gene symbol."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "gene_symbol": ["BRCA1", "BRCA2", "TP53"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    def test_get_egenes_qvalue_threshold(self, test_client: TestClient):
        """Test eGenes with q-value threshold."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "qvalue_threshold": 0.05,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_egenes_with_sorting(self, test_client: TestClient):
        """Test eGenes with sorting."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "tissue_site_detail_id": ["Whole_Blood"],
                "sort_by": "qvalue",
                "sort_direction": "asc",
                "page": 0,
                "items_per_page": 50,
            },
        )

        assert response.status_code == 200

    def test_get_egenes_missing_tissue(self, test_client: TestClient):
        """Test eGenes without tissue parameter."""
        response = test_client.get("/api/v1/association/egenes")

        assert response.status_code == 422


class TestSQTLRoutes:
    """Test sQTL (splicing quantitative trait loci) API routes."""

    def test_get_single_tissue_sqtl_basic(self, test_client: TestClient):
        """Test basic single tissue sQTL retrieval."""
        response = test_client.get(
            "/api/v1/association/sqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_sqtl_by_intron(self, test_client: TestClient):
        """Test single tissue sQTL by intron cluster."""
        response = test_client.get(
            "/api/v1/association/sqtl/single-tissue",
            params={
                "intron_cluster_id": ["chr17:43044295:43125364:clu_12345"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    def test_get_single_tissue_sqtl_pvalue_threshold(self, test_client: TestClient):
        """Test single tissue sQTL with p-value threshold."""
        response = test_client.get(
            "/api/v1/association/sqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "pvalue_threshold": 1e-5,
            },
        )

        assert response.status_code == 200

    def test_get_sgenes_basic(self, test_client: TestClient):
        """Test basic sGenes retrieval."""
        response = test_client.get(
            "/api/v1/association/sgenes",
            params={
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200


class TestVariantAssociationRoutes:
    """Test variant association API routes."""

    def test_get_variants_by_location_basic(self, test_client: TestClient):
        """Test basic variant retrieval by location."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "chromosome": "chr17",
                "start": 43000000,
                "end": 44000000,
                "dataset_id": "gtex_v8",
            },
        )

        assert response.status_code == 200

    def test_get_variants_by_id(self, test_client: TestClient):
        """Test variant retrieval by ID."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "variant_id": [
                    "chr17_43051071_T_C_b38",
                    "chr17_43082434_G_A_b38",
                ],
            },
        )

        assert response.status_code == 200

    def test_get_variants_by_rs_id(self, test_client: TestClient):
        """Test variant retrieval by rs ID."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "rs_id": ["rs8176318", "rs1799966"],
            },
        )

        assert response.status_code == 200

    def test_get_variants_maf_filter(self, test_client: TestClient):
        """Test variant retrieval with MAF filter."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "chromosome": "chr17",
                "start": 43000000,
                "end": 44000000,
                "min_maf": 0.01,
                "max_maf": 0.5,
            },
        )

        assert response.status_code == 200

    def test_get_variants_invalid_range(self, test_client: TestClient):
        """Test variant retrieval with invalid range."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "chromosome": "chr17",
                "start": 50000000,
                "end": 40000000,  # Invalid: end < start
            },
        )

        assert response.status_code == 422


class TestAsyncAssociationRoutes:
    """Test association routes with async client."""

    @pytest.mark.asyncio
    async def test_async_single_tissue_eqtl(self, async_client: AsyncClient):
        """Test async single tissue eQTL retrieval."""
        response = await async_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_egenes(self, async_client: AsyncClient):
        """Test async eGenes retrieval."""
        response = await async_client.get(
            "/api/v1/association/egenes", params={"tissue_site_detail_id": ["Whole_Blood"]}
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_variants(self, async_client: AsyncClient):
        """Test async variant retrieval."""
        response = await async_client.get(
            "/api/v1/association/variants",
            params={
                "chromosome": "chr17",
                "start": 43000000,
                "end": 44000000,
            },
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_async_concurrent_association_requests(self, async_client: AsyncClient):
        """Test concurrent async association requests."""
        import asyncio

        tasks = [
            async_client.get(
                "/api/v1/association/eqtl/single-tissue",
                params={
                    "gene_symbol": ["BRCA1"],
                    "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                },
            ),
            async_client.get(
                "/api/v1/association/egenes", params={"tissue_site_detail_id": ["Whole_Blood"]}
            ),
            async_client.get(
                "/api/v1/association/variants",
                params={"chromosome": "chr17", "start": 43000000, "end": 44000000},
            ),
        ]

        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200


class TestAssociationRouteErrorHandling:
    """Test error handling in association routes."""

    def test_eqtl_invalid_tissue_id(self, test_client: TestClient):
        """Test eQTL with invalid tissue ID."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": ["Invalid_Tissue"],
            },
        )

        assert response.status_code == 422

    def test_eqtl_invalid_chromosome(self, test_client: TestClient):
        """Test eQTL with invalid chromosome."""
        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "chromosome": "chr99",  # Invalid chromosome
                "start": 1000000,
                "end": 2000000,
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
            },
        )

        assert response.status_code == 422

    def test_variants_missing_location_params(self, test_client: TestClient):
        """Test variant retrieval with missing location parameters."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={"chromosome": "chr17"},  # Missing start and end
        )

        assert response.status_code == 422

    def test_egenes_invalid_qvalue(self, test_client: TestClient):
        """Test eGenes with invalid q-value."""
        response = test_client.get(
            "/api/v1/association/egenes",
            params={
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "qvalue_threshold": 1.5,  # Invalid: > 1.0
            },
        )

        assert response.status_code == 422


class TestAssociationRoutePerformance:
    """Test performance aspects of association routes."""

    def test_eqtl_large_gene_list(self, test_client: TestClient):
        """Test eQTL with large gene list."""
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
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": large_gene_list,
                "tissue_site_detail_id": ["Breast_Mammary_Tissue"],
                "pvalue_threshold": 1e-5,
            },
        )

        assert response.status_code == 200

    def test_eqtl_multiple_tissues(self, test_client: TestClient):
        """Test eQTL across multiple tissues."""
        cancer_tissues = [
            "Breast_Mammary_Tissue",
            "Ovary",
            "Prostate",
            "Lung",
            "Colon_Transverse",
            "Liver",
            "Stomach",
            "Kidney_Cortex",
        ]

        response = test_client.get(
            "/api/v1/association/eqtl/single-tissue",
            params={
                "gene_symbol": ["BRCA1"],
                "tissue_site_detail_id": cancer_tissues,
                "pvalue_threshold": 1e-5,
            },
        )

        assert response.status_code == 200

    def test_variants_large_genomic_region(self, test_client: TestClient):
        """Test variant retrieval for large genomic region."""
        response = test_client.get(
            "/api/v1/association/variants",
            params={
                "chromosome": "chr17",
                "start": 1,
                "end": 10000000,  # Large region (10Mb)
                "min_maf": 0.01,
            },
        )

        assert response.status_code == 200

    @pytest.mark.slow
    def test_concurrent_eqtl_requests(self, test_client: TestClient):
        """Test concurrent eQTL requests."""
        import concurrent.futures

        def make_eqtl_request(gene_tissue_pair):
            gene, tissue = gene_tissue_pair
            return test_client.get(
                "/api/v1/association/eqtl/single-tissue",
                params={
                    "gene_symbol": [gene],
                    "tissue_site_detail_id": [tissue],
                    "pvalue_threshold": 1e-5,
                },
            )

        gene_tissue_pairs = [
            ("BRCA1", "Breast_Mammary_Tissue"),
            ("TP53", "Lung"),
            ("EGFR", "Brain_Cortex"),
            ("MYC", "Liver"),
        ]

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(make_eqtl_request, pair) for pair in gene_tissue_pairs]
            responses = [future.result() for future in futures]

        for response in responses:
            assert response.status_code == 200
