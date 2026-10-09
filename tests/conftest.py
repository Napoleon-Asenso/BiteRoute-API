"""Pytest configuration and shared asynchronous fixtures."""

from collections.abc import AsyncGenerator
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import async_engine
from app.main import app


@pytest_asyncio.fixture(loop_scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an asynchronous HTTP client configured for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    await async_engine.dispose()
