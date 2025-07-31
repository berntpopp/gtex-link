"""Health check endpoints for GTEx-Link."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter
import httpx

from gtex_link.config import settings
from gtex_link.models.responses import HealthResponse

from .dependencies import LoggerDep, GTExClientDep

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger

    from gtex_link.api.client import GTExClient

router = APIRouter(prefix="/api", tags=["health"])

# Track server start time for uptime calculation
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    client: GTExClient = GTExClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> HealthResponse:
    """Health check for the GTEx-Link service."""
    # Check GTEx API health
    gtex_status = "available"
    overall_status = "healthy"
    try:
        await client.get_service_info()
    except (httpx.HTTPError, asyncio.TimeoutError) as e:
        logger.warning("GTEx API health check failed", error=str(e))
        gtex_status = "unavailable"
        overall_status = "degraded"

    uptime = time.time() - _start_time
    cache_status = "enabled" if settings.cache.stats_enabled else "disabled"

    logger.info(
        "Health check completed",
        overall_status=overall_status,
        gtex_status=gtex_status,
    )

    return HealthResponse(
        status=overall_status,
        version="0.1.0",
        gtex_api=gtex_status,
        cache=cache_status,
        uptime_seconds=uptime,
    )


@router.get("/version")
async def version_info() -> dict[str, Any]:
    """Get version information."""
    return {
        "version": "0.1.0",
        "api_version": "v1",
        "gtex_api": settings.api.base_url,
    }
