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
