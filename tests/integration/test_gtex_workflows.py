"""Integration tests for GTEx end-to-end workflows with real data patterns."""

import pytest

from gtex_link.models import (
    Chromosome,
    DatasetId,
    MedianGeneExpressionRequest,
    PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse,
    SingleTissueEqtlRequest,
    TissueSiteDetailId,
    TopExpressedGenesRequest,
    VariantByLocationRequest,
)
from gtex_link.services.gtex_service import GTExService


class TestCancerGeneAnalysisWorkflow:
    """Test complete cancer gene analysis workflow."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_brca_gene_analysis_complete_workflow(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        gene_search_response,
        median_expression_response,
        eqtl_response,
    ):
        """Test complete BRCA gene analysis workflow."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        # Configure mocks for complete workflow
        mock_gtex_client.search_genes.return_value = gene_search_response
        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response
        mock_gtex_client.get_single_tissue_eqtl.return_value = eqtl_response

        # Step 1: Search for BRCA genes
        brca_genes = ["BRCA1", "BRCA2"]
        gene_results = []

        for gene in brca_genes:
            result = await service.search_genes(query=gene)
            gene_results.append(result)
            assert isinstance(result, PaginatedGeneResponse)
            assert len(result.data) > 0

        # Step 2: Get expression data for breast and ovarian tissues
        breast_tissues = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.OVARY,
        ]

        expression_results = []
        for tissue in breast_tissues:
            expression_request = MedianGeneExpressionRequest(
                gene_symbol=brca_genes,
                tissue_site_detail_id=[tissue],
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_median_gene_expression(expression_request)
            expression_results.append(result)
            assert isinstance(result, PaginatedMedianGeneExpressionResponse)

        # Step 3: Get eQTL data for breast tissue
        eqtl_request = SingleTissueEqtlRequest(
            gene_symbol=brca_genes,
            tissue_site_detail_id=[TissueSiteDetailId.BREAST_MAMMARY_TISSUE],
            pvalue_threshold=1e-5,
            dataset_id=DatasetId.GTEX_V8,
        )
        eqtl_result = await service.get_single_tissue_eqtl(eqtl_request)

        # Verify workflow completion
        assert len(gene_results) == 2
        assert len(expression_results) == 2
        assert len(eqtl_result.data) == 2

        # Verify service call counts
        assert mock_gtex_client.search_genes.call_count == 2
        assert mock_gtex_client.get_median_gene_expression.call_count == 2
        mock_gtex_client.get_single_tissue_eqtl.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_cancer_gene_comparative_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        gene_search_response,
        median_expression_response,
    ):
        """Test comparative analysis across multiple cancer genes."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.search_genes.return_value = gene_search_response
        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response

        # Cancer genes of interest
        cancer_genes = ["BRCA1", "BRCA2", "TP53", "EGFR", "MYC", "KRAS"]

        # Step 1: Search all genes
        gene_info = {}
        for gene in cancer_genes:
            result = await service.search_genes(query=gene)
            gene_info[gene] = result

        # Step 2: Compare expression across tissues
        comparison_tissues = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.LUNG,
            TissueSiteDetailId.LIVER,
            TissueSiteDetailId.COLON_TRANSVERSE,
            TissueSiteDetailId.PROSTATE,
        ]

        tissue_expression = {}
        for tissue in comparison_tissues:
            request = MedianGeneExpressionRequest(
                gene_symbol=cancer_genes,
                tissue_site_detail_id=[tissue],
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_median_gene_expression(request)
            tissue_expression[tissue] = result

        # Verify comprehensive analysis
        assert len(gene_info) == 6
        assert len(tissue_expression) == 5

        for gene, info in gene_info.items():
            assert isinstance(info, PaginatedGeneResponse)

        for tissue, expression in tissue_expression.items():
            assert isinstance(expression, PaginatedMedianGeneExpressionResponse)

        # Verify service calls
        assert mock_gtex_client.search_genes.call_count == 6
        assert mock_gtex_client.get_median_gene_expression.call_count == 5


class TestGenomicRegionAnalysisWorkflow:
    """Test genomic region analysis workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_chromosome_17_hotspot_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        gene_search_response,
        variant_response,
        eqtl_response,
    ):
        """Test analysis of chromosome 17 cancer hotspot region."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        # Configure mocks
        mock_gtex_client.search_genes.return_value = gene_search_response
        mock_gtex_client.get_variants.return_value = variant_response
        mock_gtex_client.get_single_tissue_eqtl.return_value = eqtl_response

        # Chr17 cancer hotspot region (BRCA1 locus)
        hotspot_region = {
            "chromosome": Chromosome.CHR17,
            "start": 43000000,
            "end": 44000000,
        }

        # Step 1: Find genes in region
        genes_in_region = await service.search_genes(
            query="BRCA1",  # Primary gene of interest
            dataset_id=DatasetId.GTEX_V8,
        )

        # Step 2: Get variants in region
        variant_request = VariantByLocationRequest(
            chromosome=hotspot_region["chromosome"],
            start=hotspot_region["start"],
            end=hotspot_region["end"],
            dataset_id=DatasetId.GTEX_V8,
        )
        variants_in_region = await service.get_variants_by_location(variant_request)

        # Step 3: Get eQTLs for the region in cancer-relevant tissues
        cancer_tissues = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.OVARY,
        ]

        eqtl_results = []
        for tissue in cancer_tissues:
            eqtl_request = SingleTissueEqtlRequest(
                gene_symbol=["BRCA1"],
                tissue_site_detail_id=[tissue],
                pvalue_threshold=1e-5,
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_single_tissue_eqtl(eqtl_request)
            eqtl_results.append(result)

        # Verify comprehensive region analysis
        assert isinstance(genes_in_region, PaginatedGeneResponse)
        assert len(variants_in_region.data) > 0
        assert len(eqtl_results) == 2

        # Verify service calls
        mock_gtex_client.search_genes.assert_called_once()
        mock_gtex_client.get_variants.assert_called_once()
        assert mock_gtex_client.get_single_tissue_eqtl.call_count == 2

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multi_chromosome_comparative_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        gene_search_response,
        median_expression_response,
    ):
        """Test comparative analysis across multiple chromosomes."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.search_genes.return_value = gene_search_response
        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response

        # Key cancer genes on different chromosomes
        chromosome_genes = {
            Chromosome.CHR17: ["BRCA1", "TP53"],
            Chromosome.CHR13: ["BRCA2", "RB1"],
            Chromosome.CHR7: ["EGFR", "MET"],
            Chromosome.CHR12: ["KRAS", "MDM2"],
        }

        chromosome_results = {}

        for chromosome, genes in chromosome_genes.items():
            gene_results = []
            expression_results = []

            # Search genes on each chromosome
            for gene in genes:
                gene_result = await service.search_genes(query=gene)
                gene_results.append(gene_result)

            # Get expression data for genes
            expression_request = MedianGeneExpressionRequest(
                gene_symbol=genes,
                tissue_site_detail_id=[TissueSiteDetailId.WHOLE_BLOOD],
                dataset_id=DatasetId.GTEX_V8,
            )
            expression_result = await service.get_median_gene_expression(expression_request)
            expression_results.append(expression_result)

            chromosome_results[chromosome] = {
                "genes": gene_results,
                "expression": expression_results,
            }

        # Verify cross-chromosome analysis
        assert len(chromosome_results) == 4

        for chromosome, results in chromosome_results.items():
            assert len(results["genes"]) == 2
            assert len(results["expression"]) == 1

            for gene_result in results["genes"]:
                assert isinstance(gene_result, PaginatedGeneResponse)

            for expr_result in results["expression"]:
                assert isinstance(expr_result, PaginatedMedianGeneExpressionResponse)

        # Verify service calls (2 genes × 4 chromosomes = 8 gene searches, 4 expression calls)
        assert mock_gtex_client.search_genes.call_count == 8
        assert mock_gtex_client.get_median_gene_expression.call_count == 4


