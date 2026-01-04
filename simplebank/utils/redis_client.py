import os
import redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global Redis client instance (singleton pattern)
redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance (singleton pattern).
    Uses environment variables for configuration.
    """
    global redis_client
    
    if redis_client is not None:
        return redis_client
    
    # Get configuration from environment variables
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    password = os.getenv("REDIS_PASSWORD", None)
    db = int(os.getenv("REDIS_DB", "0"))
    
    try:
        redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            db=db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        # Test connection
        redis_client.ping()
        logger.info(f"Connected to Redis at {host}:{port}")
        return redis_client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client is not None:
        try:
            redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
        finally:
            redis_client = None

