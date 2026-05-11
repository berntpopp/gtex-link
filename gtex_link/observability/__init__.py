"""Observability — correlation IDs, structured logs, Prometheus metrics."""

from gtex_link.observability.correlation import (
    bind_correlation_id_processor,
    install_correlation_middleware,
)
from gtex_link.observability.metrics import (
    install_metrics_middleware,
    install_metrics_route,
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
