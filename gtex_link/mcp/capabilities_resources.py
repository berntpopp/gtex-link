"""Register gtex:// discovery resources on a FastMCP instance."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from gtex_link.mcp.metadata import build_capabilities
from gtex_link.mcp.resources import (
    GTEX_REFERENCE_NOTES,
    GTEX_USAGE_NOTES,
    RECOMMENDED_CITATION,
    RESEARCH_USE_NOTICE,
)

if TYPE_CHECKING:
    from fastmcp import FastMCP


def register_capability_resources(mcp: FastMCP) -> None:
    """Register the gtex:// resource family."""

    @mcp.resource("gtex://capabilities", mime_type="application/json")
    def capabilities() -> str:
        return json.dumps(build_capabilities())

    @mcp.resource("gtex://usage", mime_type="text/plain")
    def usage() -> str:
        return GTEX_USAGE_NOTES

    @mcp.resource("gtex://reference", mime_type="text/plain")
    def reference() -> str:
        return GTEX_REFERENCE_NOTES

    @mcp.resource("gtex://research-use", mime_type="text/plain")
    def research_use() -> str:
        return RESEARCH_USE_NOTICE

    @mcp.resource("gtex://citations", mime_type="text/plain")
    def citations() -> str:
        return RECOMMENDED_CITATION
