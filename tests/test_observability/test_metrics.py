"""Tests for Prometheus metrics."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gtex_link.observability.metrics import (
    install_metrics_middleware,
    install_metrics_route,
    record_cache_event,
    record_upstream_call,
)


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format() -> None:
    """GET /metrics returns Prometheus text exposition format."""
    app = FastAPI()
    install_metrics_route(app)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "gtex_" in response.text  # at least one collector defined


@pytest.mark.asyncio
async def test_request_metric_increments_on_request() -> None:
    """Wired middleware increments the request counter on a request."""
    app = FastAPI()
    install_metrics_middleware(app)
    install_metrics_route(app)

    @app.get("/echo")
    async def echo() -> dict[str, str]:
        return {"ok": "true"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/echo")
        await client.get("/echo")
        metrics_response = await client.get("/metrics")

    # Should see at least one sample for the /echo route.
    assert "gtex_http_requests_total" in metrics_response.text
    assert "/echo" in metrics_response.text


def test_record_upstream_call_increments_counter() -> None:
    """record_upstream_call updates the upstream request counter."""
    from prometheus_client import REGISTRY

    record_upstream_call(endpoint="reference/gene", status=200, duration_s=0.123)

    # Probe the registry for our counter
    found = False
    for metric in REGISTRY.collect():
        if metric.name == "gtex_upstream_requests":
            for sample in metric.samples:
                if (
                    sample.labels.get("endpoint") == "reference/gene"
                    and sample.labels.get("status") == "200"
                ):
                    found = True
    assert found, "expected gtex_upstream_requests_total sample not found"


def test_record_cache_event_increments_hit_or_miss() -> None:
    """record_cache_event tracks hits and misses."""
    from prometheus_client import REGISTRY

    record_cache_event(cache="gene_search", hit=True)
    record_cache_event(cache="gene_search", hit=False)

    hit_seen = False
    miss_seen = False
    for metric in REGISTRY.collect():
        if metric.name == "gtex_cache_hits":
            for sample in metric.samples:
                if sample.labels.get("cache") == "gene_search":
                    hit_seen = True
        if metric.name == "gtex_cache_misses":
            for sample in metric.samples:
                if sample.labels.get("cache") == "gene_search":
                    miss_seen = True
    assert hit_seen and miss_seen
