"""Centralized caching utilities and decorators."""

from __future__ import annotations

import functools
import hashlib
import json
import time
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from pydantic import BaseModel

from gtex_link.logging_config import log_cache_operation

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from structlog.typing import FilteringBoundLogger

# Type variables for generic function signatures
P = TypeVar("P")
R = TypeVar("R")


def _make_hashable_key(*args: Any, **kwargs: Any) -> str:
    """Create a hashable key from arguments including Pydantic models."""

    def _serialize_value(value: Any) -> Any:
        """Convert unhashable values to hashable representations."""
        if isinstance(value, BaseModel):
            # Convert Pydantic model to sorted dict representation
            return (
                "__pydantic__",
                value.__class__.__name__,
                tuple(sorted(value.model_dump().items())),
            )
        if isinstance(value, list):
            return ("__list__", tuple(_serialize_value(item) for item in value))
        if isinstance(value, dict):
            return (
                "__dict__",
                tuple(sorted((_serialize_value(k), _serialize_value(v)) for k, v in value.items())),
            )
        if isinstance(value, set):
            return ("__set__", tuple(sorted(_serialize_value(item) for item in value)))
        return value

    # Serialize all arguments and keyword arguments
    serialized_args = tuple(_serialize_value(arg) for arg in args)
    serialized_kwargs = tuple(sorted((k, _serialize_value(v)) for k, v in kwargs.items()))

    # Create a JSON representation and hash it
    key_data = {"args": serialized_args, "kwargs": serialized_kwargs}
    key_json = json.dumps(key_data, sort_keys=True, default=str)

    # Create a shorter hash for use as cache key
    return hashlib.md5(key_json.encode()).hexdigest()


class CacheManager:
    """Centralized cache management with statistics tracking."""

    def __init__(self, logger: FilteringBoundLogger | None = None) -> None:
        """Initialize cache manager.

        Args:
            logger: Optional logger for cache operations
        """
        self.logger = logger
        self._cache_stats = {"hits": 0, "misses": 0}
        self._cached_functions: list[Any] = []

    @property
    def cache_stats(self) -> dict[str, Any]:
        """Get comprehensive cache statistics."""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = self._cache_stats["hits"] / total_requests if total_requests > 0 else 0.0

        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": hit_rate * 100.0,  # Convert to percentage
            "total_requests": total_requests,
            "cached_functions": len(self._cached_functions),
        }

    def _log_cache_hit(self, key: str) -> None:
        """Log cache hit."""
        self._cache_stats["hits"] += 1
        if self.logger:
            self.logger.debug("Cache hit", cache_key=key)

    def _log_cache_miss(self, key: str) -> None:
        """Log cache miss."""
        self._cache_stats["misses"] += 1
        if self.logger:
            self.logger.debug("Cache miss", cache_key=key)

    def cached(
        self,
        maxsize: int = 128,
        ttl: int = 3600,
        key_pattern: str | None = None,
    ) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Awaitable[R]]]:
        """Create a caching decorator with custom key generation for Pydantic models.

        Args:
            maxsize: Maximum number of cached items
            ttl: Time-to-live in seconds
            key_pattern: Optional pattern for cache key generation

        Returns:
            Decorated function with caching capabilities
        """

        def decorator(func: Callable[..., Awaitable[R]]) -> Callable[..., Awaitable[R]]:
            cache_dict: dict[str, tuple[R, float]] = {}
            hits = 0
            misses = 0

            @functools.wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> R:
                nonlocal hits, misses

                # Skip 'self' parameter for method calls
                if args and hasattr(args[0], func.__name__):
                    cache_args = args[1:]  # Skip 'self'
                else:
                    cache_args = args

                # Create a hashable key from the arguments
                hash_key = _make_hashable_key(*cache_args, **kwargs)

                # Generate cache key for logging
                if key_pattern:
                    display_key = f"{key_pattern}:{hash_key[:8]}..."  # Show first 8 chars of hash
                else:
                    display_key = f"{func.__name__}:{hash_key[:8]}..."

                start_time = time.time()
                was_cache_hit = False

                # Check if we have a cached result
                if hash_key in cache_dict:
                    result, timestamp = cache_dict[hash_key]
                    if time.time() - timestamp < ttl:
                        was_cache_hit = True
                        hits += 1
                    else:
                        # TTL expired, remove from cache
                        del cache_dict[hash_key]
                        misses += 1
                        result = await func(*args, **kwargs)
                        cache_dict[hash_key] = (result, time.time())
                else:
                    # Not in cache, compute result
                    misses += 1
                    result = await func(*args, **kwargs)
                    cache_dict[hash_key] = (result, time.time())

                # Implement LRU eviction if cache is too large
                if len(cache_dict) > maxsize:
                    # Remove oldest entries
                    sorted_items = sorted(cache_dict.items(), key=lambda x: x[1][1])
                    for old_key, _ in sorted_items[: len(cache_dict) - maxsize]:
                        del cache_dict[old_key]

                # Log cache operation
                if was_cache_hit:
                    self._log_cache_hit(display_key)
                else:
                    self._log_cache_miss(display_key)

                # Log performance metrics
                cache_info_current = type(
                    "CacheInfo",
                    (),
                    {
                        "hits": hits,
                        "misses": misses,
                        "maxsize": maxsize,
                        "currsize": len(cache_dict),
                    },
                )()

                log_cache_operation(
                    self.logger,
                    was_cache_hit,
                    display_key,
                    cache_info_current,
                    time.time() - start_time,
                )

                return result

            # Add cache info method with actual stats
            def cache_info():
                return type(
                    "CacheInfo",
                    (),
                    {
                        "hits": hits,
                        "misses": misses,
                        "maxsize": maxsize,
                        "currsize": len(cache_dict),
                    },
                )()

            def cache_clear():
                nonlocal hits, misses
                cache_dict.clear()
                hits = 0
                misses = 0

            wrapper.cache_info = cache_info  # type: ignore
            wrapper.cache_clear = cache_clear  # type: ignore

            self._cached_functions.append(wrapper)
            return wrapper

        return decorator

    def get_cache_info(self) -> dict[str, dict[str, Any]]:
        """Get cache information for all cached functions."""
        cache_info = {}
        for i, func in enumerate(self._cached_functions):
            if hasattr(func, "cache_info"):
                info = func.cache_info()
                cache_info[f"function_{i}"] = {
                    "hits": info.hits,
                    "misses": info.misses,
                    "current_size": info.currsize,
                    "max_size": info.maxsize,
                    "hit_rate": (
                        (info.hits / (info.hits + info.misses) * 100.0)
                        if (info.hits + info.misses) > 0
                        else 0.0
                    ),
                }
        return cache_info

    def clear_all_caches(self) -> None:
        """Clear all cached functions."""
        for func in self._cached_functions:
            if hasattr(func, "cache_clear"):
                func.cache_clear()


def create_service_cache_decorator(logger: FilteringBoundLogger | None = None) -> CacheManager:
    """Create a cache manager instance for service-level caching.

    Args:
        logger: Optional logger for cache operations

    Returns:
        Configured cache manager instance
    """
    return CacheManager(logger)
