import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import logging

from simplebank.models.models import User
from simplebank.models.schemas import TokenData

logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_in_production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7"))


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing data to encode in the token (e.g., {"sub": username, "user_id": user_id})
        expires_delta: Optional custom expiration time. If not provided, uses ACCESS_TOKEN_EXPIRE_MINUTES
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        data: Dictionary containing data to encode in the token (e.g., {"sub": username, "user_id": user_id})
    
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Optional[TokenData]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string to verify
        token_type: Expected token type ("access" or "refresh")
    
    Returns:
        TokenData if token is valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verify token type
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch. Expected {token_type}, got {payload.get('type')}")
            return None
        
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if username is None:
            return None
        
        token_data = TokenData(username=username, user_id=user_id)
        return token_data
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        return None


def get_current_user(token: str, db: Session) -> Optional[User]:
    """
    Get the current user from a JWT token.
    
    Args:
        token: JWT access token
        db: Database session
    
    Returns:
        User object if token is valid and user exists, None otherwise
    """
    token_data = verify_token(token, token_type="access")
    if token_data is None:
        return None
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        logger.warning(f"User not found: {token_data.username}")
        return None
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {token_data.username}")
        return None
    
    return user