class TestTissueComparativeAnalysisWorkflow:
    """Test tissue comparative analysis workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_tissue_specificity_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        median_expression_response,
        top_genes_response,
    ):
        """Test tissue specificity analysis workflow."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response
        mock_gtex_client.get_top_expressed_genes.return_value = top_genes_response

        # Test gene across multiple tissues
        test_gene = "BRCA1"
        tissue_panel = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.OVARY,
            TissueSiteDetailId.UTERUS,
            TissueSiteDetailId.WHOLE_BLOOD,
            TissueSiteDetailId.MUSCLE_SKELETAL,
            TissueSiteDetailId.BRAIN_CORTEX,
            TissueSiteDetailId.LIVER,
            TissueSiteDetailId.LUNG,
        ]

        # Step 1: Get expression across all tissues
        tissue_expression = {}
        for tissue in tissue_panel:
            request = MedianGeneExpressionRequest(
                gene_symbol=[test_gene],
                tissue_site_detail_id=[tissue],
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_median_gene_expression(request)
            tissue_expression[tissue] = result

        # Step 2: Get top expressed genes in each tissue for context
        top_genes_per_tissue = {}
        for tissue in tissue_panel:
            request = TopExpressedGenesRequest(
                tissue_site_detail_id=tissue,
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_top_expressed_genes(request)
            top_genes_per_tissue[tissue] = result

        # Verify comprehensive tissue analysis
        assert len(tissue_expression) == 8
        assert len(top_genes_per_tissue) == 8

        for tissue, expression in tissue_expression.items():
            assert isinstance(expression, PaginatedMedianGeneExpressionResponse)

        # Verify service calls
        assert mock_gtex_client.get_median_gene_expression.call_count == 8
        assert mock_gtex_client.get_top_expressed_genes.call_count == 8

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_developmental_tissue_comparison(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        median_expression_response,
    ):
        """Test developmental tissue comparison workflow."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response

        # Developmental genes
        dev_genes = ["SOX2", "NANOG", "POU5F1", "KLF4", "MYC"]

        # Tissues representing different developmental stages/lineages
        developmental_tissues = {
            "stem_cell_like": [TissueSiteDetailId.TESTIS],
            "neural": [
                TissueSiteDetailId.BRAIN_CORTEX,
                TissueSiteDetailId.BRAIN_CEREBELLUM,
                TissueSiteDetailId.SPINAL_CORD_CERVICAL,
            ],
            "reproductive": [
                TissueSiteDetailId.OVARY,
                TissueSiteDetailId.TESTIS,
                TissueSiteDetailId.UTERUS,
            ],
            "metabolic": [
                TissueSiteDetailId.LIVER,
                TissueSiteDetailId.PANCREAS,
                TissueSiteDetailId.ADIPOSE_SUBCUTANEOUS,
            ],
        }

        lineage_results = {}

        for lineage, tissues in developmental_tissues.items():
            lineage_expression = {}

            for tissue in tissues:
                request = MedianGeneExpressionRequest(
                    gene_symbol=dev_genes,
                    tissue_site_detail_id=[tissue],
                    dataset_id=DatasetId.GTEX_V8,
                )
                result = await service.get_median_gene_expression(request)
                lineage_expression[tissue] = result

            lineage_results[lineage] = lineage_expression

        # Verify developmental analysis
        assert len(lineage_results) == 4

        for lineage, tissues in lineage_results.items():
            for tissue, expression in tissues.items():
                assert isinstance(expression, PaginatedMedianGeneExpressionResponse)

        # Verify total service calls (11 total tissues)
        total_tissues = sum(len(tissues) for tissues in developmental_tissues.values())
        assert mock_gtex_client.get_median_gene_expression.call_count == total_tissues


class TestPerformanceIntegrationWorkflows:
    """Test performance-focused integration workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_large_scale_gene_expression_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        median_expression_response,
        large_gene_list,
    ):
        """Test large-scale gene expression analysis performance."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response

        # Simulate analysis of large gene list (100 genes)
        gene_batch = large_gene_list[:100]
        tissue = TissueSiteDetailId.WHOLE_BLOOD

        # Process in batches to simulate real-world usage
        batch_size = 10
        batch_results = []

        for i in range(0, len(gene_batch), batch_size):
            batch = gene_batch[i : i + batch_size]
            request = MedianGeneExpressionRequest(
                gene_symbol=batch,
                tissue_site_detail_id=[tissue],
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_median_gene_expression(request)
            batch_results.append(result)

        # Verify large-scale processing
        assert len(batch_results) == 10  # 100 genes / 10 per batch

        for result in batch_results:
            assert isinstance(result, PaginatedMedianGeneExpressionResponse)

        # Verify caching efficiency (should be exactly 10 calls due to batching)
        assert mock_gtex_client.get_median_gene_expression.call_count == 10

    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_comprehensive_multi_tissue_gene_analysis(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        median_expression_response,
        eqtl_response,
    ):
        """Test comprehensive multi-tissue analysis for single gene."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response
        mock_gtex_client.get_single_tissue_eqtl.return_value = eqtl_response

        target_gene = "BRCA1"

        # All major tissue types for comprehensive analysis
        all_tissues = [
            TissueSiteDetailId.ADIPOSE_SUBCUTANEOUS,
            TissueSiteDetailId.ADRENAL_GLAND,
            TissueSiteDetailId.ARTERY_AORTA,
            TissueSiteDetailId.BRAIN_CORTEX,
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.COLON_TRANSVERSE,
            TissueSiteDetailId.HEART_LEFT_VENTRICLE,
            TissueSiteDetailId.KIDNEY_CORTEX,
            TissueSiteDetailId.LIVER,
            TissueSiteDetailId.LUNG,
            TissueSiteDetailId.MUSCLE_SKELETAL,
            TissueSiteDetailId.OVARY,
            TissueSiteDetailId.PANCREAS,
            TissueSiteDetailId.PROSTATE,
            TissueSiteDetailId.SKIN_SUN_EXPOSED,
            TissueSiteDetailId.STOMACH,
            TissueSiteDetailId.TESTIS,
            TissueSiteDetailId.THYROID,
            TissueSiteDetailId.UTERUS,
            TissueSiteDetailId.WHOLE_BLOOD,
        ]

        # Get expression data for all tissues
        expression_results = {}
        for tissue in all_tissues:
            request = MedianGeneExpressionRequest(
                gene_symbol=[target_gene],
                tissue_site_detail_id=[tissue],
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_median_gene_expression(request)
            expression_results[tissue] = result

        # Get eQTL data for subset of tissues (cancer-relevant)
        eqtl_tissues = [
            TissueSiteDetailId.BREAST_MAMMARY_TISSUE,
            TissueSiteDetailId.OVARY,
            TissueSiteDetailId.PROSTATE,
            TissueSiteDetailId.LUNG,
            TissueSiteDetailId.COLON_TRANSVERSE,
        ]

        eqtl_results = {}
        for tissue in eqtl_tissues:
            request = SingleTissueEqtlRequest(
                gene_symbol=[target_gene],
                tissue_site_detail_id=[tissue],
                pvalue_threshold=1e-5,
                dataset_id=DatasetId.GTEX_V8,
            )
            result = await service.get_single_tissue_eqtl(request)
            eqtl_results[tissue] = result

        # Verify comprehensive analysis
        assert len(expression_results) == 20
        assert len(eqtl_results) == 5

        for tissue, result in expression_results.items():
            assert isinstance(result, PaginatedMedianGeneExpressionResponse)

        # Verify service call counts
        assert mock_gtex_client.get_median_gene_expression.call_count == 20
        assert mock_gtex_client.get_single_tissue_eqtl.call_count == 5


class TestErrorHandlingIntegrationWorkflows:
    """Test error handling in integration workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_partial_failure_recovery_workflow(
        self,
        mock_gtex_client,
        test_cache_config,
        mock_logger,
        gene_search_response,
        median_expression_response,
    ):
        """Test workflow recovery from partial failures."""
        service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

        # Configure mixed success/failure responses
        mock_gtex_client.search_genes.side_effect = [
            gene_search_response,  # Success
            Exception("Network timeout"),  # Failure
            gene_search_response,  # Success after retry
        ]
        mock_gtex_client.get_median_gene_expression.return_value = median_expression_response

        genes_to_analyze = ["BRCA1", "TP53", "EGFR"]
        successful_searches = []
        failed_searches = []

        # Attempt to search all genes with error handling
        for gene in genes_to_analyze:
            try:
                result = await service.search_genes(query=gene)
                successful_searches.append((gene, result))
            except Exception as e:
                failed_searches.append((gene, str(e)))

        # Continue with successful genes for expression analysis
        successful_genes = [gene for gene, _ in successful_searches]
        if successful_genes:
            expression_request = MedianGeneExpressionRequest(
                gene_symbol=successful_genes,
                tissue_site_detail_id=[TissueSiteDetailId.WHOLE_BLOOD],
                dataset_id=DatasetId.GTEX_V8,
            )
            expression_result = await service.get_median_gene_expression(expression_request)

        # Verify partial success handling
        assert len(successful_searches) == 2  # BRCA1 and EGFR succeeded
        assert len(failed_searches) == 1  # TP53 failed
        assert failed_searches[0][0] == "TP53"
        assert "Network timeout" in failed_searches[0][1]

        # Verify expression analysis continued with successful genes
        assert isinstance(expression_result, PaginatedMedianGeneExpressionResponse)

        # Verify service calls
        assert mock_gtex_client.search_genes.call_count == 3
        mock_gtex_client.get_median_gene_expression.assert_called_once()
