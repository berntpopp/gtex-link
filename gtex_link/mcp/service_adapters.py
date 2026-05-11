"""Service binding for MCP tools.

This module is the single place where `GTExClient` and `GTExService` are
instantiated for MCP tool use. Tool modules call `get_gtex_service()` to
obtain a shared, lazily-constructed service instance.
"""

from __future__ import annotations

from functools import lru_cache

from gtex_link.api.client import GTExClient
from gtex_link.config import DEFAULT_API_CONFIG, DEFAULT_CACHE_CONFIG
from gtex_link.services.gtex_service import GTExService


@lru_cache(maxsize=1)
def get_gtex_service() -> GTExService:
    """Return the shared GTExService instance for MCP tools."""
    client = GTExClient(config=DEFAULT_API_CONFIG)
    return GTExService(client=client, cache_config=DEFAULT_CACHE_CONFIG)


def reset_gtex_service() -> None:
    """Clear the cached service instance (test helper)."""
    get_gtex_service.cache_clear()
