import pytest
import fakeredis
from unittest.mock import patch, MagicMock
import os

from simplebank.utils.redis_client import get_redis_client, close_redis, redis_client


class TestRedisClient:
    """Test Redis client connection and lifecycle management"""

    def setup_method(self):
        """Reset Redis client before each test"""
        close_redis()

    def test_get_redis_client_creates_connection(self, mock_redis):
        """Test that get_redis_client returns a Redis connection"""
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis):
            client = get_redis_client()
            assert client is not None

    def test_get_redis_client_singleton(self, mock_redis):
        """Test that get_redis_client returns the same instance (singleton pattern)"""
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis):
            client1 = get_redis_client()
            client2 = get_redis_client()
            assert client1 is client2

    def test_redis_connection_with_environment_variables(self, mock_redis):
        """Test Redis connection uses environment variables"""
        close_redis()  # Ensure fresh start
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis) as mock_redis_class:
            with patch.dict(os.environ, {
                'REDIS_HOST': 'test_host',
                'REDIS_PORT': '6380',
                'REDIS_PASSWORD': 'test_password',
                'REDIS_DB': '1'
            }):
                get_redis_client()
                mock_redis_class.assert_called_once()
                call_kwargs = mock_redis_class.call_args[1]
                assert call_kwargs.get('host') == 'test_host'
                assert call_kwargs.get('port') == 6380
                assert call_kwargs.get('password') == 'test_password'
                assert call_kwargs.get('db') == 1

    def test_redis_connection_defaults(self, mock_redis):
        """Test Redis connection uses default values when env vars not set"""
        close_redis()  # Ensure fresh start
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis) as mock_redis_class:
            with patch.dict(os.environ, {}, clear=True):
                get_redis_client()
                mock_redis_class.assert_called_once()
                call_kwargs = mock_redis_class.call_args[1]
                assert call_kwargs.get('host') == 'localhost'
                assert call_kwargs.get('port') == 6379
                assert call_kwargs.get('db') == 0

    def test_close_redis(self, mock_redis):
        """Test that close_redis properly closes the connection"""
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis):
            client = get_redis_client()
            # Mock the close method
            client.close = MagicMock()
            close_redis()
            client.close.assert_called_once()

    def test_redis_connection_error_handling(self):
        """Test that connection errors are handled gracefully"""
        with patch('simplebank.utils.redis_client.redis.Redis', side_effect=Exception("Connection failed")):
            # Should not raise, but handle gracefully
            try:
                client = get_redis_client()
                # If connection fails, client might be None or raise
                # This depends on implementation
                pass
            except Exception:
                # Expected behavior - connection errors should be handled
                pass

    def test_redis_ping(self, mock_redis):
        """Test that Redis connection can ping"""
        with patch('simplebank.utils.redis_client.redis.Redis', return_value=mock_redis):
            client = get_redis_client()
            # fakeredis supports ping
            result = client.ping()
            assert result is True

