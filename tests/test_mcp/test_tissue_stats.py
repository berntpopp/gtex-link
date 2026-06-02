"""Tests for tissue sample-count map and spread stats."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from gtex_link.mcp.tissue_stats import compute_spread, sample_count_map
from gtex_link.models.responses import (
    PaginatedTissueSiteDetailResponse,
    PaginationInfo,
    TissueSiteDetail,
)


def _tissue(tid: str, n: int) -> TissueSiteDetail:
    return TissueSiteDetail.model_validate(
        {
            "tissueSiteDetailId": tid, "colorHex": "000000", "colorRgb": "0,0,0",
            "datasetId": "gtex_v8", "eGeneCount": None, "expressedGeneCount": 1,
            "hasEGenes": False, "hasSGenes": False, "mappedInHubmap": False,
            "eqtlSampleSummary": {"totalCount": n, "female": {}, "male": {}},
            "rnaSeqSampleSummary": {"totalCount": n, "female": {}, "male": {}},
            "sGeneCount": None, "samplingSite": "x", "tissueSite": "x",
            "tissueSiteDetail": "x", "tissueSiteDetailAbbr": "x",
            "ontologyId": "UBERON:1", "ontologyIri": "http://x",
        }
    )


@pytest.mark.asyncio
async def test_sample_count_map_builds_tissue_to_n() -> None:
    service = AsyncMock()
    service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(
            data=[_tissue("Kidney_Medulla", 4), _tissue("Muscle_Skeletal", 803)],
            pagingInfo=PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=2),
        )
    )

    result = await sample_count_map(service, "gtex_v8")

    assert result == {"Kidney_Medulla": 4, "Muscle_Skeletal": 803}


def test_compute_spread_quartiles() -> None:
    spread = compute_spread([1224.0, 1837.0, 2395.0, 3766.0])
    assert spread["n"] == 4
    assert spread["min"] == 1224.0
    assert spread["max"] == 3766.0
    assert spread["q1"] <= spread["median"] <= spread["q3"]
    assert spread["iqr"] == pytest.approx(spread["q3"] - spread["q1"])


def test_compute_spread_empty_is_none() -> None:
    assert compute_spread([]) is None
