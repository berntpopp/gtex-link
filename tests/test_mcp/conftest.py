"""Shared fixtures for MCP tool tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gtex_link.mcp.service_adapters import reset_gtex_service


@pytest.fixture(autouse=True)
def _reset_gtex_service() -> Iterator[None]:
    """Reset the cached GTExService before and after each test.

    Why: get_gtex_service() is @lru_cache(maxsize=1), so the bound httpx
    AsyncClient would otherwise persist across pytest's per-test event loops.
    """
    reset_gtex_service()
    yield
    reset_gtex_service()
