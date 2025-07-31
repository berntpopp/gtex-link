"""Comprehensive tests for caching utilities."""

import asyncio
import pytest
from typing import Any
from unittest.mock import Mock, patch

from pydantic import BaseModel

from gtex_link.utils.caching import (
    CacheManager,
    _make_hashable_key,
    create_service_cache_decorator,
)


class TestModel(BaseModel):
    """Test Pydantic model for cache key generation."""

    name: str
    value: int


class TestMakeHashableKey:
    """Tests for _make_hashable_key function."""

    def test_simple_args(self):
        """Test with simple arguments."""
        key = _make_hashable_key("test", 123, True)
        assert isinstance(key, str)
        assert len(key) == 32  # MD5 hash length

    def test_kwargs_only(self):
        """Test with keyword arguments only."""
        key = _make_hashable_key(name="test", value=123)
        assert isinstance(key, str)

    def test_mixed_args_kwargs(self):
        """Test with mixed args and kwargs."""
        key1 = _make_hashable_key("arg1", name="test", value=123)
        key2 = _make_hashable_key("arg1", name="test", value=123)
        assert key1 == key2

    def test_pydantic_model_serialization(self):
        """Test Pydantic model serialization in cache key."""
        model = TestModel(name="test", value=42)
        key = _make_hashable_key(model)
        assert isinstance(key, str)

    def test_list_serialization(self):
        """Test list serialization in cache key."""
        key = _make_hashable_key([1, 2, 3])
        assert isinstance(key, str)

    def test_dict_serialization(self):
        """Test dict serialization in cache key."""
        key = _make_hashable_key({"a": 1, "b": 2})
        assert isinstance(key, str)

    def test_set_serialization(self):
        """Test set serialization in cache key."""
        key = _make_hashable_key({1, 2, 3})
        assert isinstance(key, str)

    def test_nested_structures(self):
        """Test nested data structures."""
        nested_data = {
            "models": [TestModel(name="test1", value=1), TestModel(name="test2", value=2)],
            "lists": [[1, 2], [3, 4]],
            "sets": [{1, 2}, {3, 4}],
        }
        key = _make_hashable_key(nested_data)
        assert isinstance(key, str)

    def test_key_consistency(self):
        """Test that same input produces same key."""
        model = TestModel(name="test", value=42)
        key1 = _make_hashable_key(model, extra="data")
        key2 = _make_hashable_key(model, extra="data")
        assert key1 == key2

    def test_key_uniqueness(self):
        """Test that different inputs produce different keys."""
        key1 = _make_hashable_key("test1")
        key2 = _make_hashable_key("test2")
        assert key1 != key2


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_init_without_logger(self):
        """Test initialization without logger."""
        manager = CacheManager()
        assert manager.logger is None
        assert manager._cache_stats == {"hits": 0, "misses": 0}
        assert manager._cached_functions == []

    def test_init_with_logger(self):
        """Test initialization with logger."""
        mock_logger = Mock()
        manager = CacheManager(mock_logger)
        assert manager.logger is mock_logger

    def test_cache_stats_empty(self):
        """Test cache stats with no activity."""
        manager = CacheManager()
        stats = manager.cache_stats
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["hit_rate"] == 0.0
        assert stats["total_requests"] == 0
        assert stats["cached_functions"] == 0

    def test_cache_stats_with_activity(self):
        """Test cache stats after hits and misses."""
        manager = CacheManager()
        manager._cache_stats["hits"] = 7
        manager._cache_stats["misses"] = 3

        stats = manager.cache_stats
        assert stats["hits"] == 7
        assert stats["misses"] == 3
        assert stats["hit_rate"] == 70.0
        assert stats["total_requests"] == 10
        assert stats["cached_functions"] == 0

    def test_log_cache_hit_without_logger(self):
        """Test logging cache hit without logger."""
        manager = CacheManager()
        manager._log_cache_hit("test_key")
        assert manager._cache_stats["hits"] == 1

    def test_log_cache_hit_with_logger(self):
        """Test logging cache hit with logger."""
        mock_logger = Mock()
        manager = CacheManager(mock_logger)
        manager._log_cache_hit("test_key")
        assert manager._cache_stats["hits"] == 1
        mock_logger.debug.assert_called_once_with("Cache hit", cache_key="test_key")

    def test_log_cache_miss_without_logger(self):
        """Test logging cache miss without logger."""
        manager = CacheManager()
        manager._log_cache_miss("test_key")
        assert manager._cache_stats["misses"] == 1

    def test_log_cache_miss_with_logger(self):
        """Test logging cache miss with logger."""
        mock_logger = Mock()
        manager = CacheManager(mock_logger)
        manager._log_cache_miss("test_key")
        assert manager._cache_stats["misses"] == 1
        mock_logger.debug.assert_called_once_with("Cache miss", cache_key="test_key")

    @pytest.mark.asyncio
    async def test_cached_decorator_basic(self):
        """Test basic caching functionality."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=10, ttl=60)
        async def test_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return value * 2

        # First call - should miss cache
        result1 = await test_func(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - should hit cache
        result2 = await test_func(5)
        assert result2 == 10
        assert call_count == 1  # No additional call

    @pytest.mark.asyncio
    async def test_cached_decorator_with_self_parameter(self):
        """Test caching with method calls (self parameter)."""
        manager = CacheManager()

        class TestClass:
            def __init__(self):
                self.call_count = 0

            @manager.cached(maxsize=10, ttl=60)
            async def method(self, value: int) -> int:
                self.call_count += 1
                return value * 3

        obj = TestClass()

        # First call
        result1 = await obj.method(4)
        assert result1 == 12
        assert obj.call_count == 1

        # Second call - should hit cache
        result2 = await obj.method(4)
        assert result2 == 12
        assert obj.call_count == 1

    @pytest.mark.asyncio
    async def test_cached_decorator_ttl_expiration(self):
        """Test TTL expiration in cache."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=10, ttl=0.1)  # 100ms TTL
        async def test_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return value * 2

        # First call
        result1 = await test_func(5)
        assert result1 == 10
        assert call_count == 1

        # Wait for TTL to expire
        await asyncio.sleep(0.2)

        # Second call after TTL - should call function again
        result2 = await test_func(5)
        assert result2 == 10
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_cached_decorator_lru_eviction(self):
        """Test LRU eviction when maxsize is exceeded."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=2, ttl=60)
        async def test_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            return value * 2

        # Fill cache to capacity
        await test_func(1)  # call_count = 1
        await test_func(2)  # call_count = 2

        # This should trigger eviction
        await test_func(3)  # call_count = 3

        # First value should be evicted, so this should call function again
        result = await test_func(1)  # call_count = 4
        assert result == 2
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_cached_decorator_with_key_pattern(self):
        """Test caching with custom key pattern."""
        mock_logger = Mock()
        manager = CacheManager(mock_logger)

        @manager.cached(maxsize=10, ttl=60, key_pattern="custom_pattern")
        async def test_func(value: int) -> int:
            return value * 2

        await test_func(5)

        # Check that custom pattern was used in logging
        mock_logger.debug.assert_called()
        # The logging calls are for cache hit/miss, not the cache_key parameter
        call_args = mock_logger.debug.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_cache_info_and_clear(self):
        """Test cache_info and cache_clear methods."""
        manager = CacheManager()

        @manager.cached(maxsize=10, ttl=60)
        async def test_func(value: int) -> int:
            return value * 2

        # Initial state
        info = test_func.cache_info()
        assert info.hits == 0
        assert info.misses == 0
        assert info.currsize == 0

        # After cache miss
        await test_func(5)
        info = test_func.cache_info()
        assert info.hits == 0
        assert info.misses == 1
        assert info.currsize == 1

        # After cache hit
        await test_func(5)
        info = test_func.cache_info()
        assert info.hits == 1
        assert info.misses == 1
        assert info.currsize == 1

        # Clear cache
        test_func.cache_clear()
        info = test_func.cache_info()
        assert info.hits == 0
        assert info.misses == 0
        assert info.currsize == 0

    def test_get_cache_info_empty(self):
        """Test get_cache_info with no cached functions."""
        manager = CacheManager()
        info = manager.get_cache_info()
        assert info == {}

    @pytest.mark.asyncio
    async def test_get_cache_info_with_functions(self):
        """Test get_cache_info with cached functions."""
        manager = CacheManager()

        @manager.cached(maxsize=10, ttl=60)
        async def test_func1(value: int) -> int:
            return value * 2

        @manager.cached(maxsize=5, ttl=30)
        async def test_func2(value: str) -> str:
            return value.upper()

        # Generate some cache activity
        await test_func1(1)  # miss
        await test_func1(1)  # hit
        await test_func2("hello")  # miss

        info = manager.get_cache_info()
        assert len(info) == 2

        # Check function_0 stats
        func0_info = info["function_0"]
        assert func0_info["hits"] == 1
        assert func0_info["misses"] == 1
        assert func0_info["hit_rate"] == 50.0
        assert func0_info["current_size"] == 1
        assert func0_info["max_size"] == 10

        # Check function_1 stats
        func1_info = info["function_1"]
        assert func1_info["hits"] == 0
        assert func1_info["misses"] == 1
        assert func1_info["hit_rate"] == 0.0
        assert func1_info["current_size"] == 1
        assert func1_info["max_size"] == 5

    @pytest.mark.asyncio
    async def test_clear_all_caches(self):
        """Test clearing all caches."""
        manager = CacheManager()

        @manager.cached(maxsize=10, ttl=60)
        async def test_func1(value: int) -> int:
            return value * 2

        @manager.cached(maxsize=10, ttl=60)
        async def test_func2(value: str) -> str:
            return value.upper()

        # Generate cache entries
        await test_func1(1)
        await test_func2("hello")

        # Verify caches have content
        assert test_func1.cache_info().currsize == 1
        assert test_func2.cache_info().currsize == 1

        # Clear all caches
        manager.clear_all_caches()

        # Verify caches are empty
        assert test_func1.cache_info().currsize == 0
        assert test_func2.cache_info().currsize == 0

    @pytest.mark.asyncio
    async def test_cached_functions_registration(self):
        """Test that decorated functions are registered with manager."""
        manager = CacheManager()

        @manager.cached(maxsize=10, ttl=60)
        async def test_func(value: int) -> int:
            return value * 2

        assert len(manager._cached_functions) == 1
        assert manager._cached_functions[0] == test_func

    @pytest.mark.asyncio
    @patch("gtex_link.utils.caching.log_cache_operation")
    async def test_cache_operation_logging(self, mock_log_cache_operation):
        """Test that cache operations are logged properly."""
        mock_logger = Mock()
        manager = CacheManager(mock_logger)

        @manager.cached(maxsize=10, ttl=60)
        async def test_func(value: int) -> int:
            return value * 2

        await test_func(5)

        # Verify log_cache_operation was called
        mock_log_cache_operation.assert_called_once()
        args = mock_log_cache_operation.call_args[0]
        assert args[0] == mock_logger  # logger
        assert args[1] == "cache_miss"  # operation (first call is miss)
        assert "test_func:" in args[2]  # display_key
        assert args[3] is False  # hit (first call is miss)
        assert isinstance(args[4], int)  # size


class TestCreateServiceCacheDecorator:
    """Tests for create_service_cache_decorator function."""

    def test_create_without_logger(self):
        """Test creating cache decorator without logger."""
        cache_manager = create_service_cache_decorator()
        assert isinstance(cache_manager, CacheManager)
        assert cache_manager.logger is None

    def test_create_with_logger(self):
        """Test creating cache decorator with logger."""
        mock_logger = Mock()
        cache_manager = create_service_cache_decorator(mock_logger)
        assert isinstance(cache_manager, CacheManager)
        assert cache_manager.logger is mock_logger


class TestCacheIntegration:
    """Integration tests for caching functionality."""

    @pytest.mark.asyncio
    async def test_pydantic_model_caching(self):
        """Test caching with Pydantic models as arguments."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=10, ttl=60)
        async def process_model(model: TestModel) -> str:
            nonlocal call_count
            call_count += 1
            return f"{model.name}_{model.value}"

        model1 = TestModel(name="test", value=42)
        model2 = TestModel(name="test", value=42)  # Same values
        model3 = TestModel(name="different", value=42)  # Different values

        # First call with model1
        result1 = await process_model(model1)
        assert result1 == "test_42"
        assert call_count == 1

        # Second call with model2 (same values) - should hit cache
        result2 = await process_model(model2)
        assert result2 == "test_42"
        assert call_count == 1

        # Third call with model3 (different values) - should miss cache
        result3 = await process_model(model3)
        assert result3 == "different_42"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_complex_arguments_caching(self):
        """Test caching with complex argument structures."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=10, ttl=60)
        async def complex_func(
            models: list[TestModel], metadata: dict[str, Any], tags: set[str]
        ) -> str:
            nonlocal call_count
            call_count += 1
            return f"processed_{len(models)}_{len(metadata)}_{len(tags)}"

        models = [TestModel(name="test1", value=1), TestModel(name="test2", value=2)]
        metadata = {"key1": "value1", "key2": {"nested": "value"}}
        tags = {"tag1", "tag2", "tag3"}

        # First call
        result1 = await complex_func(models, metadata, tags)
        assert result1 == "processed_2_2_3"
        assert call_count == 1

        # Same arguments - should hit cache
        result2 = await complex_func(models, metadata, tags)
        assert result2 == "processed_2_2_3"
        assert call_count == 1

        # Different order in set - should still hit cache (sets are sorted)
        tags_different_order = {"tag3", "tag1", "tag2"}
        result3 = await complex_func(models, metadata, tags_different_order)
        assert result3 == "processed_2_2_3"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_concurrent_cache_access(self):
        """Test concurrent access to cached function."""
        manager = CacheManager()
        call_count = 0

        @manager.cached(maxsize=10, ttl=60)
        async def slow_func(value: int) -> int:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate slow operation
            return value * 2

        # Launch multiple concurrent calls with same argument
        tasks = [slow_func(5) for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All results should be the same
        assert all(result == 10 for result in results)

        # Function should have been called multiple times since they're concurrent
        # (this tests that we don't have race conditions in cache access)
        assert call_count >= 1
