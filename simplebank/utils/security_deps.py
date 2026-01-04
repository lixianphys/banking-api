from fastapi import Request, Response, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import time
from typing import Optional
import logging
from sqlalchemy.orm import Session

from simplebank.database import get_db
from simplebank.utils.jwt_utils import get_current_user
from simplebank.utils.redis_token_store import is_token_blacklisted
from simplebank.utils.redis_rate_limit import check_rate_limit_redis
from simplebank.models.models import User

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_WINDOW = 60  # Window in seconds

security = HTTPBearer()

# Standard security headers to prevent XSS attacks and cache attacks
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache"
}

def check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limits using Redis"""
    return check_rate_limit_redis(ip, max_requests=RATE_LIMIT_MAX, window=RATE_LIMIT_WINDOW)


async def verify_jwt_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency for JWT token verification.
    Returns User if token is valid, raises HTTPException otherwise.
    """
    # Skip for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    
    # Check if token is blacklisted
    if is_token_blacklisted(token):
        logger.warning("Blacklisted token attempted access")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify token and get user
    user = get_current_user(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check rate limits using user ID or IP
    identifier = f"user:{user.id}" if user else getattr(request.client, 'host', '127.0.0.1')
    if not check_rate_limit_redis(identifier):
        logger.warning(f"Rate limit exceeded for {identifier}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded, please try again later",
        )
    
    # Store start time for timing requests
    request.state.start_time = time.time()
    
    return user

def log_request(request: Request, operation: str, status_code: int, duration: float) -> None:
    """Log request details for security audit"""
    logger.info(
        f"{operation}: {request.method} {request.url.path} - "
        f"Status: {status_code} - "
        f"Client: {getattr(request.client, 'host', '127.0.0.1')} - "
        f"Duration: {duration:.4f}s"
    )

async def add_security_headers(response: Response) -> None:
    """Add security headers to response"""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value

class SecurityAudit:
    """Dependency class for logging and securing operations"""
    
    def __init__(self, operation_name: str = "API"):
        self.operation_name = operation_name
        
    async def __call__(self, request: Request, response: Response):
        # Get the start time stored by verify_jwt_token
        start_time = getattr(request.state, "start_time", time.time())
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the request
        log_request(request, self.operation_name, response.status_code, duration)
        
        # Add security headers
        await add_security_headers(response)
        
        return True 