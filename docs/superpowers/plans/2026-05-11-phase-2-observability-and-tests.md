# Phase 2 — Observability & Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add correlation IDs, Prometheus metrics, and a `/metrics` endpoint; migrate HTTP-mocking tests to `respx`; turn on parallel test execution. No external API or MCP tool contract changes.

**Architecture:** New `gtex_link/observability/` package with `correlation.py` (asgi-correlation-id wiring + structlog processor) and `metrics.py` (Prometheus collectors + `/metrics` endpoint). `GTExClient` propagates correlation IDs as outbound `X-Request-ID` headers. ASGI middleware emits request metrics. Cache/rate-limit/MCP call sites increment counters at the call site. Tests migrate from hand-rolled httpx mocks to `respx` route-by-route; old fixtures stay alongside until each route is converted, then deleted.

**Tech Stack:** asgi-correlation-id 4.3+, prometheus-client 0.21+, structlog (already in), respx 0.22+, pytest-xdist 3.6+.

**Prerequisite:** Phase 1 merged. This plan assumes the `pyproject.toml`, `Makefile`, and dependency baseline from Phase 1.

---

## File Structure

**Create:**
- `gtex_link/observability/__init__.py`
- `gtex_link/observability/correlation.py`
- `gtex_link/observability/metrics.py`
- `tests/test_observability/__init__.py`
- `tests/test_observability/test_correlation.py`
- `tests/test_observability/test_metrics.py`
- `tests/fixtures/respx_responses.py` (declarative respx response bodies)

**Modify:**
- `gtex_link/app.py` (add middleware, add `/metrics` route)
- `gtex_link/logging_config.py` (add correlation_id processor; service/version fields)
- `gtex_link/api/client.py` (propagate inbound correlation ID outbound; emit upstream metrics)
- `gtex_link/services/gtex_service.py` (cache hit/miss metrics)
- `gtex_link/config.py` (no new settings; just ensure metrics endpoint excluded from CORS if needed — see Task 9)
- `tests/conftest.py` (respx fixture; remove hand-rolled httpx mocks once routes migrated)
- `tests/test_api/test_*_routes.py` (route-by-route respx migration)
- `tests/test_services/*.py` (respx migration)
- `tests/test_client/*.py` (respx migration)
- `CHANGELOG.md` (append Phase 2 Added section)

**Delete (after migration complete):**
- Any obsolete mock fixture functions in `tests/conftest.py` (named like `_install_httpx_mock_*`)

---

## Task 1: Create a feature branch

**Files:**
- No files modified

- [ ] **Step 1: Create branch from main**

```bash
git checkout main
git pull origin main
git checkout -b phase-2-observability-and-tests
```

---

## Task 2: Scaffold the observability package

**Files:**
- Create: `gtex_link/observability/__init__.py`

- [ ] **Step 1: Create directory and stub**

```bash
mkdir -p gtex_link/observability
```

Write `gtex_link/observability/__init__.py`:

```python
"""Observability — correlation IDs, structured logs, Prometheus metrics."""

from gtex_link.observability.correlation import (
    bind_correlation_id_processor,
    install_correlation_middleware,
)
from gtex_link.observability.metrics import (
    install_metrics_route,
    install_metrics_middleware,
    record_cache_event,
    record_mcp_tool_call,
    record_rate_limit_wait,
    record_upstream_call,
)

__all__ = [
    "bind_correlation_id_processor",
    "install_correlation_middleware",
    "install_metrics_middleware",
    "install_metrics_route",
    "record_cache_event",
    "record_mcp_tool_call",
    "record_rate_limit_wait",
    "record_upstream_call",
]
```

Note: the imported symbols are defined in later tasks; the file won't import successfully until Tasks 3 and 4 land.

