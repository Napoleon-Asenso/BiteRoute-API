"""Tests for client IP rate limiting middleware, quota exhaustion, and header assertions."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_headers_on_all_responses(async_client: AsyncClient) -> None:
    """Ensure compliance headers are present on regular endpoints."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "100"


@pytest.mark.asyncio
async def test_health_check_exempt_from_quota_decrement(async_client: AsyncClient) -> None:
    """Ensure /api/v1/health never exhausts quota even with repeated requests."""
    for _ in range(105):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_quota_exhaustion_returns_429(async_client: AsyncClient) -> None:
    """Verify that exceeding quota on non-exempt endpoint triggers HTTP 429 with Retry-After."""
    headers = {"X-Forwarded-For": "198.51.100.42"}

    # Exhaust the 100 requests quota on a 404 test endpoint
    for _ in range(100):
        res = await async_client.get("/api/v1/dummy-endpoint", headers=headers)
        assert res.status_code == 404

    # 101st request must trigger 429 RATE_LIMIT_EXCEEDED
    blocked = await async_client.get("/api/v1/dummy-endpoint", headers=headers)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert blocked.headers["X-RateLimit-Remaining"] == "0"

    payload = blocked.json()
    assert "error" in payload
    assert payload["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert "Too many requests. Please wait" in payload["error"]["message"]
