from fastapi import Request, Response, HTTPException, Header, status
import os
import time
import secrets
from typing import Dict, Optional
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_KEY = os.getenv("API_KEY", "default_secret_key")

# Simple in-memory rate limiting
rate_limits: Dict[str, Dict[float, int]] = {}  # {ip: {timestamp: count}}
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "60"))
RATE_LIMIT_WINDOW = 60  # Window in seconds

# Standard security headers to prevent XSS attacks and cache attacks
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache"
}

def check_rate_limit(ip: str) -> bool:
    """Check if IP is within rate limits"""
    now = time.time()
    
    # Initialize if this is the first request from this IP
    if ip not in rate_limits:
        rate_limits[ip] = {}
    
    # Clean up old entries (older than window)
    rate_limits[ip] = {ts: count for ts, count in rate_limits[ip].items() 
                      if now - ts < RATE_LIMIT_WINDOW}
    
    # Calculate total requests in current window
    total_requests = sum(rate_limits[ip].values())
    
    # Check if limit exceeded
    if total_requests >= RATE_LIMIT_MAX:
        return False
    
    # Record this request
    if now not in rate_limits[ip]:
        rate_limits[ip][now] = 0
    rate_limits[ip][now] += 1
    
    return True


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """Dependency for API key verification"""
    # Skip for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return None
        
    # Verify API key
    if not x_api_key or x_api_key != API_KEY:
        # Get client IP safely
        client_ip = getattr(request.client, 'host', '127.0.0.1')
        logger.warning(f"Invalid API key attempt from {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Check rate limits - handle None client safely
    client_ip = getattr(request.client, 'host', '127.0.0.1')
    if not check_rate_limit(client_ip):
        logger.warning(f"Rate limit exceeded for {client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded, please try again later",
        )
    
    # Store start time for timing requests
    request.state.start_time = time.time()
    
    return x_api_key

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

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
        # Get the start time stored by verify_api_key
        start_time = getattr(request.state, "start_time", time.time())
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log the request
        log_request(request, self.operation_name, response.status_code, duration)
        
        # Add security headers
        await add_security_headers(response)
        
        return True 