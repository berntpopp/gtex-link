"""API routes module."""

from .association import router as association_router
from .expression import router as expression_router
from .health import router as health_router
from .reference import router as reference_router

__all__ = [
    "association_router",
    "expression_router",
    "health_router",
    "reference_router",
]
