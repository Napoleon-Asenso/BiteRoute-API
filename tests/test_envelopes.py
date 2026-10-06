"""Tests for uniform error envelope shape and status code translation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_not_found_returns_uniform_error_envelope(async_client: AsyncClient) -> None:
    """Verify that accessing a non-existent route returns standard ErrorEnvelope."""
    response = await async_client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404

    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert isinstance(payload["error"]["message"], str)
    assert len(payload["error"]["message"]) > 0

    # Ensure raw FastAPI detail is never leaked
    assert "detail" not in payload


@pytest.mark.asyncio
async def test_method_not_allowed_returns_uniform_error_envelope(
    async_client: AsyncClient,
) -> None:
    """Verify that invoking an unsupported HTTP verb returns standard ErrorEnvelope."""
    response = await async_client.post("/health")
    assert response.status_code == 405

    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert isinstance(payload["error"]["message"], str)
    assert len(payload["error"]["message"]) > 0

    assert "detail" not in payload
