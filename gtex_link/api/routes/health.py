"""Health check and service status routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from gtex_link.exceptions import GTExAPIError
from gtex_link.models import ErrorResponse

from .dependencies import LoggerDep, ServiceDep

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get(
    "/",
    summary="Health check",
    description="Basic health check endpoint to verify service is running.",
    operation_id="health_check",
    response_model=dict[str, str],
    responses={
        200: {"description": "Service is healthy"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def health_check() -> dict[str, str]:
    """Check service health status."""
    return {"status": "healthy", "service": "gtex-link"}


@router.get(
    "/ready",
    summary="Readiness check",
    description=(
        "Check if service is ready to handle requests by testing GTEx Portal API connectivity."
    ),
    operation_id="readiness_check",
    response_model=dict[str, Any],
    responses={
        200: {"description": "Service is ready to handle requests"},
        503: {
            "description": "Service not ready - GTEx Portal API unavailable",
            "model": ErrorResponse,
        },
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def readiness_check(
    service: ServiceDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Readiness check with GTEx Portal API connectivity test."""
    try:
        # Test GTEx Portal API connectivity
        service_info = await service.get_service_info()

        logger.info("Readiness check passed", service_info=service_info.model_dump())

        return {
            "status": "ready",
            "service": "gtex-link",
            "gtex_api": "connected",
            "gtex_service_info": service_info.model_dump(),
        }
    except GTExAPIError as e:
        logger.exception("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "service": "gtex-link",
                "gtex_api": "disconnected",
                "error": str(e),
            },
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during readiness check", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "service": "gtex-link",
                "error": "Internal server error",
            },
        ) from e


@router.get(
    "/stats",
    summary="Service statistics",
    description="Get service performance statistics including cache and API client metrics.",
    operation_id="service_statistics",
    response_model=dict[str, Any],
    responses={
        200: {"description": "Service statistics retrieved successfully"},
        500: {"description": "Failed to retrieve service statistics", "model": ErrorResponse},
    },
)
async def service_stats(
    service: ServiceDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Get service statistics."""
    try:
        cache_stats = service.cache_stats
        client_stats = service.client_stats
        cache_info = service.get_cache_info()

        logger.debug("Retrieved service statistics")

    except Exception as e:
        logger.exception("Error retrieving service statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve service statistics",
        ) from e
    else:
        return {
            "cache": {
                "global_stats": cache_stats,
                "function_stats": cache_info,
            },
            "client": client_stats,
        }
