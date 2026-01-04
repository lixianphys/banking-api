import pytest
import time
from unittest.mock import patch

from simplebank.utils.redis_rate_limit import check_rate_limit_redis


class TestRedisRateLimit:
    """Test Redis-based rate limiting"""

    def test_rate_limit_within_limit(self, mock_redis):
        """Test that requests within limit are allowed"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            identifier = "127.0.0.1"
            max_requests = 10
            window = 60
            
            # Make requests up to the limit
            for i in range(max_requests):
                result = check_rate_limit_redis(identifier, max_requests, window)
                assert result is True

    def test_rate_limit_exceeded(self, mock_redis):
        """Test that requests exceeding limit are blocked"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            identifier = "127.0.0.1"
            max_requests = 5
            window = 60
            
            # Make requests up to the limit
            for i in range(max_requests):
                result = check_rate_limit_redis(identifier, max_requests, window)
                assert result is True
            
            # Next request should be blocked
            result = check_rate_limit_redis(identifier, max_requests, window)
            assert result is False

    def test_rate_limit_different_identifiers(self, mock_redis):
        """Test that rate limits are per identifier"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            max_requests = 5
            window = 60
            
            # Exceed limit for identifier 1
            for i in range(max_requests + 1):
                result = check_rate_limit_redis("identifier1", max_requests, window)
                if i < max_requests:
                    assert result is True
                else:
                    assert result is False
            
            # Identifier 2 should still be within limit
            result = check_rate_limit_redis("identifier2", max_requests, window)
            assert result is True

    def test_rate_limit_sliding_window(self, mock_redis):
        """Test that rate limit uses sliding window"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            identifier = "127.0.0.1"
            max_requests = 3
            window = 2  # 2 second window for testing
            
            # Make requests up to limit
            for i in range(max_requests):
                result = check_rate_limit_redis(identifier, max_requests, window)
                assert result is True
            
            # Should be blocked
            result = check_rate_limit_redis(identifier, max_requests, window)
            assert result is False
            
            # Wait for window to pass
            time.sleep(window + 0.1)
            
            # Should be allowed again
            result = check_rate_limit_redis(identifier, max_requests, window)
            assert result is True

    def test_rate_limit_defaults(self, mock_redis):
        """Test rate limit with default parameters"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            identifier = "127.0.0.1"
            result = check_rate_limit_redis(identifier)
            assert result is True

    def test_rate_limit_custom_parameters(self, mock_redis):
        """Test rate limit with custom parameters"""
        with patch('simplebank.utils.redis_rate_limit.get_redis_client', return_value=mock_redis):
            identifier = "127.0.0.1"
            max_requests = 2
            window = 10
            
            # Should allow first 2 requests
            assert check_rate_limit_redis(identifier, max_requests, window) is True
            assert check_rate_limit_redis(identifier, max_requests, window) is True
            # Third should be blocked
            assert check_rate_limit_redis(identifier, max_requests, window) is False

