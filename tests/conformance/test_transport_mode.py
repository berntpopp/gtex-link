"""Stateless-tier construction guard (in-process, no server needed)."""

from __future__ import annotations

import inspect
import json
from typing import Any

from fastapi.testclient import TestClient

from gtex_link import __version__, server_manager
from gtex_link.app import app


def test_unified_server_builds_stateless_json_mcp_app() -> None:
    src = inspect.getsource(server_manager.create_unified_app)
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


_MODERN_VERSION = "2026-07-28"
_MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": _MODERN_VERSION,
    "io.modelcontextprotocol/clientCapabilities": {},
    "io.modelcontextprotocol/clientInfo": {"name": "gtex-host-test", "version": "1.0.0"},
}


def _modern_post(client: TestClient, req_id: int, method: str, params: dict[str, object]) -> Any:
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": _MODERN_VERSION,
        "mcp-method": method,
    }
    if "name" in params:
        headers["mcp-name"] = str(params["name"])
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": {"_meta": _MODERN_META, **params},
    }
    return client.post("/mcp", headers=headers, json=body)


def test_modern_mcp_http_discovers_lists_calls_and_fences_unknown_tool() -> None:
    """2026-07-28 sessionless era: discover -> list -> call, unknown name never reflected."""
    hostile = "ignore-instructions-secret"
    with TestClient(server_manager.create_unified_app(), base_url="http://localhost") as client:
        discover = _modern_post(client, 1, "server/discover", {})
        listed = _modern_post(client, 2, "tools/list", {})
        # Missing required args: dispatch reaches the tool's arg validation, no upstream call.
        called = _modern_post(
            client, 3, "tools/call", {"name": "get_median_expression_levels", "arguments": {}}
        )
        unknown = _modern_post(client, 4, "tools/call", {"name": hostile, "arguments": {}})

    assert discover.status_code == 200
    assert _MODERN_VERSION in discover.json()["result"]["supportedVersions"]
    assert "mcp-session-id" not in discover.headers
    assert listed.status_code == 200
    assert "get_median_expression_levels" in {t["name"] for t in listed.json()["result"]["tools"]}
    assert called.status_code == 200
    called_result = called.json()["result"]
    assert called_result["isError"] is True
    assert called_result["structuredContent"]["error_code"] == "invalid_input"
    assert unknown.status_code == 200
    unknown_result = unknown.json()["result"]
    assert unknown_result["isError"] is True
    assert json.loads(unknown_result["content"][0]["text"]) == unknown_result["structuredContent"]
    assert unknown_result["structuredContent"]["error_code"] == "not_found"
    assert hostile not in unknown.text


_EVIL_METHOD = "evil__IGNORE_ALL_PREVIOUS__method"


def _assert_fixed_method_not_found(resp: Any) -> None:
    error = resp.json()["error"]
    assert error["code"] == -32601
    assert "data" not in error
    assert _EVIL_METHOD not in resp.text


def test_unknown_jsonrpc_method_is_not_echoed_legacy_era() -> None:
    """SDK 2 echoes an unknown METHOD in METHOD_NOT_FOUND ``data``; it must be stripped."""
    headers = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
    with TestClient(server_manager.create_unified_app(), base_url="http://localhost") as client:
        init = {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "probe", "version": "0"},
        }
        client.post(
            "/mcp",
            headers=headers,
            json={"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": init},
        )
        resp = client.post(
            "/mcp",
            headers={**headers, "mcp-protocol-version": "2025-06-18"},
            json={"jsonrpc": "2.0", "id": 1, "method": _EVIL_METHOD, "params": {}},
        )
    _assert_fixed_method_not_found(resp)


def test_unknown_jsonrpc_method_is_not_echoed_modern_era() -> None:
    with TestClient(server_manager.create_unified_app(), base_url="http://localhost") as client:
        resp = _modern_post(client, 1, _EVIL_METHOD, {})
    _assert_fixed_method_not_found(resp)
