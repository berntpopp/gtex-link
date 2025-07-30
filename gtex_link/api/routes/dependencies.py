"""Dependency injection for FastAPI routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from structlog.typing import FilteringBoundLogger

from gtex_link.api.client import GTExClient
from gtex_link.config import get_api_config, get_cache_config
from gtex_link.logging_config import configure_logging
from gtex_link.services.gtex_service import GTExService


def get_logger() -> FilteringBoundLogger:
    """Get configured logger instance."""
    return configure_logging()


async def get_gtex_client(
    logger: Annotated[FilteringBoundLogger, Depends(get_logger)],
) -> GTExClient:
    """Get GTEx Portal API client instance."""
    config = get_api_config()
    client = GTExClient(config=config, logger=logger)
    return client


def get_gtex_service(
    client: Annotated[GTExClient, Depends(get_gtex_client)],
    logger: Annotated[FilteringBoundLogger, Depends(get_logger)],
) -> GTExService:
    """Get GTEx service instance."""
    cache_config = get_cache_config()
    return GTExService(
        client=client,
        cache_config=cache_config,
        logger=logger,
    )


# Type aliases for clean dependency injection
LoggerDep = Annotated[FilteringBoundLogger, Depends(get_logger)]
ClientDep = Annotated[GTExClient, Depends(get_gtex_client)]
ServiceDep = Annotated[GTExService, Depends(get_gtex_service)]
