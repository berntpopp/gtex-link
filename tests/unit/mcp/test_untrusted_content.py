"""Structural untrusted-text fencing contracts."""

from __future__ import annotations

import hashlib

import pytest

from gtex_link.mcp.untrusted_content import (
    UntrustedTextLimitError,
    enforce_untrusted_text_limits,
    fence_untrusted_text,
)


def test_fence_normalizes_and_removes_forbidden_controls() -> None:
    raw = "Cafe\u0301\x00\u200b\u202e\nBRCA1"
    fenced = fence_untrusted_text(raw, source="gtex", record_id="ENSG00000012048.20")

    assert fenced.kind == "untrusted_text"
    assert fenced.text == "Caf\u00e9\nBRCA1"
    assert fenced.raw_sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert fenced.provenance.source == "gtex"
    assert fenced.provenance.record_id == "ENSG00000012048.20"


def test_fence_preserves_tabs_newlines_and_scientific_symbols() -> None:
    raw = "p.Gly12Asp\t\u0394G = \u22121.2 kcal/mol\r\n"
    assert fence_untrusted_text(raw, source="gtex", record_id="ENSG00000012048.20").text == raw


def test_limits_reject_oversized_object() -> None:
    big = fence_untrusted_text("x" * 10, source="gtex", record_id="ENSG00000012048.20")
    with pytest.raises(UntrustedTextLimitError):
        enforce_untrusted_text_limits([big], max_text_bytes=5)


def test_limits_reject_too_many_objects() -> None:
    objs = [fence_untrusted_text("x", source="gtex", record_id=f"ENSG{i}") for i in range(3)]
    with pytest.raises(UntrustedTextLimitError):
        enforce_untrusted_text_limits(objs, max_objects=2)


def test_limits_accept_large_object_count_under_search_ceiling() -> None:
    """A >128-object result must NOT raise when max_objects reflects the real cap."""
    objs = [
        fence_untrusted_text(f"gene {i}", source="gtex", record_id=f"ENSG{i}") for i in range(200)
    ]
    enforce_untrusted_text_limits(objs, max_objects=10_000)
