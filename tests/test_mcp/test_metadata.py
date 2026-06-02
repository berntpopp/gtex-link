"""Tests for the capabilities surface."""

from __future__ import annotations

from gtex_link.mcp.metadata import build_capabilities, capabilities_version, valid_tissues


def test_valid_tissues_excludes_empty_sentinel() -> None:
    tissues = valid_tissues()
    assert "" not in tissues
    assert "Kidney_Medulla" in tissues
    assert len(tissues) == 54


def test_capabilities_has_expected_top_level_keys() -> None:
    caps = build_capabilities()
    for key in (
        "server",
        "server_version",
        "mcp_protocol_version",
        "gtex_release",
        "research_use_only",
        "datasets",
        "tissues",
        "tools",
        "error_codes",
        "response_fields",
        "capabilities_version",
        "citation",
    ):
        assert key in caps
    assert caps["mcp_protocol_version"] == "2025-11-25"
    assert "" not in caps["tissues"]
    assert "get_median_expression_levels" in caps["tools"]


def test_capabilities_version_is_stable() -> None:
    assert capabilities_version() == capabilities_version()
    assert len(capabilities_version()) == 16
