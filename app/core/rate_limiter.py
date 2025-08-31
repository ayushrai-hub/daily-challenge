"""
Rate limiter middleware for the Daily Challenge API.
Uses Redis to store rate limit counters and slowapi for implementation.
"""
from fastapi import Request, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Callable, Optional
import redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger()

# Initialize Redis client
try:
    # Use settings for Redis configuration
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        socket_connect_timeout=1,  # Short timeout for startup
    )
    # Test Redis connection
    redis_client.ping()
    redis_available = True
    logger.info(f"Redis connection established at {settings.REDIS_HOST}:{settings.REDIS_PORT}, rate limiting enabled")
except (redis.ConnectionError, redis.exceptions.ConnectionError) as e:
    redis_available = False
    redis_client = None
    logger.warning(f"Redis connection failed, rate limiting disabled: {str(e)}")

# Define a custom key function that can be used when Redis is not available
def get_key_func(request: Request) -> str:
    """
    Key generator function for rate limiting.
    Falls back to IP address if X-Forwarded-For header is not present.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get the client's real IP when behind a proxy
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)

# Configure the rate limiter
limiter = Limiter(
    key_func=get_key_func,
    storage_uri=settings.REDIS_URL if redis_available else "memory://",
    default_limits=[settings.RATE_LIMIT_DEFAULT],
)

# Rate limit decorators for specific routes
def rate_limit(
    limit_value: str, key_func: Optional[Callable] = None
):
    """
    Decorator for rate limiting specific routes.
    
    Args:
        limit_value: Rate limit string in format "number/time_period" (e.g., "5/minute")
        key_func: Optional function to determine the rate limit key
        
    Returns:
        Rate limit decorator
    """
    if not redis_available:
        logger.warning(f"Rate limiting requested but Redis unavailable, using in-memory storage")
        
    # Use the provided key_func or the default one
    actual_key_func = key_func or get_key_func
    
    return limiter.limit(
        limit_value,
        key_func=actual_key_func,
    )
