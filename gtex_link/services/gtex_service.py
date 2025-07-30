"""GTEx service with caching and business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.exceptions import ValidationError
from gtex_link.models import (
    DatasetSampleRequest,
    EqtlGeneRequest,
    GeneExpressionRequest,
    GeneRequest,
    MedianGeneExpressionRequest,
    PaginatedDatasetSampleResponse,
    PaginatedEqtlGeneResponse,
    PaginatedExonResponse,
    PaginatedGeneExpressionResponse,
    PaginatedGeneResponse,
    PaginatedIndependentEqtlResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedMetaSoftResponse,
    PaginatedSGeneResponse,
    PaginatedSingleTissueEqtlResponse,
    PaginatedSingleTissueSqtlResponse,
    PaginatedSubjectResponse,
    PaginatedTissueSiteDetailResponse,
    PaginatedTopExpressedGenesResponse,
    PaginatedTranscriptResponse,
    PaginatedVariantResponse,
    ServiceInfo,
    SGeneRequest,
    SingleTissueEqtlRequest,
    SingleTissueSqtlRequest,
    SubjectRequest,
    TissueSiteDetailRequest,
    TopExpressedGenesRequest,
    TranscriptRequest,
    VariantByLocationRequest,
    VariantRequest,
)
from gtex_link.utils.caching import create_service_cache_decorator

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from gtex_link.api.client import GTExClient
    from gtex_link.config import CacheConfigModel


class GTExService:
    """Service for GTEx Portal operations with caching and business logic."""

    def __init__(
        self,
        client: GTExClient,
        cache_config: CacheConfigModel,
        logger: FilteringBoundLogger | None = None,
    ) -> None:
        """Initialize GTEx service.

        Args:
            client: GTEx Portal API client
            cache_config: Cache configuration
            logger: Optional logger instance
        """
        self.client = client
        self.cache_config = cache_config
        self.logger = logger

        # Initialize centralized cache manager
        self.cache = create_service_cache_decorator(logger)

    def _generate_cache_key(self, operation: str, **kwargs: Any) -> str:
        """Generate cache key for operation.

        Args:
            operation: Operation name
            **kwargs: Parameters for cache key

        Returns:
            Cache key string
        """
        parts = [operation]
        for key, value in sorted(kwargs.items()):
            parts.append(f"{key}:{value}")
        return ":".join(parts)

    @property
    def cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        return self.cache.cache_stats

    # Service info endpoint
    async def get_service_info(self) -> ServiceInfo:
        """Get GTEx Portal service information with caching."""
        self.logger.info("Fetching GTEx service information") if self.logger else None
        raw_data = await self.client.get_service_info()
        return ServiceInfo(**raw_data)

    # Reference endpoints
    async def search_genes(
        self,
        query: str,
        dataset_id: str = "gtex_v8",
        page: int = 0,
        page_size: int = 250,
    ) -> PaginatedGeneResponse:
        """Search for genes with caching."""
        (
            self.logger.info("Searching genes", query=query, dataset_id=dataset_id)
            if self.logger
            else None
        )

        # Validate inputs
        if not query or len(query.strip()) < 1:
            msg = "Query must be at least 1 character long"
            raise ValidationError(msg, field="query")

        raw_data = await self.client.search_genes(
            query=query.strip(),
            dataset_id=dataset_id,
            page=page,
            page_size=page_size,
        )
        return PaginatedGeneResponse(**raw_data)

    async def get_genes(self, params: GeneRequest) -> PaginatedGeneResponse:
        """Get gene information with caching."""
        self.logger.info("Fetching genes", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_genes(api_params)
        return PaginatedGeneResponse(**raw_data)

    async def get_transcripts(self, params: TranscriptRequest) -> PaginatedTranscriptResponse:
        """Get transcript information with caching."""
        self.logger.info("Fetching transcripts", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_transcripts(api_params)
        return PaginatedTranscriptResponse(**raw_data)

    async def get_exons(self, params: dict[str, Any]) -> PaginatedExonResponse:
        """Get exon information with caching."""
        self.logger.info("Fetching exons", **params) if self.logger else None
        raw_data = await self.client.get_exons(params)
        return PaginatedExonResponse(**raw_data)

    # Expression endpoints

    async def get_median_gene_expression(
        self, params: MedianGeneExpressionRequest
    ) -> PaginatedMedianGeneExpressionResponse:
        """Get median gene expression data with caching."""
        (
            self.logger.info("Fetching median gene expression", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_median_gene_expression(api_params)
        return PaginatedMedianGeneExpressionResponse(**raw_data)

    async def get_gene_expression(
        self, params: GeneExpressionRequest
    ) -> PaginatedGeneExpressionResponse:
        """Get gene expression data with caching."""
        self.logger.info("Fetching gene expression", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_gene_expression(api_params)
        return PaginatedGeneExpressionResponse(**raw_data)

    async def get_top_expressed_genes(
        self, params: TopExpressedGenesRequest
    ) -> PaginatedTopExpressedGenesResponse:
        """Get top expressed genes with caching."""
        (
            self.logger.info("Fetching top expressed genes", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_top_expressed_genes(api_params)
        return PaginatedTopExpressedGenesResponse(**raw_data)

    # Association endpoints

    async def get_single_tissue_eqtl(
        self, params: SingleTissueEqtlRequest
    ) -> PaginatedSingleTissueEqtlResponse:
        """Get single tissue eQTL data with caching."""
        (
            self.logger.info("Fetching single tissue eQTL", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_single_tissue_eqtl(api_params)
        return PaginatedSingleTissueEqtlResponse(**raw_data)

    async def get_single_tissue_sqtl(
        self, params: SingleTissueSqtlRequest
    ) -> PaginatedSingleTissueSqtlResponse:
        """Get single tissue sQTL data with caching."""
        (
            self.logger.info("Fetching single tissue sQTL", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_single_tissue_sqtl(api_params)
        return PaginatedSingleTissueSqtlResponse(**raw_data)

    async def get_egenes(self, params: EqtlGeneRequest) -> PaginatedEqtlGeneResponse:
        """Get eGene data with caching."""
        self.logger.info("Fetching eGenes", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_egenes(api_params)
        return PaginatedEqtlGeneResponse(**raw_data)

    async def get_sgenes(self, params: SGeneRequest) -> PaginatedSGeneResponse:
        """Get sGene data with caching."""
        self.logger.info("Fetching sGenes", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_sgenes(api_params)
        return PaginatedSGeneResponse(**raw_data)

    async def get_independent_eqtl(
        self, params: dict[str, Any]
    ) -> PaginatedIndependentEqtlResponse:
        """Get independent eQTL data with caching."""
        self.logger.info("Fetching independent eQTL", **params) if self.logger else None
        raw_data = await self.client.get_independent_eqtl(params)
        return PaginatedIndependentEqtlResponse(**raw_data)

    async def get_metasoft(self, params: dict[str, Any]) -> PaginatedMetaSoftResponse:
        """Get MetaSoft analysis data with caching."""
        self.logger.info("Fetching MetaSoft data", **params) if self.logger else None
        raw_data = await self.client.get_metasoft(params)
        return PaginatedMetaSoftResponse(**raw_data)

    # Dataset endpoints

    async def get_tissue_site_details(
        self, params: TissueSiteDetailRequest
    ) -> PaginatedTissueSiteDetailResponse:
        """Get tissue site details with caching."""
        (
            self.logger.info("Fetching tissue site details", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_tissue_site_details(api_params)
        return PaginatedTissueSiteDetailResponse(**raw_data)

    async def get_subjects(self, params: SubjectRequest) -> PaginatedSubjectResponse:
        """Get subject information with caching."""
        self.logger.info("Fetching subjects", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_subjects(api_params)
        return PaginatedSubjectResponse(**raw_data)

    async def get_samples(self, params: DatasetSampleRequest) -> PaginatedDatasetSampleResponse:
        """Get sample information with caching."""
        self.logger.info("Fetching samples", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_samples(api_params)
        return PaginatedDatasetSampleResponse(**raw_data)

    async def get_variants(self, params: VariantRequest) -> PaginatedVariantResponse:
        """Get variant information with caching."""
        self.logger.info("Fetching variants", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_variants(api_params)
        return PaginatedVariantResponse(**raw_data)

    async def get_variants_by_location(
        self, params: VariantByLocationRequest
    ) -> PaginatedVariantResponse:
        """Get variants by genomic location with caching."""
        (
            self.logger.info("Fetching variants by location", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode='json')
        raw_data = await self.client.get_variants_by_location(api_params)
        return PaginatedVariantResponse(**raw_data)

    # Utility methods
    def clear_cache(self, pattern: str | None = None) -> dict[str, int]:
        """Clear service cache.

        Args:
            pattern: Optional pattern to match (currently unused, clears all)

        Returns:
            Dictionary with cleared cache statistics
        """
        self.logger.info("Clearing service cache", pattern=pattern) if self.logger else None
        return self.cache.clear_all_caches(pattern)

    def get_cache_info(self) -> dict[str, Any]:
        """Get detailed cache information.

        Returns:
            Dictionary with cache information for each cached method
        """
        return self.cache.get_cache_info()

    @property
    def client_stats(self) -> dict[str, Any]:
        """Get API client statistics."""
        return self.client.stats
