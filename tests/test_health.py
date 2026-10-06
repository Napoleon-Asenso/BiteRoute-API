"""Tests for health probe endpoints and rate limit compliance headers."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /health returns expected structure with null meta."""
    response = await async_client.get("/health")
    assert response.status_code == 200

    payload = response.json()
    assert "data" in payload
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["service"] == "BiteRoute API"
    assert payload.get("meta") is None

    # Assert standard rate limit headers are attached
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


@pytest.mark.asyncio
async def test_api_v1_health_endpoint(async_client: AsyncClient) -> None:
    """Verify GET /api/v1/health adheres to canonical PRD contract."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert "data" in payload
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["version"] == "1.0.0"

    # Assert standard rate limit headers are attached
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
