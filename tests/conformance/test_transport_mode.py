"""Stateless-tier construction guard (in-process, no server needed)."""

from __future__ import annotations

import inspect

from fastapi.testclient import TestClient

from gtex_link import __version__, server_manager
from gtex_link.app import app


def test_unified_server_builds_stateless_json_mcp_app() -> None:
    src = inspect.getsource(server_manager.UnifiedServerManager.start_unified_server)
    assert "stateless_http=True" in src, "MCP app must be built stateless"
    assert "json_response=True" in src, "MCP app must return JSON responses"
    assert 'mount("/"' in src, "MCP ASGI app must mount at root (no 307)"


def test_health_endpoint_returns_transport_standard_fields() -> None:
    """GET /health must return {status, version, transport} for the conformance probe."""
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["transport"] == "streamable-http-stateless"
