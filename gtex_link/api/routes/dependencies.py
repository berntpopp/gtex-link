"""FastAPI dependencies for GTEx-Link routes.

This module provides dependency injection for common services
and utilities used across route handlers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Depends

from gtex_link.api.client import GTExClient
from gtex_link.config import get_api_config, get_cache_config, settings
from gtex_link.logging_config import configure_logging
from gtex_link.services.gtex_service import GTExService

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from structlog.typing import FilteringBoundLogger


async def get_gtex_client() -> AsyncGenerator[GTExClient, None]:
    """Dependency to get GTEx client instance.

    Yields:
        GTEx client with proper lifecycle management
    """
    config = get_api_config()
    logger = configure_logging()
    client = GTExClient(config=config, logger=logger)
    try:
        yield client
    finally:
        # GTExClient doesn't need explicit cleanup in current implementation
        # but this provides the pattern for future enhancements
        pass


def get_logger_dependency() -> FilteringBoundLogger:
    """Dependency to get logger instance.

    Returns:
        Structured logger instance
    """
    return configure_logging()


# Type aliases for cleaner route signatures
GTExClientDep = Depends(get_gtex_client)
LoggerDep = Depends(get_logger_dependency)


async def get_gtex_service(
    client: GTExClient = GTExClientDep,
    logger: FilteringBoundLogger = LoggerDep,
) -> GTExService:
    """Dependency to get GTEx service instance.

    Args:
        client: GTEx client dependency
        logger: Logger dependency

    Returns:
        GTEx service instance
    """
    cache_config = get_cache_config()
    return GTExService(
        client=client,
        cache_config=cache_config,
        logger=logger,
    )


GTExServiceDep = Depends(get_gtex_service)
