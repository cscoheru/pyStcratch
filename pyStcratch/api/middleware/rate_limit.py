"""
Rate limiting middleware (basic implementation).
"""
from fastapi import Request, Response, HTTPException
from loguru import logger
from collections import defaultdict
import time


# Simple in-memory rate limiter (for production, use Redis)
class RateLimiter:
    """Simple rate limiter using in-memory storage."""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed."""
        now = time.time()
        minute_ago = now - 60

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > minute_ago
        ]

        # Check if under limit
        if len(self.requests[client_id]) < self.requests_per_minute:
            self.requests[client_id].append(now)
            return True

        return False


# Global rate limiter instance
_rate_limiter = RateLimiter(requests_per_minute=60)


async def rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting to requests."""

    # Get client identifier
    client_id = request.client.host if request.client else "unknown"

    # Skip rate limiting for health checks
    if request.url.path in ["/health", "/api/system/health", "/docs", "/redoc", "/"]:
        return await call_next(request)

    # Check rate limit
    if not _rate_limiter.is_allowed(client_id):
        logger.warning(f"Rate limit exceeded for {client_id}")
        return Response(
            content='{"success": false, "error": "Rate limit exceeded"}',
            status_code=429,
            media_type="application/json"
        )

    return await call_next(request)
