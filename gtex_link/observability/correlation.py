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
        validator=None,
    )


def bind_correlation_id_processor(
    _logger: Any, _name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor that binds the current correlation ID into log events."""
    cid = correlation_id.get()
    if cid:
        event_dict["correlation_id"] = cid
    return event_dict
