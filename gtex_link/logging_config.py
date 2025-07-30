"""Logging configuration for GTEx-Link.

This module sets up structured logging using structlog with appropriate
formatters and handlers for different environments.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.logging import RichHandler
import structlog

from .config import settings

if TYPE_CHECKING:
    from structlog.typing import FilteringBoundLogger


def configure_stdlib_logging() -> None:
    """Configure standard library logging."""
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure handlers based on environment
    is_development = settings.reload or settings.log_level == "DEBUG"
    if is_development:
        # Rich handler for development
        console = Console(stderr=True)
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True,
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
    else:
        # Standard handler for production
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        handler.setFormatter(formatter)

    handler.setLevel(getattr(logging, settings.log_level))
    root_logger.addHandler(handler)

    # Configure specific loggers
    configure_third_party_loggers()


def configure_third_party_loggers() -> None:
    """Configure third-party library loggers."""
    # Reduce verbosity of third-party loggers
    is_debug = settings.log_level == "DEBUG"
    loggers_config = {
        "httpx": "WARNING",
        "httpcore": "WARNING",
        "uvicorn.access": "WARNING" if not is_debug else "INFO",
        "uvicorn.error": "INFO",
        "fastapi": "INFO",
        "fastmcp": "WARNING" if not is_debug else "INFO",
        "mcp": "WARNING" if not is_debug else "INFO",
    }

    for logger_name, level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, level))


def configure_structlog() -> None:
    """Configure structlog for structured logging."""
    # Shared processors
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    is_debug = settings.log_level == "DEBUG"
    if is_debug:
        shared_processors.append(structlog.dev.set_exc_info)

    # Configure processors based on format
    is_development = settings.reload or settings.log_level == "DEBUG"
    if settings.log_format == "json":
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    elif is_development:
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=True)]
    else:
        processors = [*shared_processors, structlog.dev.ConsoleRenderer(colors=False)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging() -> FilteringBoundLogger:
    """Configure complete logging setup and return logger."""
    # Set up stdlib logging first
    configure_stdlib_logging()

    # Then configure structlog
    configure_structlog()

    # Return configured logger
    return structlog.get_logger("gtex_link")


def orjson_serializer(obj: Any) -> str:
    """Fast JSON serializer using orjson."""
    try:
        import orjson

        return orjson.dumps(obj).decode("utf-8")
    except ImportError:
        import json

        return json.dumps(obj, default=str)


def log_api_request(
    logger: FilteringBoundLogger,
    method: str,
    url: str,
    response_time: float,
    status_code: int,
    error: str | None = None,
) -> None:
    """Log API request with structured data."""
    log_data = {
        "method": method,
        "url": url,
        "response_time_ms": round(response_time * 1000, 2),
        "status_code": status_code,
    }

    if error:
        log_data["error"] = error
        logger.error("API request failed", **log_data)
    else:
        logger.info("API request completed", **log_data)


def log_cache_operation(
    logger: FilteringBoundLogger,
    operation: str,
    key: str,
    hit: bool | None = None,
    size: int | None = None,
) -> None:
    """Log cache operation with structured data."""
    log_data = {
        "operation": operation,
        "key": key,
    }

    if hit is not None:
        log_data["cache_hit"] = hit
    if size is not None:
        log_data["cache_size"] = size

    logger.debug("Cache operation", **log_data)


def log_mcp_tool_call(
    logger: FilteringBoundLogger,
    tool_name: str,
    params: dict[str, Any],
    duration: float,
    success: bool,
    error: str | None = None,
) -> None:
    """Log MCP tool call with structured data."""
    log_data = {
        "tool_name": tool_name,
        "params": params,
        "duration_ms": round(duration * 1000, 2),
        "success": success,
    }

    if error:
        log_data["error"] = error
        logger.error("MCP tool call failed", **log_data)
    else:
        logger.info("MCP tool call completed", **log_data)


def log_server_startup(
    logger: FilteringBoundLogger,
    mode: str,
    host: str | None = None,
    port: int | None = None,
) -> None:
    """Log server startup with structured data."""
    log_data = {
        "mode": mode,
    }

    if host and port:
        log_data.update({"host": host, "port": port})

    logger.info("Server starting", **log_data)


def log_error_with_context(
    logger: FilteringBoundLogger,
    error: Exception,
    operation: str,
    context: dict[str, Any] | None = None,
) -> None:
    """Log error with additional context."""
    log_data = {
        "operation": operation,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }

    if context:
        log_data["context"] = context

    logger.error("Operation failed", **log_data, exc_info=True)
