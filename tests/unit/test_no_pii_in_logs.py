"""Security guard: GTEx-Link must not log free-text search queries, subject or
sample identifiers, or the full upstream URL. These are PII / leakage vectors
(Theme A, LOW). The test drives each anchor with a high-entropy sentinel and
asserts the sentinel (and the upstream host) never appear in any emitted log
value. Research use only; not clinical decision support."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gtex_link.logging_config import log_api_request
from gtex_link.models import DatasetSampleRequest, SubjectRequest
from gtex_link.services.gtex_service import GTExService

if TYPE_CHECKING:
    from unittest.mock import MagicMock

SENTINEL = "SENTINEL-PII-7f3a"

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
