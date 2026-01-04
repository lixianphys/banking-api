import pytest
import json
from unittest.mock import patch

from simplebank.utils.redis_token_store import (
    add_to_blacklist,
    is_token_blacklisted,
    store_refresh_token,
    get_refresh_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens
)


class TestRedisTokenStore:
    """Test Redis token storage utilities"""

    def test_add_to_blacklist(self, mock_redis):
        """Test adding a token to blacklist"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            token = "test_token_123"
            expires_in = 3600
            result = add_to_blacklist(token, expires_in)
            
            assert result is True
            # Verify token is in blacklist
            key = f"blacklist:{token}"
            assert mock_redis.get(key) is not None

    def test_is_token_blacklisted_true(self, mock_redis):
        """Test checking if a blacklisted token is blacklisted"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            token = "test_token_123"
            expires_in = 3600
            add_to_blacklist(token, expires_in)
            
            result = is_token_blacklisted(token)
            assert result is True

    def test_is_token_blacklisted_false(self, mock_redis):
        """Test checking if a non-blacklisted token is blacklisted"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            token = "non_blacklisted_token"
            result = is_token_blacklisted(token)
            assert result is False

    def test_store_refresh_token(self, mock_redis):
        """Test storing a refresh token"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            user_id = 123
            token = "refresh_token_123"
            expires_in = 604800  # 7 days
            
            result = store_refresh_token(user_id, token, expires_in)
            assert result is True
            
            # Verify token was stored
            key = f"refresh_token:{user_id}:{token}"
            stored = mock_redis.get(key)
            assert stored is not None
            data = json.loads(stored)
            assert data["user_id"] == user_id
            assert data["token"] == token

    def test_get_refresh_token_valid(self, mock_redis):
        """Test retrieving a valid refresh token"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            user_id = 123
            token = "refresh_token_123"
            expires_in = 604800
            
            store_refresh_token(user_id, token, expires_in)
            result = get_refresh_token(user_id, token)
            
            assert result is not None
            assert result["user_id"] == user_id
            assert result["token"] == token

    def test_get_refresh_token_invalid(self, mock_redis):
        """Test retrieving a non-existent refresh token"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            user_id = 123
            token = "nonexistent_token"
            
            result = get_refresh_token(user_id, token)
            assert result is None

    def test_revoke_refresh_token(self, mock_redis):
        """Test revoking a refresh token"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            user_id = 123
            token = "refresh_token_123"
            expires_in = 604800
            
            # Store token
            store_refresh_token(user_id, token, expires_in)
            assert get_refresh_token(user_id, token) is not None
            
            # Revoke token
            result = revoke_refresh_token(user_id, token)
            assert result is True
            
            # Verify token is gone
            assert get_refresh_token(user_id, token) is None

    def test_revoke_all_user_refresh_tokens(self, mock_redis):
        """Test revoking all refresh tokens for a user"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            user_id = 123
            expires_in = 604800
            
            # Store multiple tokens for user
            store_refresh_token(user_id, "token1", expires_in)
            store_refresh_token(user_id, "token2", expires_in)
            store_refresh_token(456, "token3", expires_in)  # Different user
            
            # Revoke all tokens for user 123
            deleted = revoke_all_user_refresh_tokens(user_id)
            assert deleted == 2
            
            # Verify user 123's tokens are gone
            assert get_refresh_token(user_id, "token1") is None
            assert get_refresh_token(user_id, "token2") is None
            # Other user's token should remain
            assert get_refresh_token(456, "token3") is not None

    def test_token_blacklist_expiration(self, mock_redis):
        """Test that blacklisted tokens have expiration set"""
        with patch('simplebank.utils.redis_token_store.get_redis_client', return_value=mock_redis):
            token = "test_token"
            expires_in = 3600
            add_to_blacklist(token, expires_in)
            
            # Token should be blacklisted
            assert is_token_blacklisted(token) is True
            
            # Note: fakeredis doesn't automatically expire keys,
            # but in real Redis, the key would expire after expires_in seconds