- [ ] **Step 2: Commit (with the rest of this task's structure intentionally incomplete)**

Wait — don't commit a broken import. Combine this scaffold with Task 3 and Task 4 in a single commit. Move to Task 3 next.

---

## Task 3: Implement `correlation.py`

**Files:**
- Create: `gtex_link/observability/correlation.py`
- Test: `tests/test_observability/test_correlation.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_observability/__init__.py` (empty file).

Create `tests/test_observability/test_correlation.py`:

```python
"""Tests for correlation ID propagation."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from gtex_link.observability.correlation import install_correlation_middleware


@pytest.mark.asyncio
async def test_inbound_correlation_id_is_echoed() -> None:
    """Correlation ID sent in the request is echoed in the response."""
    app = FastAPI()
    install_correlation_middleware(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping", headers={"X-Request-ID": "abc-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "abc-123"


@pytest.mark.asyncio
async def test_correlation_id_is_generated_if_absent() -> None:
    """If no X-Request-ID is sent, the middleware generates one."""
    app = FastAPI()
    install_correlation_middleware(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"ok": "true"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_observability/test_correlation.py -v
```
Expected: import error (`gtex_link.observability.correlation` module missing).

- [ ] **Step 3: Write `gtex_link/observability/correlation.py`**

```python
"""Correlation ID middleware and structlog integration."""

from __future__ import annotations

from typing import Any

from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI


def install_correlation_middleware(app: FastAPI) -> None:
    """Install the correlation-id ASGI middleware on a FastAPI app.

    Generates a UUID if no `X-Request-ID` header is present; echoes the
    correlation ID back on the response.
    """
    app.add_middleware(
        CorrelationIdMiddleware,
        header_name="X-Request-ID",
        update_request_header=True,
    )


def bind_correlation_id_processor(
    _logger: Any, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that binds the current correlation ID into log events."""
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_observability/test_correlation.py -v
```
Expected: both tests pass.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/observability/__init__.py gtex_link/observability/correlation.py \
        tests/test_observability/__init__.py tests/test_observability/test_correlation.py
git commit -m "feat(observability): add correlation id middleware and structlog processor"
```

Note: `__init__.py`'s import of `metrics` still fails — fix in Task 4.

---

## Task 4: Implement `metrics.py`

**Files:**
- Create: `gtex_link/observability/metrics.py`
- Test: `tests/test_observability/test_metrics.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_observability/test_metrics.py`:

```python
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
    assert '/echo' in metrics_response.text


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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_observability/test_metrics.py -v
```
Expected: import error on `gtex_link.observability.metrics`.

- [ ] **Step 3: Write `gtex_link/observability/metrics.py`**

```python
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
        call_next: "Callable[[Request], Awaitable[StarletteResponse]]",
    ) -> StarletteResponse:
        # Don't measure the /metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)

        route = self._resolve_route(request)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            status = str(response.status_code)
            return response
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start
            HTTP_REQUESTS.labels(
                method=request.method, route=route, status=status
            ).inc()
            HTTP_REQUEST_DURATION.labels(method=request.method, route=route).observe(
                duration
            )

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
    UPSTREAM_REQUESTS.labels(endpoint=endpoint, status=str(status)).inc()
    UPSTREAM_REQUEST_DURATION.labels(endpoint=endpoint).observe(duration_s)


def record_cache_event(*, cache: str, hit: bool) -> None:
    if hit:
        CACHE_HITS.labels(cache=cache).inc()
    else:
        CACHE_MISSES.labels(cache=cache).inc()


def record_rate_limit_wait(*, wait_s: float) -> None:
    RATE_LIMIT_WAITS.inc()
    RATE_LIMIT_WAIT_SECONDS.observe(wait_s)


def record_mcp_tool_call(*, tool: str, success: bool) -> None:
    MCP_TOOL_CALLS.labels(tool=tool, status="ok" if success else "error").inc()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_observability/ -v
```
Expected: all 6 tests (correlation + metrics) pass.

- [ ] **Step 5: Commit**

```bash
git add gtex_link/observability/metrics.py tests/test_observability/test_metrics.py
git commit -m "feat(observability): add prometheus collectors and /metrics endpoint"
```

---

## Task 5: Wire correlation + metrics into the FastAPI app

**Files:**
- Modify: `gtex_link/app.py`

- [ ] **Step 1: Open `gtex_link/app.py` and modify the `create_app()` factory**

Find the section that adds CORS middleware (around line 46-52) and includes routers (around line 55-57). After CORS is installed but before routers are registered, install correlation. After router includes, install metrics middleware and the `/metrics` route.

Replace the body of `create_app()` (lines 33-74 in the current file) with:

```python
def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="GTEx-Link",
        description=(
            "High-performance MCP/API server for GTEx Portal genetic expression database"
        ),
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # Correlation ID and metrics middleware
    from gtex_link.observability import (
        install_correlation_middleware,
        install_metrics_middleware,
        install_metrics_route,
    )

    install_correlation_middleware(app)
    install_metrics_middleware(app)

    # Routers
    app.include_router(reference_router)
    app.include_router(expression_router)
    app.include_router(health_router)

    # Metrics endpoint
    install_metrics_route(app)

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        return {
            "name": "GTEx-Link",
            "version": "0.2.0",
            "description": (
                "High-performance MCP/API server for GTEx Portal genetic expression database"
            ),
            "docs": "/docs",
            "health": "/api/health",
            "metrics": "/metrics",
            "mcp_endpoint": settings.mcp_path,
        }

    return app
