"""Observability — correlation IDs, structured logs, Prometheus metrics."""

from gtex_link.observability.correlation import (
    bind_correlation_id_processor,
    install_correlation_middleware,
)

__all__ = [
    "bind_correlation_id_processor",
    "install_correlation_middleware",
]
