"""Shared fixtures for unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.profiles import MCPToolProfile

if TYPE_CHECKING:
    from fastmcp import FastMCP


@pytest.fixture
def facade() -> FastMCP:
    """A FastMCP facade with the full tool surface registered.

    ``list_tools()`` only inspects registrations, so no service injection is
    needed for tool-name introspection.
    """
    return create_gtex_mcp(profile=MCPToolProfile.FULL)