```

Note: bump the version reference from `"0.1.0"` to `"0.2.0"` in two places (FastAPI title and root endpoint).

- [ ] **Step 2: Verify the app still boots**

```bash
uv run python -c "from gtex_link.app import create_app; app = create_app(); print('OK')"
```
Expected: `OK` printed without exceptions.

- [ ] **Step 3: Run existing tests**

```bash
uv run pytest tests -q
```
Expected: existing tests pass. If `/metrics` 404s in any health test, add `/metrics` to the route allowlist there.

- [ ] **Step 4: Commit**

```bash
git add gtex_link/app.py
git commit -m "feat(app): wire correlation id, metrics middleware, /metrics endpoint"
```

---

## Task 6: Wire correlation processor into structlog

**Files:**
- Modify: `gtex_link/logging_config.py`

- [ ] **Step 1: Add the correlation processor to `configure_structlog()`**

Open `gtex_link/logging_config.py`. Find the `configure_structlog` function (starts around line 81). Modify the `shared_processors` list to include the correlation processor and a static service/version field.

Locate the existing `shared_processors = [...]` block (lines 84-91) and replace it with:

```python
    from gtex_link.observability.correlation import bind_correlation_id_processor

    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        bind_correlation_id_processor,
        structlog.processors.CallsiteParameterAdder(
            parameters=[structlog.processors.CallsiteParameter.MODULE]
        )
        if settings.log_show_caller
        else _noop_processor,
    ]
