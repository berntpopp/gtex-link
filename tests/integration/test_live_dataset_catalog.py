"""Live proof that the advertised GTEx dataset set remains truthful."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from gtex_link.models.gtex import DATASET_GENCODE_VERSION

FIXTURE = Path(__file__).parents[1] / "fixtures" / "gtex_dataset_catalog_2026-09-01.json"
BASE_URL = "https://gtexportal.org/api/v2"


@pytest.mark.integration
def test_live_catalog_and_representative_datasets_match_captured_truth() -> None:
    captured = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert captured["supported"] == DATASET_GENCODE_VERSION
    assert set(captured["catalog_ids"]) == set(captured["supported"]) | set(captured["excluded"])

    with httpx.Client(timeout=30.0, follow_redirects=False) as client:
        catalog = client.get(f"{BASE_URL}/metadata/dataset")
        catalog.raise_for_status()
        payload = catalog.json()
        assert isinstance(payload, list)
        assert {row["datasetId"] for row in payload} == set(captured["catalog_ids"])

        for dataset_id in DATASET_GENCODE_VERSION:
            response = client.get(
                f"{BASE_URL}/dataset/tissueSiteDetail", params={"datasetId": dataset_id}
            )
            response.raise_for_status()
            rows = response.json()["data"]
            assert rows
            assert {row["datasetId"] for row in rows} == {dataset_id}

        absent = client.get(
            f"{BASE_URL}/dataset/tissueSiteDetail",
            params={"datasetId": "gtex_snrnaseq_pilot"},
        )
        absent.raise_for_status()
        assert absent.json()["data"] == []
