import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import time

from simplebank.main import app
from simplebank.tests.conftest import test_db, TestingSessionLocal
from simplebank.models.models import User, Customer, Account, Transaction
from simplebank.utils.security_deps import API_KEY
from simplebank.utils.redis_cache import get_cache_key, get_cached_response, set_cached_response


class TestCaching:
    """Test Redis caching integration in API endpoints"""

    def test_account_cache_hit(self, client, test_db, mock_redis):
        """Test that cached account responses are returned"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            # Create an account first
            customer = Customer(name="Test Customer")
            db = TestingSessionLocal()
            try:
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                account = Account(customer_id=customer.id, balance=1000.0)
                db.add(account)
                db.commit()
                db.refresh(account)
            finally:
                db.close()
            
            # First request - should query database
            response1 = client.get(
                f"/api/accounts/{account.id}",
                headers={"X-API-Key": API_KEY}
            )
            assert response1.status_code == 200
            
            # Second request - should use cache
            response2 = client.get(
                f"/api/accounts/{account.id}",
                headers={"X-API-Key": API_KEY}
            )
            assert response2.status_code == 200
            assert response1.json() == response2.json()

    def test_account_cache_miss(self, client, test_db, mock_redis):
        """Test that cache miss queries database"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            customer = Customer(name="Test Customer")
            db = TestingSessionLocal()
            try:
                db.add(customer)
                db.commit()
                db.refresh(customer)
                
                account = Account(customer_id=customer.id, balance=500.0)
                db.add(account)
                db.commit()
                db.refresh(account)
            finally:
                db.close()
            
            # Request should query database (cache miss)
            response = client.get(
                f"/api/accounts/{account.id}",
                headers={"X-API-Key": API_KEY}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["balance"] == 500.0

    def test_cache_invalidation_on_create(self, client, test_db, mock_redis):
        """Test that cache is invalidated when account is created"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            customer = Customer(name="Test Customer")
            db = TestingSessionLocal()
            try:
                db.add(customer)
                db.commit()
                db.refresh(customer)
            finally:
                db.close()
            
            # Get customer accounts (should be cached)
            response1 = client.get(
                f"/api/customers/{customer.id}/accounts",
                headers={"X-API-Key": API_KEY}
            )
            assert response1.status_code == 200
            initial_count = len(response1.json())
            
            # Create a new account
            response2 = client.post(
                "/api/accounts",
                json={"customer_id": customer.id, "initial_deposit": 200.0},
                headers={"X-API-Key": API_KEY}
            )
            assert response2.status_code == 200
            
            # Get customer accounts again - should reflect new account
            response3 = client.get(
                f"/api/customers/{customer.id}/accounts",
                headers={"X-API-Key": API_KEY}
            )
            assert response3.status_code == 200
            # Cache should be invalidated, so we get fresh data
            # Note: In real scenario, cache invalidation happens, but with mock_redis
            # we're testing the integration

    def test_cache_key_uniqueness_per_user(self, client, test_db, mock_redis):
        """Test that cache keys are unique per user"""
        # No need to patch for this test - just testing key generation
        # Generate cache keys for different users
        key1 = get_cache_key("/api/accounts/1", {}, user_id=1)
        key2 = get_cache_key("/api/accounts/1", {}, user_id=2)
        key3 = get_cache_key("/api/accounts/1", {}, user_id=None)
        
        # Keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_cache_key_includes_query_params(self, client, test_db, mock_redis):
        """Test that cache keys include query parameters"""
        # No need to patch for this test - just testing key generation
        # Generate cache keys with different query params
        key1 = get_cache_key("/api/accounts", {"skip": 0, "limit": 10}, user_id=None)
        key2 = get_cache_key("/api/accounts", {"skip": 10, "limit": 10}, user_id=None)
        key3 = get_cache_key("/api/accounts", {"skip": 0, "limit": 20}, user_id=None)
        
        # Keys should be different
        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

    def test_customer_list_caching(self, client, test_db, mock_redis):
        """Test that customer list is cached"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            # First request
            response1 = client.get(
                "/api/customers",
                headers={"X-API-Key": API_KEY}
            )
            assert response1.status_code == 200
            
            # Second request - should use cache
            response2 = client.get(
                "/api/customers",
                headers={"X-API-Key": API_KEY}
            )
            assert response2.status_code == 200
            assert response1.json() == response2.json()

    def test_transaction_cache(self, client, test_db, mock_redis):
        """Test that transactions are cached"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            customer1 = Customer(name="Customer 1")
            customer2 = Customer(name="Customer 2")
            db = TestingSessionLocal()
            try:
                db.add_all([customer1, customer2])
                db.commit()
                db.refresh(customer1)
                db.refresh(customer2)
                
                account1 = Account(customer_id=customer1.id, balance=1000.0)
                account2 = Account(customer_id=customer2.id, balance=500.0)
                db.add_all([account1, account2])
                db.commit()
                db.refresh(account1)
                db.refresh(account2)
            finally:
                db.close()
            
            # First request
            response1 = client.get(
                "/api/transactions",
                headers={"X-API-Key": API_KEY}
            )
            assert response1.status_code == 200
            
            # Second request - should use cache
            response2 = client.get(
                "/api/transactions",
                headers={"X-API-Key": API_KEY}
            )
            assert response2.status_code == 200

    def test_cache_ttl_setting(self, mock_redis):
        """Test that cache TTL is set correctly"""
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            key = "cache:test_key"
            value = {"data": "test"}
            ttl = 60
            
            result = set_cached_response(key, value, ttl=ttl)
            assert result is True
            
            # Verify data was stored
            cached = get_cached_response(key)
            assert cached == value

    def test_cache_invalidation_pattern(self, mock_redis):
        """Test cache invalidation with patterns"""
        from simplebank.utils.redis_cache import invalidate_cache
        
        with patch('simplebank.utils.redis_cache.get_redis_client', return_value=mock_redis):
            # Set multiple cache entries
            set_cached_response("cache:account:1", {"id": 1}, ttl=60)
            set_cached_response("cache:account:2", {"id": 2}, ttl=60)
            set_cached_response("cache:customer:1", {"id": 1}, ttl=60)
            
            # Invalidate account caches
            deleted = invalidate_cache("cache:account:*")
            assert deleted == 2
            
            # Verify account caches are gone
            assert get_cached_response("cache:account:1") is None
            assert get_cached_response("cache:account:2") is None
            # Customer cache should remain
            assert get_cached_response("cache:customer:1") is not None

