"""Security guard: GTEx-Link must not log free-text search queries, subject or
sample identifiers, or the full upstream URL. These are PII / leakage vectors
(Theme A, LOW). The test drives each anchor with a high-entropy sentinel and
asserts the sentinel (and the upstream host) never appear in any emitted log
value. Research use only; not clinical decision support."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from gtex_link.api.client import GTExClient
from gtex_link.api.routes.dependencies import get_logger_dependency
from gtex_link.app import create_app
from gtex_link.config import GTExAPIConfigModel
from gtex_link.exceptions import GTExAPIError
from gtex_link.logging_config import log_api_request
from gtex_link.models import DatasetSampleRequest, SubjectRequest
from gtex_link.services.gtex_service import GTExService

if TYPE_CHECKING:
    import respx

SENTINEL = "SENTINEL-PII-7f3a"

# The router/app default to the real GTEx Portal base URL; respx patterns target
# it so the running app's / client's outbound httpx calls are intercepted.
GTEX_DEFAULT_BASE = "https://gtexportal.org/api/v2"

_EMPTY_PAGINATED = {
    "data": [],
    "pagingInfo": {
        "numberOfPages": 0,
        "page": 0,
        "maxItemsPerPage": 250,
        "totalNumberOfItems": 0,
    },
}


def _logged_text(logger: MagicMock) -> str:
    """Concatenate every positional + keyword value passed to any logger method."""
    parts: list[str] = []
    for _name, args, kwargs in logger.method_calls:
        parts.extend(str(a) for a in args)
        parts.extend(str(v) for v in kwargs.values())
    return " ".join(parts)


@pytest.mark.asyncio
async def test_search_query_not_logged(mock_gtex_client, test_cache_config, mock_logger):
    """The free-text `search` query must not be logged."""
    service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

    await service._search_genes_impl(query=SENTINEL)

    assert SENTINEL not in _logged_text(mock_logger)


@pytest.mark.asyncio
async def test_subject_ids_not_logged(mock_gtex_client, test_cache_config, mock_logger):
    """Subject identifiers must not be logged."""
    mock_gtex_client.get_subjects.return_value = _EMPTY_PAGINATED
    service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

    await service._get_subjects_impl(SubjectRequest(subject_id=[SENTINEL]))

    assert SENTINEL not in _logged_text(mock_logger)


@pytest.mark.asyncio
async def test_sample_ids_not_logged(mock_gtex_client, test_cache_config, mock_logger):
    """Sample identifiers must not be logged."""
    mock_gtex_client.get_samples.return_value = _EMPTY_PAGINATED
    service = GTExService(mock_gtex_client, test_cache_config, mock_logger)

    await service._get_samples_impl(DatasetSampleRequest(sample_id=[SENTINEL]))

    assert SENTINEL not in _logged_text(mock_logger)


def test_upstream_url_not_logged(mock_logger):
    """The full upstream URL (scheme + host + query) must not be logged."""
    url = f"https://gtexportal.org/api/v2/reference/gene?geneId={SENTINEL}"

    log_api_request(mock_logger, "GET", url, 0.012, 200)

    logged = _logged_text(mock_logger)
    assert SENTINEL not in logged
    assert "gtexportal.org" not in logged
    assert "https://" not in logged


def test_search_genes_route_query_not_logged(respx_mock: respx.MockRouter) -> None:
    """Route-level guard: the public geneSearch route handler is a separate log
    site from the service and must not log the free-text `geneId` query."""
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/reference/geneSearch").respond(200, json=_EMPTY_PAGINATED)
    mock = MagicMock()
    app = create_app()
    # Override the logger dependency so the route (and the service it builds) log
    # into an inspectable mock instead of the real structured logger.
    app.dependency_overrides[get_logger_dependency] = lambda: mock
    try:
        client = TestClient(app)
        resp = client.get("/api/reference/geneSearch", params={"geneId": SENTINEL})
        assert resp.status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert SENTINEL not in _logged_text(mock)


@pytest.mark.asyncio
async def test_client_json_parse_failure_does_not_log_upstream_host(
    respx_mock: respx.MockRouter,
) -> None:
    """Failure-path guard: on an unparseable upstream body the client diagnostics
    must log the request path, never the full upstream URL (scheme + host)."""
    logger = MagicMock()
    client = GTExClient(config=GTExAPIConfigModel(), logger=logger)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/reference/geneSearch").respond(
        200, text="<<not valid json>>"
    )

    with pytest.raises(GTExAPIError):
        await client._make_request("GET", "reference/geneSearch")
    await client.close()

    logged = _logged_text(logger)
    assert "gtexportal.org" not in logged
    assert "https://" not in logged


@pytest.mark.asyncio
async def test_client_retry_warning_does_not_log_upstream_host(
    respx_mock: respx.MockRouter,
) -> None:
    """Retry-path guard: the 'Request failed, retrying' warning must log the
    request path, never the full upstream URL (scheme + host)."""
    logger = MagicMock()
    client = GTExClient(config=GTExAPIConfigModel(max_retries=1, retry_delay=0.1), logger=logger)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/reference/geneSearch").mock(
        side_effect=[
            httpx.RequestError("network boom"),
            httpx.Response(200, json=_EMPTY_PAGINATED),
        ]
    )

    result = await client._make_request("GET", "reference/geneSearch")
    await client.close()

    assert result == _EMPTY_PAGINATED
    logged = _logged_text(logger)
    assert "gtexportal.org" not in logged
    assert "https://" not in logged
