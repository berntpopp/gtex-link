"""Pytest configuration and fixtures for GTEx-Link tests."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient
import pytest
import pytest_asyncio

from gtex_link.api.client import GTExClient
from gtex_link.app import create_app
from gtex_link.config import CacheConfigModel, GTExAPIConfigModel, ServerSettings
from gtex_link.services.gtex_service import GTExService

from .fixtures.gtex_api_responses import (
    EGENES_RESPONSE,
    GENE_SEARCH_RESPONSE,
    MEDIAN_GENE_EXPRESSION_RESPONSE,
    SERVICE_INFO_RESPONSE,
    SUBJECT_RESPONSE,
    TEST_GENCODE_IDS,
    TEST_GENE_SYMBOLS,
    TEST_TISSUE_IDS,
    TEST_VARIANT_IDS,
    TISSUE_SITE_DETAILS_RESPONSE,
    TOP_EXPRESSED_GENES_RESPONSE,
    VARIANT_RESPONSE,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_api_config() -> GTExAPIConfigModel:
    """Create test API configuration."""
    return GTExAPIConfigModel(
        base_url="https://test.gtexportal.org/api/v2/",
        timeout=10,
        rate_limit_per_second=10.0,
        burst_size=20,
        max_retries=2,
        retry_delay=0.1,  # Fast for tests
        user_agent="GTEx-Link-Test/0.1.0",
    )


@pytest.fixture
def test_cache_config() -> CacheConfigModel:
    """Create test cache configuration."""
    return CacheConfigModel(
        size=100,
        ttl=60,  # Short TTL for tests
        stats_enabled=True,
        cleanup_interval=60,  # Must be >= 60 per validation rules
    )


@pytest.fixture
def test_settings(
    test_api_config: GTExAPIConfigModel, test_cache_config: CacheConfigModel
) -> ServerSettings:
    """Create test server settings."""
    settings = ServerSettings(
        host="127.0.0.1",
        port=8000,
        transport_mode="http",
        log_level="DEBUG",
        log_format="console",
    )
    settings.api = test_api_config
    settings.cache = test_cache_config
    return settings


@pytest.fixture
def app():
    """Create FastAPI app for testing."""
    return create_app()


@pytest.fixture
def test_client(app) -> Generator[TestClient, None, None]:
    """Create test client."""
    client = TestClient(app)
    yield client
    client.close()


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    from httpx._transports.asgi import ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def gtex_client(test_api_config: GTExAPIConfigModel) -> AsyncGenerator[GTExClient, None]:
    """Create GTEx client for testing."""
    logger = MagicMock()
    client = GTExClient(config=test_api_config, logger=logger)
    yield client
    await client.close()


@pytest.fixture
def mock_gtex_client(test_api_config: GTExAPIConfigModel) -> MagicMock:
    """Create mock GTEx client with realistic responses."""
    mock_client = AsyncMock(spec=GTExClient)
    mock_client.config = test_api_config

    # Configure mock responses
    mock_client.get_service_info.return_value = SERVICE_INFO_RESPONSE
    mock_client.search_genes.return_value = GENE_SEARCH_RESPONSE
    mock_client.get_genes.return_value = GENE_SEARCH_RESPONSE
    mock_client.get_median_gene_expression.return_value = MEDIAN_GENE_EXPRESSION_RESPONSE
    mock_client.get_tissue_site_details.return_value = TISSUE_SITE_DETAILS_RESPONSE
    mock_client.get_top_expressed_genes.return_value = TOP_EXPRESSED_GENES_RESPONSE

    # Mock stats
    mock_client.stats = {
        "total_requests": 10,
        "successful_requests": 9,
        "success_rate": 0.9,
        "current_rate": 2.5,
        "current_tokens": 8.0,
        "avg_response_time": 0.15,
    }

    return mock_client


@pytest.fixture
def mock_gtex_service(
    mock_gtex_client: MagicMock, test_cache_config: CacheConfigModel
) -> MagicMock:
    """Create mock GTEx service."""
    mock_service = AsyncMock(spec=GTExService)
    mock_service.client = mock_gtex_client
    mock_service.cache_config = test_cache_config

    # Configure cache stats
    mock_service.cache_stats = {
        "hits": 15,
        "misses": 5,
        "hit_rate": 75.0,
        "total_requests": 20,
        "cached_functions": 5,
    }

    mock_service.get_cache_info.return_value = {
        "search_genes": {
            "hits": 8,
            "misses": 2,
            "current_size": 10,
            "max_size": 100,
            "hit_rate": 80.0,
        },
        "get_median_gene_expression": {
            "hits": 5,
            "misses": 2,
            "current_size": 7,
            "max_size": 100,
            "hit_rate": 71.4,
        },
    }

    return mock_service


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    return MagicMock()


# Test data fixtures
@pytest.fixture
def sample_gene_data():
    """Sample gene data from real GTEx API."""
    return GENE_SEARCH_RESPONSE["data"][0]


@pytest.fixture
def sample_expression_data():
    """Sample expression data from real GTEx API."""
    return MEDIAN_GENE_EXPRESSION_RESPONSE["data"][0]


@pytest.fixture
def sample_variant_data():
    """Sample variant data from real GTEx API."""
    return VARIANT_RESPONSE["data"][0]


@pytest.fixture
def sample_tissue_data():
    """Sample tissue data from real GTEx API."""
    return TISSUE_SITE_DETAILS_RESPONSE["data"][0]


@pytest.fixture
def test_gene_symbols():
    """Common gene symbols for testing."""
    return TEST_GENE_SYMBOLS


@pytest.fixture
def test_gencode_ids():
    """Common Gencode IDs for testing."""
    return TEST_GENCODE_IDS


@pytest.fixture
def test_variant_ids():
    """Common variant IDs for testing."""
    return TEST_VARIANT_IDS


@pytest.fixture
def test_tissue_ids():
    """Common tissue IDs for testing."""
    return TEST_TISSUE_IDS


# Response fixtures for different scenarios
@pytest.fixture
def gene_search_response():
    """Complete gene search response."""
    return GENE_SEARCH_RESPONSE


@pytest.fixture
def median_expression_response():
    """Complete median expression response."""
    return MEDIAN_GENE_EXPRESSION_RESPONSE


@pytest.fixture
def tissue_response():
    """Complete tissue response."""
    return TISSUE_SITE_DETAILS_RESPONSE


@pytest.fixture
def top_genes_response():
    """Complete top genes response."""
    return TOP_EXPRESSED_GENES_RESPONSE


@pytest.fixture
def variant_response():
    """Complete variant response."""
    return VARIANT_RESPONSE


@pytest.fixture
def egenes_response():
    """Complete eGenes response."""
    return EGENES_RESPONSE


@pytest.fixture
def subject_response():
    """Complete subject response."""
    return SUBJECT_RESPONSE


@pytest.fixture
def service_info_response():
    """Service info response."""
    return SERVICE_INFO_RESPONSE


# Parameterized fixtures for edge cases
@pytest.fixture(params=["BRCA1", "BRCA2", "TP53", "EGFR", "MYC", "PIK3CA", "KRAS", "PTEN"])
def gene_symbol(request):
    """Parameterized gene symbols for comprehensive testing."""
    return request.param


@pytest.fixture(
    params=[
        "Whole_Blood",
        "Breast_Mammary_Tissue",
        "Muscle_Skeletal",
        "Brain_Cortex",
        "Liver",
        "Lung",
    ]
)
def tissue_id(request):
    """Parameterized tissue IDs for comprehensive testing."""
    return request.param


@pytest.fixture(
    params=[
        ("chr17", 43000000, 44000000),
        ("chr13", 32000000, 33000000),
        ("chrX", 100000, 200000),
    ]
)
def genomic_region(request):
    """Parameterized genomic regions for testing."""
    chromosome, start, end = request.param
    return {"chromosome": chromosome, "start": start, "end": end}


# Error simulation fixtures
@pytest.fixture
def api_error_responses():
    """Provide common API error responses for testing."""
    return {
        "rate_limit": {
            "status_code": 429,
            "headers": {"Retry-After": "60"},
            "content": {"detail": "Rate limit exceeded"},
        },
        "server_error": {"status_code": 500, "content": {"detail": "Internal server error"}},
        "not_found": {"status_code": 404, "content": {"detail": "Gene not found"}},
        "validation_error": {
            "status_code": 422,
            "content": {
                "detail": [
                    {
                        "loc": ["query_params", "itemsPerPage"],
                        "msg": "ensure this value is less than or equal to 1000",
                        "type": "value_error.number.not_le",
                    }
                ]
            },
        },
    }


# Performance testing fixtures
@pytest.fixture
def large_gene_list():
    """Large list of genes for performance testing."""
    return TEST_GENE_SYMBOLS * 100  # 800 genes


@pytest.fixture
def pagination_scenarios():
    """Different pagination scenarios for testing."""
    return [
        {"page": 0, "items_per_page": 10},
        {"page": 0, "items_per_page": 250},
        {"page": 1, "items_per_page": 100},
        {"page": 10, "items_per_page": 50},
    ]