```

Add a tiny no-op processor at the bottom of the same file (after `log_error_with_context`):

```python
def _noop_processor(
    _logger: object, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """No-op structlog processor used to keep the processor chain stable."""
    return event_dict
```

Also add `service` and `version` static fields once at module top: add a constant just above `configure_structlog`:

```python
from gtex_link import __version__ as _GTEX_LINK_VERSION  # noqa: E402

_STATIC_FIELDS_PROCESSOR = structlog.processors.add_log_level  # placeholder
```

Actually use a cleaner approach — add this helper just above `configure_structlog`:

```python
def _add_static_fields(
    _logger: object, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add static `service` and `version` fields to every log event."""
    event_dict.setdefault("service", "gtex-link")
    event_dict.setdefault("version", _GTEX_LINK_VERSION)
    return event_dict
```

And insert `_add_static_fields` into the `shared_processors` list right before the renderer-selection block.

If `gtex_link/__init__.py` doesn't already expose `__version__`, add it:

```python
"""GTEx-Link package."""

__version__ = "0.2.0"
```

- [ ] **Step 2: Run the logging test**

If no logging-specific test exists, run the observability suite to ensure logs are still emitted:

```bash
uv run pytest tests/test_observability/ -v
```

- [ ] **Step 3: Run the full test suite**

```bash
make test
```
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add gtex_link/logging_config.py gtex_link/__init__.py
git commit -m "feat(logging): add correlation id and service/version fields to structlog"
```

---

## Task 7: Propagate correlation ID and emit upstream metrics in `GTExClient`

**Files:**
- Modify: `gtex_link/api/client.py`

- [ ] **Step 1: Add correlation header on outbound requests**

Open `gtex_link/api/client.py`. Find where the client builds an httpx request (search for `httpx.AsyncClient` or `self._client.request`). Add a small helper at the top of the file:

```python
from asgi_correlation_id import correlation_id as _correlation_id_ctx


def _inject_correlation_header(headers: dict[str, str] | None) -> dict[str, str]:
    """Add the current correlation ID to outbound headers when available."""
    out = dict(headers) if headers else {}
    cid = _correlation_id_ctx.get()
    if cid and "X-Request-ID" not in out:
        out["X-Request-ID"] = cid
    return out
```

Then in every place the client constructs request headers, wrap them:

```python
headers = _inject_correlation_header(headers)
```

If the client uses a default header dict on its `AsyncClient` instance, this can be done once per request rather than at construction time (correlation IDs vary per request).

- [ ] **Step 2: Emit upstream metrics around each request**

Locate the method that issues the actual HTTP call (likely `_request`, `_get`, or similar; in the current code it's around line 100-200 of `client.py`). Wrap the call to capture status and duration:

```python
import time as _time
from gtex_link.observability.metrics import (
    record_rate_limit_wait,
    record_upstream_call,
)

# Inside the request method, after acquiring a rate-limit token:
wait_seconds = await self._rate_limiter.acquire()
if wait_seconds > 0:
    record_rate_limit_wait(wait_s=wait_seconds)

start = _time.perf_counter()
status = 0
try:
    response = await self._client.request(method, url, headers=headers, params=params, json=json_body)
    status = response.status_code
    return response
finally:
    record_upstream_call(
        endpoint=self._endpoint_label(url),
        status=status,
        duration_s=_time.perf_counter() - start,
    )
```

Add a small helper to derive the endpoint label (do not log the full URL with query params, which would explode cardinality):

```python
def _endpoint_label(self, url: str) -> str:
    """Reduce a full URL to a label suitable for a Prometheus counter."""
    # Strip query string, then trim to the last 3 path segments
    from urllib.parse import urlsplit

    path = urlsplit(url).path
    parts = [p for p in path.split("/") if p]
    return "/".join(parts[-3:]) if parts else "unknown"
```

- [ ] **Step 3: Run client tests**

```bash
uv run pytest tests/test_client/ -v
```
Expected: pass. If tests fail because of how the rate-limiter or response is structured, update the test to use the new call shape — but only if the test was previously asserting behavior that's now wrong. Don't suppress real failures.

- [ ] **Step 4: Commit**

```bash
git add gtex_link/api/client.py
git commit -m "feat(client): propagate correlation id and emit upstream metrics"
```

---

## Task 8: Add cache hit/miss metrics in `GTExService`

**Files:**
- Modify: `gtex_link/services/gtex_service.py`

- [ ] **Step 1: Open `gtex_link/services/gtex_service.py` and locate the cache call sites**

The service uses `async_lru` decorators on cached methods. The `async_lru` library does not expose hit/miss hooks directly. Two options:

**Option A — wrap each cache call.** Around each `@alru_cache`-decorated method, expose a thin wrapper that checks the cache info before/after the call:

```python
from async_lru import alru_cache
from gtex_link.observability.metrics import record_cache_event


@alru_cache(maxsize=1000, ttl=3600)
async def _cached_search_genes(self, ...args...): ...


async def search_genes(self, ...args...):
    before = self._cached_search_genes.cache_info()
    result = await self._cached_search_genes(...args...)
    after = self._cached_search_genes.cache_info()
    record_cache_event(cache="search_genes", hit=after.hits > before.hits)
    return result
```

**Option B — wrap with a small helper.** Add a single helper method on the service:

```python
async def _measured(self, name: str, cached_callable, *args, **kwargs):
    before = cached_callable.cache_info()
    result = await cached_callable(*args, **kwargs)
    after = cached_callable.cache_info()
    record_cache_event(cache=name, hit=after.hits > before.hits)
    return result
```

Choose **Option B** for less repetition. Apply to every cached method on the service:

- `search_genes` → cache name `"search_genes"`
- `get_genes` → `"genes"`
- `get_transcripts` → `"transcripts"`
- `get_median_gene_expression` → `"median_gene_expression"`
- `get_gene_expression` → `"gene_expression"`
- `get_top_expressed_genes` → `"top_expressed_genes"`

(Adjust to the actual method names in the file.)

- [ ] **Step 2: Run service tests**

```bash
uv run pytest tests/test_services/ -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add gtex_link/services/gtex_service.py
git commit -m "feat(services): emit cache hit/miss metrics"
```

---

## Task 9: Verify `/metrics` is excluded from MCP route mapping

**Files:**
- Modify: `gtex_link/app.py` (only the `mcp_route_maps` list)

- [ ] **Step 1: Open `gtex_link/app.py` and find `mcp_route_maps`**

Around line 92-100 of the current file. Add an exclusion for `/metrics`:

```python
    mcp_route_maps = [
        RouteMap(pattern=r"^/api/health.*$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/docs$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/openapi.json$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/redoc$", mcp_type=MCPType.EXCLUDE),
        RouteMap(pattern=r"^/metrics$", mcp_type=MCPType.EXCLUDE),
    ]
```

- [ ] **Step 2: Commit**

```bash
git add gtex_link/app.py
git commit -m "fix(mcp): exclude /metrics from MCP route mapping"
```

---

## Task 10: Add `respx` fixture to `tests/conftest.py`

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add a `respx_mock` fixture and a base-URL fixture**

Open `tests/conftest.py`. Add near the top of the file (after the imports block at lines 1-35):

```python
import respx


@pytest.fixture
def respx_mock():
    """Yield a respx router intercepting all httpx calls in the test."""
    with respx.mock(assert_all_called=False) as router:
        yield router


GTEX_BASE = "https://test.gtexportal.org/api/v2"  # matches test_api_config.base_url
```

Note: the existing `test_api_config` fixture sets `base_url="https://test.gtexportal.org/api/v2/"`. The `GTEX_BASE` constant should match this exactly so respx URL patterns line up.

- [ ] **Step 2: Run the suite to verify nothing is broken**

```bash
uv run pytest tests -q
```
Expected: pass (no existing test uses respx yet, so adding the fixture is a no-op for them).

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add respx_mock fixture and GTEX_BASE constant"
```

---

## Task 11: Migrate `tests/test_api/test_reference_routes.py` to respx

**Files:**
- Modify: `tests/test_api/test_reference_routes.py`

- [ ] **Step 1: Identify how the existing tests mock the upstream**

Open the file. Find each test. They likely either:
- Inject a `MagicMock` for `GTExService` via a FastAPI dependency override, OR
- Patch `httpx.AsyncClient` somewhere.

The migration goal: tests hit the real `GTExService` and real `GTExClient`, with respx intercepting outbound HTTPS to `https://test.gtexportal.org/api/v2/reference/...`.

- [ ] **Step 2: For each test, replace the mock setup with respx**

Example before (typical pattern):

```python
@pytest.mark.asyncio
async def test_gene_search(test_client, monkeypatch):
    mock_service = AsyncMock()
    mock_service.search_genes.return_value = GENE_SEARCH_RESPONSE
    monkeypatch.setattr(...)
    response = test_client.get("/api/reference/geneSearch?geneId=BRCA1")
    assert response.status_code == 200
```

Example after:

```python
@pytest.mark.asyncio
async def test_gene_search(async_client, respx_mock):
    respx_mock.get(f"{GTEX_BASE}/reference/geneSearch").respond(
        200, json=GENE_SEARCH_RESPONSE
    )
    response = await async_client.get("/api/reference/geneSearch", params={"geneId": "BRCA1"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"][0]["geneSymbol"] == "BRCA1"
```

Add this import at the top of the file if missing:
```python
from tests.conftest import GTEX_BASE
```
(Or replicate the constant inside the test module.)

- [ ] **Step 3: Run the migrated file**

```bash
uv run pytest tests/test_api/test_reference_routes.py -v
```
Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_api/test_reference_routes.py
git commit -m "test(api): migrate reference route tests to respx"
```

---

## Task 12: Migrate `tests/test_api/test_expression_routes.py` to respx

**Files:**
- Modify: `tests/test_api/test_expression_routes.py`

- [ ] **Step 1: Apply the same migration pattern as Task 11**

For each test in the file, replace mock-based upstream simulation with respx route registrations. Use the canned response payloads already present in `tests/fixtures/gtex_api_responses.py`:

- `MEDIAN_GENE_EXPRESSION_RESPONSE`
- `TOP_EXPRESSED_GENES_RESPONSE`
- (Add fixtures for any endpoints currently mocked but not in the file.)

Example:

```python
@pytest.mark.asyncio
async def test_median_gene_expression(async_client, respx_mock):
    respx_mock.get(f"{GTEX_BASE}/expression/medianGeneExpression").respond(
        200, json=MEDIAN_GENE_EXPRESSION_RESPONSE
    )
    response = await async_client.get(
        "/api/expression/medianGeneExpression",
        params={"gencodeId": "ENSG00000012048.20", "tissueSiteDetailId": "Whole_Blood"},
    )
    assert response.status_code == 200
```

- [ ] **Step 2: Run the migrated file**

```bash
uv run pytest tests/test_api/test_expression_routes.py -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_api/test_expression_routes.py
git commit -m "test(api): migrate expression route tests to respx"
```

---

## Task 13: Migrate `tests/test_api/test_health_routes.py` to respx (if needed)

**Files:**
- Modify: `tests/test_api/test_health_routes.py`

- [ ] **Step 1: Inspect the file**

Health routes may not call upstream. If so, no respx changes are needed. Verify by running:

```bash
uv run pytest tests/test_api/test_health_routes.py -v
```

If the tests pass without changes, skip Step 2.

- [ ] **Step 2: If tests mock httpx, migrate**

Follow the pattern from Task 11 only for tests that actually hit upstream.

- [ ] **Step 3: Commit (only if changes were made)**

```bash
git add tests/test_api/test_health_routes.py
git commit -m "test(api): migrate health route tests to respx"
```

---

## Task 14: Migrate `tests/test_services/` to respx

**Files:**
- Modify: every file under `tests/test_services/`

- [ ] **Step 1: For each file, apply the respx pattern**

Service tests likely instantiate `GTExService(client=GTExClient(...))` and previously mocked the client. Now the client is real and respx intercepts the HTTPS calls.

```python
@pytest.mark.asyncio
async def test_search_genes_caches(gtex_client, respx_mock):
    respx_mock.get(f"{GTEX_BASE}/reference/geneSearch").respond(
        200, json=GENE_SEARCH_RESPONSE
    )
    service = GTExService(client=gtex_client, cache_config=test_cache_config)

    result1 = await service.search_genes(query="BRCA1", page=0, page_size=10)
    result2 = await service.search_genes(query="BRCA1", page=0, page_size=10)

    # Cache hit means only one upstream call
    assert respx_mock.routes[0].call_count == 1
    assert result1 == result2
```

- [ ] **Step 2: Run the directory**

```bash
uv run pytest tests/test_services/ -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_services/
git commit -m "test(services): migrate service tests to respx"
```

---

## Task 15: Migrate `tests/test_client/` to respx

**Files:**
- Modify: every file under `tests/test_client/`

- [ ] **Step 1: For each file, apply respx**

Client tests previously had to monkeypatch `httpx.AsyncClient` internals. Replace with respx routes; the rest of the test stays the same.

```python
@pytest.mark.asyncio
async def test_client_rate_limit_retry(gtex_client, respx_mock):
    respx_mock.get(f"{GTEX_BASE}/reference/gene").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"data": []}),
        ]
    )
    result = await gtex_client.get("reference/gene", params={"geneId": "BRCA1"})
    assert result.status_code == 200
```

- [ ] **Step 2: Run**

```bash
uv run pytest tests/test_client/ -v
```
Expected: pass.

- [ ] **Step 3: Commit**

```bash
git add tests/test_client/
git commit -m "test(client): migrate client tests to respx"
```

---

## Task 16: Delete obsolete hand-rolled mock fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Identify obsolete fixtures**

Open `tests/conftest.py`. Look for fixtures that exist solely to mock upstream HTTP behavior — e.g., a `mock_gtex_client` AsyncMock fixture, or any monkeypatch helpers that overrode httpx internals.

- [ ] **Step 2: Delete each obsolete fixture**

Use `Grep` first to find every test that imports/uses each fixture you intend to delete:

```bash
uv run grep -r "mock_gtex_client" tests/
```

Only remove a fixture once no test references it. If a few stragglers remain, migrate them to respx first.

- [ ] **Step 3: Run the suite**

```bash
make test
```
Expected: pass. If a fixture deletion breaks a test, that test was missed during the route-by-route migration — go back and migrate it.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: remove obsolete hand-rolled httpx mock fixtures"
```

---

## Task 17: Verify `pytest-xdist` parallel execution works

**Files:**
- No file changes (already added in Phase 1)

- [ ] **Step 1: Run the parallel target**

```bash
make test-fast
```
Expected: tests run across multiple workers. The total wall-clock time should be substantially lower than `make test`.

- [ ] **Step 2: If any tests fail under parallel execution**

Likely culprit: tests that share global state (the Prometheus default registry, settings singletons, or shared httpx clients). Fix by either:

- Adding a fixture that resets the global state per test (`autouse=True` cleanup fixture).
- Marking the test as `serial` (using `pytest-xdist`'s `--dist=loadgroup` and a custom group) — but prefer cleanup over serialization.

For Prometheus, the cleanest fix is to use a fresh `CollectorRegistry` per test where collectors are inspected. Update `tests/test_observability/test_metrics.py` if needed.

- [ ] **Step 3: Run `make ci-local`**

```bash
make ci-local
```
Expected: pass.

- [ ] **Step 4: Commit any test-stability fixes**

```bash
git add tests/
git commit -m "test: stabilize tests under pytest-xdist parallel execution"
```

(Skip if no fixes were needed.)

---

## Task 18: Update `CHANGELOG.md`

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Append a Phase 2 section under `[Unreleased]`**

Open `CHANGELOG.md`. Inside the `[Unreleased]` section, append:

```markdown
### Added (Phase 2 — Observability & tests)

- `gtex_link/observability/` package: correlation IDs (asgi-correlation-id), Prometheus collectors, `/metrics` endpoint.
- ASGI middleware: `CorrelationIdMiddleware`, `MetricsMiddleware`.
- Structlog processors: correlation_id, service, version.
- Outbound `X-Request-ID` propagation in `GTExClient`.
- Prometheus collectors: HTTP request count/duration, upstream request count/duration, cache hits/misses, rate-limit waits, MCP tool calls (populated in Phase 3).
- `respx` fixture in `tests/conftest.py`.
- `tests/test_observability/` covering correlation and metrics.

### Changed (Phase 2)

- All HTTP-mocking tests migrated from hand-rolled httpx mocks to `respx`.
- `make test-fast` now runs in parallel via pytest-xdist.

### Removed (Phase 2)

- Obsolete hand-rolled httpx mock fixtures in `tests/conftest.py`.
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add Phase 2 observability and test entries"
```

---

## Task 19: Run `make ci-local` and fix anything that fails

**Files:**
- As needed

- [ ] **Step 1: Run the gate**

```bash
make ci-local
```
Expected: pass.

- [ ] **Step 2: Confirm coverage still meets 90%**

```bash
make test-cov
```
Expected: ≥90% on `gtex_link`. New observability code should also be covered by `tests/test_observability/`.

If coverage dropped below 90%, the most likely uncovered code is in `gtex_link/observability/metrics.py` or the `GTExClient` upstream-metrics path. Add a focused test rather than excluding the file.

---

## Task 20: Push branch and open PR

**Files:**
- No file changes

- [ ] **Step 1: Push the branch**

```bash
git push -u origin phase-2-observability-and-tests
```

- [ ] **Step 2: Open the PR**

```bash
gh pr create --title "Phase 2: Observability + tests" --body "$(cat <<'EOF'
## Summary

- Add `gtex_link/observability/` package with correlation IDs and Prometheus metrics.
- Wire CorrelationIdMiddleware, MetricsMiddleware, and /metrics endpoint into the FastAPI app.
- Propagate inbound correlation IDs as outbound X-Request-ID in GTExClient.
- Emit upstream request, cache hit/miss, and rate-limit wait metrics at the call sites.
- Migrate every HTTP-mocking test from hand-rolled httpx mocks to respx.
- Enable parallel test execution via pytest-xdist (`make test-fast`).

No external API or MCP tool contract changes. The MCP tool counter is in place but only populated by Phase 3.

## Type

- [x] feat: new feature (observability)
- [x] refactor: test infrastructure

## Verification

- [x] `make ci-local` passes locally
- [x] Coverage gate still ≥90%
- [x] New tests under `tests/test_observability/` cover correlation and metrics
- [x] All existing tests pass under `make test-fast` (parallel)
- [x] CHANGELOG.md updated

## Breaking changes

None to the API or MCP surface. New `/metrics` endpoint exposed.
EOF
)"
```

---

## Phase 2 success criteria

- [ ] `/metrics` endpoint returns Prometheus exposition with all defined collectors
- [ ] Structured logs include `correlation_id`, `service=gtex-link`, `version`
- [ ] Inbound `X-Request-ID` echoed on responses; generated when absent
- [ ] `GTExClient` outbound calls carry the inbound correlation ID
- [ ] Every route-level and service-level test uses `respx` instead of hand-rolled mocks
- [ ] `make test-fast` runs in parallel and passes
- [ ] Coverage gate ≥90%
- [ ] CHANGELOG.md updated; no API/MCP contract change
