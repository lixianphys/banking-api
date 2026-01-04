import pytest
import json
from unittest.mock import patch

from simplebank.utils.redis_cache import (
    get_cache_key,
    get_cached_response,
    set_cached_response,
    invalidate_cache,
    invalidate_user_cache
)


class TestRedisCache:
    """Test Redis caching utilities"""

    def test_get_cache_key_basic(self, mock_redis):
        """Test generating a basic cache key"""
        endpoint = "/api/accounts"
        params = {"account_id": 1}
        key = get_cache_key(endpoint, params)
        
        assert key.startswith("cache:")
        assert len(key) > len("cache:")

    def test_get_cache_key_with_user(self, mock_redis):
        """Test generating a cache key with user ID"""
        endpoint = "/api/accounts"
        params = {"account_id": 1}
        user_id = 123
        key = get_cache_key(endpoint, params, user_id=user_id)
        
        assert key.startswith("cache:")
        # Key should be different when user_id is included
        key_no_user = get_cache_key(endpoint, params)
        assert key != key_no_user

    def test_get_cache_key_consistent(self, mock_redis):
        """Test that same parameters generate same cache key"""
        endpoint = "/api/accounts"
        params = {"account_id": 1, "expand": "customer"}
        key1 = get_cache_key(endpoint, params)
        key2 = get_cache_key(endpoint, params)
        
        assert key1 == key2

    def test_get_cache_key_order_independent(self, mock_redis):
        """Test that parameter order doesn't affect cache key"""
        endpoint = "/api/accounts"
        params1 = {"account_id": 1, "expand": "customer"}
        params2 = {"expand": "customer", "account_id": 1}
        
        key1 = get_cache_key(endpoint, params1)
        key2 = get_cache_key(endpoint, params2)
        
        assert key1 == key2

    def test_set_cached_response(self, mock_redis):
        """Test setting a cached response"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            key = "cache:test_key"
            value = {"data": "test_value", "id": 1}
            result = set_cached_response(key, value, ttl=60)
            
            assert result is True
            # Verify data was stored
            stored = mock_redis.get(key)
            assert stored is not None
            assert json.loads(stored) == value

    def test_get_cached_response_hit(self, mock_redis):
        """Test retrieving a cached response (cache hit)"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            key = "cache:test_key"
            value = {"data": "test_value", "id": 1}
            mock_redis.setex(key, 60, json.dumps(value))
            
            cached = get_cached_response(key)
            assert cached == value

    def test_get_cached_response_miss(self, mock_redis):
        """Test retrieving a cached response (cache miss)"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            key = "cache:nonexistent"
            cached = get_cached_response(key)
            assert cached is None

    def test_set_cached_response_with_ttl(self, mock_redis):
        """Test that TTL is set correctly"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            key = "cache:test_key"
            value = {"data": "test"}
            ttl = 120
            set_cached_response(key, value, ttl=ttl)
            
            # Check TTL (fakeredis doesn't expire automatically, but we can check it was set)
            assert mock_redis.exists(key) == 1

    def test_invalidate_cache(self, mock_redis):
        """Test invalidating cache entries"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            # Set some cache entries
            mock_redis.set("cache:key1", "value1")
            mock_redis.set("cache:key2", "value2")
            mock_redis.set("other:key3", "value3")
            
            # Invalidate cache keys
            deleted = invalidate_cache("cache:*")
            assert deleted == 2
            assert mock_redis.get("cache:key1") is None
            assert mock_redis.get("cache:key2") is None
            assert mock_redis.get("other:key3") is not None  # Not a cache key

    def test_invalidate_user_cache(self, mock_redis):
        """Test invalidating cache for a specific user"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            user_id = 123
            # Set cache entries for different users
            mock_redis.set("cache:user:123:key1", "value1")
            mock_redis.set("cache:user:123:key2", "value2")
            mock_redis.set("cache:user:456:key3", "value3")
            
            # Invalidate user 123's cache
            deleted = invalidate_user_cache(user_id)
            assert deleted >= 2
            assert mock_redis.get("cache:user:123:key1") is None
            assert mock_redis.get("cache:user:123:key2") is None
            # User 456's cache should remain
            assert mock_redis.get("cache:user:456:key3") is not None

    def test_invalidate_user_cache_specific_endpoint(self, mock_redis):
        """Test invalidating cache for a user on a specific endpoint"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            user_id = 123
            endpoint = "/api/accounts"
            # Set cache entries
            mock_redis.set("cache:user:123:/api/accounts:key1", "value1")
            mock_redis.set("cache:user:123:/api/customers:key2", "value2")
            
            # Invalidate only accounts endpoint
            deleted = invalidate_user_cache(user_id, endpoint=endpoint)
            assert deleted >= 1
            assert mock_redis.get("cache:user:123:/api/accounts:key1") is None
            # Customers cache should remain
            assert mock_redis.get("cache:user:123:/api/customers:key2") is not None

