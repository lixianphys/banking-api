import json
from typing import Optional
import logging

from simplebank.utils.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def add_to_blacklist(token: str, expires_in: int) -> bool:
    """
    Add a JWT token to the blacklist.
    
    Args:
        token: JWT token string
        expires_in: Time in seconds until token expires (used as TTL)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        key = f"blacklist:{token}"
        # Store token with TTL matching expiration
        redis_client.setex(key, expires_in, "1")
        return True
    except Exception as e:
        logger.error(f"Error adding token to blacklist: {e}")
        return False


def is_token_blacklisted(token: str) -> bool:
    """
    Check if a JWT token is blacklisted.
    
    Args:
        token: JWT token string
    
    Returns:
        True if token is blacklisted, False otherwise
    """
    try:
        redis_client = get_redis_client()
        key = f"blacklist:{token}"
        result = redis_client.get(key)
        return result is not None
    except Exception as e:
        logger.error(f"Error checking token blacklist: {e}")
        # On error, don't block the request (fail open)
        return False


def store_refresh_token(user_id: int, token: str, expires_in: int) -> bool:
    """
    Store a refresh token in Redis.
    
    Args:
        user_id: User ID
        token: Refresh token string
        expires_in: Time in seconds until token expires (used as TTL)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        key = f"refresh_token:{user_id}:{token}"
        # Store token with TTL matching expiration
        redis_client.setex(key, expires_in, json.dumps({"user_id": user_id, "token": token}))
        return True
    except Exception as e:
        logger.error(f"Error storing refresh token: {e}")
        return False


def get_refresh_token(user_id: int, token: str) -> Optional[dict]:
    """
    Validate and retrieve a refresh token from Redis.
    
    Args:
        user_id: User ID
        token: Refresh token string
    
    Returns:
        Token data if valid, None otherwise
    """
    try:
        redis_client = get_redis_client()
        key = f"refresh_token:{user_id}:{token}"
        result = redis_client.get(key)
        
        if result is None:
            return None
        
        return json.loads(result)
    except Exception as e:
        logger.error(f"Error getting refresh token: {e}")
        return None


def revoke_refresh_token(user_id: int, token: str) -> bool:
    """
    Revoke a refresh token by deleting it from Redis.
    
    Args:
        user_id: User ID
        token: Refresh token string
    
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        key = f"refresh_token:{user_id}:{token}"
        redis_client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Error revoking refresh token: {e}")
        return False


def revoke_all_user_refresh_tokens(user_id: int) -> int:
    """
    Revoke all refresh tokens for a user.
    
    Args:
        user_id: User ID
    
    Returns:
        Number of tokens revoked
    """
    try:
        redis_client = get_redis_client()
        pattern = f"refresh_token:{user_id}:*"
        keys = redis_client.keys(pattern)
        
        if not keys:
            return 0
        
        return redis_client.delete(*keys)
    except Exception as e:
        logger.error(f"Error revoking all user refresh tokens: {e}")
        return 0

