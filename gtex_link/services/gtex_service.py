"""GTEx service with caching and business logic."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from gtex_link.exceptions import ValidationError
from gtex_link.models import (
    DatasetSampleRequest,
    GeneExpressionRequest,
    GeneRequest,
    MedianGeneExpressionRequest,
    PaginatedDatasetSampleResponse,
    PaginatedExonResponse,
    PaginatedGeneExpressionResponse,
    PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedSubjectResponse,
    PaginatedTissueSiteDetailResponse,
    PaginatedTopExpressedGenesResponse,
    PaginatedTranscriptResponse,
    PaginatedVariantResponse,
    ServiceInfo,
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

        # Apply caching decorators to all data-fetching methods
        self._setup_cached_methods()

    def _setup_cached_methods(self) -> None:
        """Apply caching decorators to all data-fetching methods."""
        # Apply decorators using cache config TTL and size
        default_maxsize = self.cache_config.size
        default_ttl = self.cache_config.ttl

        # Service info (rarely changes)
        self.get_service_info = self.cache.cached(maxsize=1, ttl=1800, key_pattern="service_info")(
            self._get_service_info_impl
        )

        # Reference endpoints
        self.search_genes = self.cache.cached(
            maxsize=min(500, default_maxsize), ttl=default_ttl, key_pattern="gene_search"
        )(self._search_genes_impl)

        self.get_genes = self.cache.cached(
            maxsize=min(1000, default_maxsize), ttl=default_ttl * 2, key_pattern="genes"
        )(self._get_genes_impl)

        self.get_transcripts = self.cache.cached(
            maxsize=min(500, default_maxsize), ttl=default_ttl * 2, key_pattern="transcripts"
        )(self._get_transcripts_impl)

        self.get_exons = self.cache.cached(
            maxsize=min(300, default_maxsize), ttl=default_ttl * 2, key_pattern="exons"
        )(self._get_exons_impl)

        # Expression endpoints
        self.get_median_gene_expression = self.cache.cached(
            maxsize=min(800, default_maxsize), ttl=default_ttl, key_pattern="median_expression"
        )(self._get_median_gene_expression_impl)

        self.get_gene_expression = self.cache.cached(
            maxsize=min(600, default_maxsize), ttl=default_ttl, key_pattern="gene_expression"
        )(self._get_gene_expression_impl)

        self.get_top_expressed_genes = self.cache.cached(
            maxsize=min(400, default_maxsize), ttl=default_ttl, key_pattern="top_genes"
        )(self._get_top_expressed_genes_impl)

        # Dataset endpoints
        self.get_tissue_site_details = self.cache.cached(
            maxsize=min(200, default_maxsize), ttl=default_ttl * 2, key_pattern="tissues"
        )(self._get_tissue_site_details_impl)

        self.get_subjects = self.cache.cached(
            maxsize=min(400, default_maxsize), ttl=default_ttl * 2, key_pattern="subjects"
        )(self._get_subjects_impl)

        self.get_samples = self.cache.cached(
            maxsize=min(600, default_maxsize), ttl=default_ttl * 2, key_pattern="samples"
        )(self._get_samples_impl)

        self.get_variants = self.cache.cached(
            maxsize=min(800, default_maxsize), ttl=default_ttl, key_pattern="variants"
        )(self._get_variants_impl)

        self.get_variants_by_location = self.cache.cached(
            maxsize=min(600, default_maxsize), ttl=default_ttl, key_pattern="variants_location"
        )(self._get_variants_by_location_impl)

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

    # Service info endpoint (implementation method called by cached version)
    async def _get_service_info_impl(self) -> ServiceInfo:
        """Get GTEx Portal service information."""
        self.logger.info("Fetching GTEx service information") if self.logger else None
        raw_data = await self.client.get_service_info()
        return ServiceInfo(**raw_data)

    # Reference endpoints (implementation methods called by cached versions)
    async def _search_genes_impl(
        self,
        query: str,
        dataset_id: str = "gtex_v8",
        page: int = 0,
        page_size: int = 250,
    ) -> PaginatedGeneResponse:
        """Search for genes in GTEx database."""
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

    async def _get_genes_impl(self, params: GeneRequest) -> PaginatedGeneResponse:
        """Get gene information."""
        self.logger.info("Fetching genes", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_genes(api_params)
        return PaginatedGeneResponse(**raw_data)

    async def _get_transcripts_impl(self, params: TranscriptRequest) -> PaginatedTranscriptResponse:
        """Get transcript information."""
        self.logger.info("Fetching transcripts", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_transcripts(api_params)
        return PaginatedTranscriptResponse(**raw_data)

    async def _get_exons_impl(self, params: dict[str, Any]) -> PaginatedExonResponse:
        """Get exon information."""
        self.logger.info("Fetching exons", **params) if self.logger else None
        raw_data = await self.client.get_exons(params)
        return PaginatedExonResponse(**raw_data)

    # Expression endpoints (implementation methods called by cached versions)

    async def _get_median_gene_expression_impl(
        self, params: MedianGeneExpressionRequest
    ) -> PaginatedMedianGeneExpressionResponse:
        """Get median gene expression data."""
        (
            self.logger.info("Fetching median gene expression", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        # Convert empty string tissue filter to None for GTEx API compatibility
        if api_params.get("tissueSiteDetailId") == "":
            api_params.pop("tissueSiteDetailId", None)
        raw_data = await self.client.get_median_gene_expression(api_params)
        return PaginatedMedianGeneExpressionResponse(**raw_data)

    async def _get_gene_expression_impl(
        self, params: GeneExpressionRequest
    ) -> PaginatedGeneExpressionResponse:
        """Get gene expression data."""
        self.logger.info("Fetching gene expression", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        # Convert empty string tissue filter to None for GTEx API compatibility
        if api_params.get("tissueSiteDetailId") == "":
            api_params.pop("tissueSiteDetailId", None)
        raw_data = await self.client.get_gene_expression(api_params)
        return PaginatedGeneExpressionResponse(**raw_data)

    async def _get_top_expressed_genes_impl(
        self, params: TopExpressedGenesRequest
    ) -> PaginatedTopExpressedGenesResponse:
        """Get top expressed genes."""
        (
            self.logger.info("Fetching top expressed genes", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_top_expressed_genes(api_params)
        return PaginatedTopExpressedGenesResponse(**raw_data)

    # Dataset endpoints (implementation methods called by cached versions)

    async def _get_tissue_site_details_impl(
        self, params: TissueSiteDetailRequest
    ) -> PaginatedTissueSiteDetailResponse:
        """Get tissue site details."""
        (
            self.logger.info("Fetching tissue site details", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_tissue_site_details(api_params)
        return PaginatedTissueSiteDetailResponse(**raw_data)

    async def _get_subjects_impl(self, params: SubjectRequest) -> PaginatedSubjectResponse:
        """Get subject information."""
        self.logger.info("Fetching subjects", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_subjects(api_params)
        return PaginatedSubjectResponse(**raw_data)

    async def _get_samples_impl(
        self, params: DatasetSampleRequest
    ) -> PaginatedDatasetSampleResponse:
        """Get sample information."""
        self.logger.info("Fetching samples", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_samples(api_params)
        return PaginatedDatasetSampleResponse(**raw_data)

    async def _get_variants_impl(self, params: VariantRequest) -> PaginatedVariantResponse:
        """Get variant information."""
        self.logger.info("Fetching variants", **params.model_dump()) if self.logger else None
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
        raw_data = await self.client.get_variants(api_params)
        return PaginatedVariantResponse(**raw_data)

    async def _get_variants_by_location_impl(
        self, params: VariantByLocationRequest
    ) -> PaginatedVariantResponse:
        """Get variants by genomic location."""
        (
            self.logger.info("Fetching variants by location", **params.model_dump())
            if self.logger
            else None
        )
        api_params = params.model_dump(by_alias=True, exclude_none=True, mode="json")
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
