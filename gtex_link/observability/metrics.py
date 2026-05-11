"""Prometheus metrics collectors and ASGI integration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


# --- Collectors ---------------------------------------------------------

HTTP_REQUESTS = Counter(
    "gtex_http_requests_total",
    "HTTP requests served by GTEx-Link",
    labelnames=("method", "route", "status"),
)

HTTP_REQUEST_DURATION = Histogram(
    "gtex_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=("method", "route"),
)

UPSTREAM_REQUESTS = Counter(
    "gtex_upstream_requests_total",
    "Outbound calls to the GTEx Portal API",
    labelnames=("endpoint", "status"),
)

UPSTREAM_REQUEST_DURATION = Histogram(
    "gtex_upstream_request_duration_seconds",
    "Upstream GTEx Portal call duration in seconds",
    labelnames=("endpoint",),
)

CACHE_HITS = Counter(
    "gtex_cache_hits_total",
    "Cache hits",
    labelnames=("cache",),
)

CACHE_MISSES = Counter(
    "gtex_cache_misses_total",
    "Cache misses",
    labelnames=("cache",),
)

RATE_LIMIT_WAITS = Counter(
    "gtex_rate_limit_waits_total",
    "Number of times the rate limiter forced the caller to wait",
)

RATE_LIMIT_WAIT_SECONDS = Histogram(
    "gtex_rate_limit_wait_seconds",
    "Time spent waiting on the rate limiter",
)

MCP_TOOL_CALLS = Counter(
    "gtex_mcp_tool_calls_total",
    "MCP tool invocations",
    labelnames=("tool", "status"),
)


# --- Middleware ---------------------------------------------------------


class MetricsMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records HTTP request counters and histograms."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        # Don't measure the /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        route = self._resolve_route(request)
        start = time.perf_counter()
        status = "500"
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        finally:
            duration = time.perf_counter() - start
            HTTP_REQUESTS.labels(method=request.method, route=route, status=status).inc()
            HTTP_REQUEST_DURATION.labels(method=request.method, route=route).observe(duration)

    @staticmethod
    def _resolve_route(request: Request) -> str:
        """Return the route template (e.g., '/api/expression/medianGeneExpression').

        Falls back to the raw path if no route is matched (e.g., 404s).
        """
        route = request.scope.get("route")
        if route is not None and hasattr(route, "path"):
            return str(route.path)
        return request.url.path


def install_metrics_middleware(app: FastAPI) -> None:
    """Install the HTTP-request metrics middleware on a FastAPI app."""
    app.add_middleware(MetricsMiddleware)


def install_metrics_route(app: FastAPI) -> None:
    """Mount the `/metrics` Prometheus exposition endpoint on a FastAPI app."""

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# --- Call-site helpers --------------------------------------------------


def record_upstream_call(*, endpoint: str, status: int, duration_s: float) -> None:
    """Record an outbound GTEx Portal call: count + latency histogram."""
    UPSTREAM_REQUESTS.labels(endpoint=endpoint, status=str(status)).inc()
    UPSTREAM_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration_s)


def record_cache_event(*, cache: str, hit: bool) -> None:
    """Record a cache hit or miss for the named cache."""
    if hit:
        CACHE_HITS.labels(cache=cache).inc()
    else:
        CACHE_MISSES.labels(cache=cache).inc()


def record_rate_limit_wait(*, wait_s: float) -> None:
    """Record a forced wait on the upstream rate limiter."""
    RATE_LIMIT_WAITS.inc()
    RATE_LIMIT_WAIT_SECONDS.observe(wait_s)


def record_mcp_tool_call(*, tool: str, success: bool) -> None:
    """Record an MCP tool invocation with success/error status."""
    MCP_TOOL_CALLS.labels(tool=tool, status="ok" if success else "error").inc()
