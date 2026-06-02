"""Tissue sample-size lookup and per-tissue distribution stats.

Per-tissue RNA-seq sample count is a dataset-level constant from
dataset/tissueSiteDetail.rnaSeqSampleSummary.totalCount (gene-independent),
so one cached call per dataset feeds `numSamples` on every median row with no
per-query round trip. Spread (min/max/quartiles/IQR) has no precomputed GTEx
endpoint and is derived from geneExpression per-sample arrays on demand.
"""

from __future__ import annotations

import statistics
from typing import TYPE_CHECKING, Any

from gtex_link.models import TissueSiteDetailRequest

if TYPE_CHECKING:
    from gtex_link.services.gtex_service import GTExService


async def sample_count_map(service: GTExService, dataset_id: str) -> dict[str, int]:
    """Return {tissueSiteDetailId: rnaSeqSampleSummary.totalCount} for *dataset_id*.

    Backed by the service's already-cached get_tissue_site_details, so repeated
    calls within the cache TTL cost nothing.
    """
    request = TissueSiteDetailRequest.model_validate({"datasetId": dataset_id})
    result = await service.get_tissue_site_details(request)
    return {
        row.tissue_site_detail_id: row.rna_seq_sample_summary.total_count for row in result.data
    }


def compute_spread(values: list[float]) -> dict[str, Any] | None:
    """Return distribution stats for a per-sample value list, or None if empty."""
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    if n >= 2:
        quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
        q1, _med, q3 = quartiles[0], quartiles[1], quartiles[2]
    else:
        q1 = q3 = ordered[0]
    return {
        "n": n,
        "min": ordered[0],
        "max": ordered[-1],
        "q1": round(q1, 4),
        "median": round(statistics.median(ordered), 4),
        "q3": round(q3, 4),
        "iqr": round(q3 - q1, 4),
    }
