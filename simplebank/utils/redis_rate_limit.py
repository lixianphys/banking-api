import time
from typing import Optional
import logging

from simplebank.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def check_rate_limit_redis(
    identifier: str,
    max_requests: int = 60,
    window: int = 60
) -> bool:
    """
    Check if a request is within rate limits using Redis.
    
    Uses a sliding window algorithm with Redis.
    
    Args:
        identifier: Unique identifier (e.g., IP address, user_id)
        max_requests: Maximum number of requests allowed
        window: Time window in seconds
    
    Returns:
        True if within rate limit, False if rate limit exceeded
    """
    try:
        redis_client = get_redis_client()
        key = f"rate_limit:{identifier}"
        now = time.time()
        
        # Remove old entries outside the window
        redis_client.zremrangebyscore(key, 0, now - window)
        
        # Count current requests in window
        current_count = redis_client.zcard(key)
        
        if current_count >= max_requests:
            logger.warning(f"Rate limit exceeded for {identifier}: {current_count}/{max_requests}")
            return False
        
        # Add current request
        redis_client.zadd(key, {str(now): now})
        # Set expiration on the key (window + 1 second buffer)
        redis_client.expire(key, window + 1)
        
        return True
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        # On error, allow the request (fail open)
        return True

