"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def get_client_ip(request: Request) -> str:
    """Extract client IP address from X-Forwarded-For header or fallback to socket host."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


limiter: Limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[settings.RATE_LIMIT],
)
