import json
import hashlib
from typing import Optional, Any, Dict
from datetime import datetime
import logging

from simplebank.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class APIJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle datetime objects and Pydantic models"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if hasattr(obj, 'model_dump'):  # Pydantic v2 models
            return obj.model_dump()
        if hasattr(obj, 'dict'):  # Pydantic v1 models
            return obj.dict()
        return super().default(obj)


def get_cache_key(endpoint: str, params: Dict[str, Any], user_id: Optional[int] = None) -> str:
    """
    Generate a cache key from endpoint and parameters.
    
    Args:
        endpoint: API endpoint path
        params: Query parameters or other identifying parameters
        user_id: Optional user ID to include in cache key for user-specific caching
    
    Returns:
        Cache key string
    """
    # Sort params for consistent key generation
    sorted_params = json.dumps(params, sort_keys=True)
    
    # Include user_id in key if provided
    key_parts = [endpoint]
    if user_id is not None:
        key_parts.append(f"user:{user_id}")
    key_parts.append(sorted_params)
    
    # Create hash of the key parts
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"cache:{key_hash}"


def get_cached_response(key: str) -> Optional[Any]:
    """
    Retrieve a cached response from Redis.
    
    Args:
        key: Cache key
    
    Returns:
        Cached data if found, None otherwise
    """
    try:
        redis_client = get_redis_client()
        cached_data = redis_client.get(key)
        
        if cached_data is None:
            return None
        
        # Deserialize JSON data
        return json.loads(cached_data)
    except Exception as e:
        logger.error(f"Error retrieving cache: {e}")
        return None


def set_cached_response(key: str, value: Any, ttl: int = 60) -> bool:
    """
    Store a response in Redis cache.
    
    Args:
        key: Cache key
        value: Data to cache (must be JSON serializable)
        ttl: Time to live in seconds (default: 60)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        # Serialize data to JSON using custom encoder for datetime and Pydantic models
        serialized_data = json.dumps(value, cls=APIJSONEncoder)
        redis_client.setex(key, ttl, serialized_data)
        return True
    except Exception as e:
        logger.error(f"Error setting cache: {e}")
        return False


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: Redis key pattern (e.g., "cache:account:*")
    
    Returns:
        Number of keys deleted
    """
    try:
        redis_client = get_redis_client()
        keys = redis_client.keys(pattern)
        
        if not keys:
            return 0
        
        return redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        return 0


def invalidate_user_cache(user_id: int, endpoint: Optional[str] = None) -> int:
    """
    Invalidate cache for a specific user.
    
    Args:
        user_id: User ID
        endpoint: Optional endpoint to limit invalidation to specific endpoint
    
    Returns:
        Number of keys deleted
    """
    if endpoint:
        pattern = f"cache:*user:{user_id}*{endpoint}*"
    else:
        pattern = f"cache:*user:{user_id}*"
    
    return invalidate_cache(pattern)

