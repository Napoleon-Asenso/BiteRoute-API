"""Rate limiting and CORS middleware implementations."""

import time
from collections.abc import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings


class ClientRateLimitRecord:
    """Tracking container for timestamps and activity of a client IP."""

    def __init__(self, current_time: float) -> None:
        self.timestamps: list[float] = []
        self.last_seen: float = current_time


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """In-memory sliding window rate limiter keyed per client IP address."""

    def __init__(self, app: Callable[..., Response]) -> None:
        super().__init__(app)
        self.records: dict[str, ClientRateLimitRecord] = {}

    def _get_client_ip(self, request: Request) -> str:
        """Extract leftmost client IP from X-Forwarded-For header or fallback to host."""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take leftmost IP address
            return forwarded_for.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    def _prune_inactive(self, now: float) -> None:
        """Evict client records that have been inactive longer than TTL."""
        expired_ips = [
            ip
            for ip, rec in self.records.items()
            if (now - rec.last_seen) > settings.RATE_LIMIT_INACTIVE_TTL_SECONDS
        ]
        for ip in expired_ips:
            del self.records[ip]

    async def dispatch(self, request: Request, call_next: Callable[..., Response]) -> Response:
        """Process incoming request, enforcing rate quota and attaching compliance headers."""
        now = time.time()
        self._prune_inactive(now)

        client_ip = self._get_client_ip(request)
        if client_ip not in self.records:
            self.records[client_ip] = ClientRateLimitRecord(now)
        record = self.records[client_ip]
        record.last_seen = now

        # Prune request timestamps outside current sliding window
        window_cutoff = now - settings.RATE_LIMIT_WINDOW_SECONDS
        record.timestamps = [ts for ts in record.timestamps if ts > window_cutoff]

        # GET /api/v1/health and /health are exempt from rate limit quota enforcement
        is_exempt = request.method == "GET" and request.url.path in (
            "/api/v1/health",
            "/health",
        )

        remaining = max(0, settings.RATE_LIMIT_REQUESTS - len(record.timestamps))
        reset_epoch = (
            int(record.timestamps[0] + settings.RATE_LIMIT_WINDOW_SECONDS)
            if record.timestamps
            else int(now + settings.RATE_LIMIT_WINDOW_SECONDS)
        )

        if not is_exempt:
            if len(record.timestamps) >= settings.RATE_LIMIT_REQUESTS:
                retry_after = max(1, int(reset_epoch - now))
                content = {
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": (
                            f"Too many requests. Please wait {retry_after} seconds before retrying."
                        ),
                    }
                }
                headers = {
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(settings.RATE_LIMIT_REQUESTS),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_epoch),
                }
                return JSONResponse(status_code=429, content=content, headers=headers)

            record.timestamps.append(now)
            remaining = max(0, settings.RATE_LIMIT_REQUESTS - len(record.timestamps))
            reset_epoch = int(record.timestamps[0] + settings.RATE_LIMIT_WINDOW_SECONDS)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_epoch)
        return response
