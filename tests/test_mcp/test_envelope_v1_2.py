"""Response-Envelope Standard v1.2: provenance on every success, checked against the schema.

The schema is vendored from berntpopp/genefoundry-envelope, tag v1.2.0. Every tool that
carries a `_meta` frame is called through the real facade (the harness of
`test_provenance_meta.py`) and its result validated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from gtex_link.mcp.envelope import run_mcp_tool
from gtex_link.utils.caching import CacheManager

from .test_provenance_meta import (
    _MINIMAL_ARGS,
    PROVENANCE_META_TOOLS,
    _call_tool,
    _v10_service,
    patch_service,
)

CONFORMANCE = Path(__file__).parents[1] / "conformance"
SCHEMA = Draft202012Validator(json.loads((CONFORMANCE / "envelope-v1.2.schema.json").read_text()))


def _errors(envelope: Any) -> list[str]:
    return [f"{e.json_path}: {e.message}" for e in SCHEMA.iter_errors(envelope)]


def test_vendored_schema_is_the_v1_2_0_release() -> None:
    digest = hashlib.sha256((CONFORMANCE / "envelope-v1.2.schema.json").read_bytes()).hexdigest()
    assert digest == (CONFORMANCE / "envelope-v1.2.schema.sha256").read_text().strip()
    assert digest == "c3c47e20d7dd189aac2568fc963b5514d7a5ac2c3e5f21d126f42c96d1ad1ae3"


@pytest.mark.parametrize("tool", sorted(PROVENANCE_META_TOOLS))
async def test_data_tool_success_is_a_v1_2_envelope(tool: str) -> None:
    with patch_service(_v10_service()):
        envelope = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert envelope["success"] is True, envelope
    assert _errors(envelope) == []
    meta = envelope["_meta"]
    assert meta["source"] == "gtex"
    assert meta["data_version"] == meta["gtex_release"]
    assert all(
        isinstance(meta[key], str) and meta[key]
        for key in ("source", "data_version", "retrieved_at", "request_id")
    )


async def test_data_version_follows_the_dataset_queried() -> None:
    args = {"gencode_id": ["BRCA1"], "dataset_id": "gtex_v10"}
    with patch_service(_v10_service()):
        envelope = await _call_tool("get_median_expression_levels", args)
    assert envelope["_meta"]["data_version"] == "gtex_v10"


async def test_error_is_a_valid_envelope_without_provenance() -> None:
    args = {"gencode_id": ["BRCA1"], "dataset_id": "not-a-dataset"}
    with patch_service(_v10_service()):
        envelope = await _call_tool("get_median_expression_levels", args)

    assert envelope["success"] is False
    assert _errors(envelope) == []
    assert "retrieved_at" not in envelope["_meta"]


async def test_a_cache_hit_keeps_the_time_of_the_fetch_that_filled_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upstream_calls = 0

    @CacheManager().cached(ttl=10**12)  # the entry is dated 2023 below and must not expire
    async def fetch(key: str) -> dict[str, Any]:
        nonlocal upstream_calls
        upstream_calls += 1
        return {"results": [key]}

    async def stamp() -> str:
        async def call() -> dict[str, Any]:
            return dict(await fetch("BRCA1"))

        return str((await run_mcp_tool("t", call))["_meta"]["retrieved_at"])

    monkeypatch.setattr("time.time", lambda: 1_700_000_000.0)
    first = await stamp()
    monkeypatch.undo()  # the second call runs today

    assert first == await stamp() == "2023-11-14T22:13:20Z"
    assert upstream_calls == 1
