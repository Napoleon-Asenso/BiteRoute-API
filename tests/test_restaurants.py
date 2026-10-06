"""Comprehensive tests for restaurant querying, filtering, sorting, and validation."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_restaurants_pagination_and_envelope(async_client: AsyncClient) -> None:
    """Verify GET /api/v1/restaurants returns uniform collection envelope."""
    response = await async_client.get("/api/v1/restaurants?limit=10&offset=0")
    assert response.status_code == 200

    payload = response.json()
    assert "data" in payload
    assert "meta" in payload
    assert isinstance(payload["data"], list)
    assert len(payload["data"]) <= 10

    meta = payload["meta"]
    assert meta["total"] >= 100
    assert meta["limit"] == 10
    assert meta["offset"] == 0
    assert meta["hasMore"] is True


@pytest.mark.asyncio
async def test_list_restaurants_category_and_cuisine_filtering(
    async_client: AsyncClient,
) -> None:
    """Verify filtering by category / cuisine returns matching records."""
    response = await async_client.get("/api/v1/restaurants?category=Pizza")
    assert response.status_code == 200

    payload = response.json()
    assert len(payload["data"]) > 0
    for r in payload["data"]:
        assert r["category"].lower() == "pizza" or r["cuisine_type"].lower() == "pizza"


@pytest.mark.asyncio
async def test_list_restaurants_sorting(async_client: AsyncClient) -> None:
    """Verify restaurants sorted by name ascending."""
    response = await async_client.get("/api/v1/restaurants?sort=name&order=asc&limit=20")
    assert response.status_code == 200

    payload = response.json()
    names = [r["name"] for r in payload["data"]]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_list_restaurants_defensive_clamping_and_validation(
    async_client: AsyncClient,
) -> None:
    """Verify defensive input clamping errors return HTTP 400 with honest error codes."""
    # Negative offset
    neg_res = await async_client.get("/api/v1/restaurants?offset=-1")
    assert neg_res.status_code == 400
    assert neg_res.json()["error"]["code"] == "BAD_REQUEST"

    # Limit > 100 clamped to 100
    over_res = await async_client.get("/api/v1/restaurants?limit=500")
    assert over_res.status_code == 200
    assert over_res.json()["meta"]["limit"] == 100

    # Limit < 1 clamped to 1
    under_res = await async_client.get("/api/v1/restaurants?limit=0")
    assert under_res.status_code == 200
    assert under_res.json()["meta"]["limit"] == 1

    # Invalid sort field
    sort_res = await async_client.get("/api/v1/restaurants?sort=unsupported_field")
    assert sort_res.status_code == 400
    assert sort_res.json()["error"]["code"] == "INVALID_SORT_FIELD"

    # Invalid sort order
    order_res = await async_client.get("/api/v1/restaurants?order=upside_down")
    assert order_res.status_code == 400
    assert order_res.json()["error"]["code"] == "INVALID_SORT_ORDER"


@pytest.mark.asyncio
async def test_get_restaurant_by_id_and_not_found(async_client: AsyncClient) -> None:
    """Verify fetching restaurant by ID and 404 / 400 edge cases."""
    # Fetch list first to obtain a valid UUID
    list_res = await async_client.get("/api/v1/restaurants?limit=1")
    valid_id = list_res.json()["data"][0]["id"]

    # Success case
    detail_res = await async_client.get(f"/api/v1/restaurants/{valid_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["data"]["id"] == valid_id

    # Not found case (valid UUID syntax, but nonexistent)
    missing_id = "00000000-0000-0000-0000-000000000000"
    not_found_res = await async_client.get(f"/api/v1/restaurants/{missing_id}")
    assert not_found_res.status_code == 404
    assert not_found_res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Malformed UUID (invalid UUID syntax returns 400 MALFORMED_IDENTIFIER)
    malformed_res = await async_client.get("/api/v1/restaurants/invalid-uuid-123")
    assert malformed_res.status_code == 400
    assert malformed_res.json()["error"]["code"] == "MALFORMED_IDENTIFIER"


@pytest.mark.asyncio
async def test_get_restaurant_menu(async_client: AsyncClient) -> None:
    """Verify retrieving menu items for a restaurant."""
    list_res = await async_client.get("/api/v1/restaurants?limit=1")
    valid_id = list_res.json()["data"][0]["id"]

    menu_res = await async_client.get(f"/api/v1/restaurants/{valid_id}/menu")
    assert menu_res.status_code == 200

    items = menu_res.json()["data"]
    assert len(items) > 0
    for it in items:
        assert it["restaurant_id"] == valid_id
        assert it["price"] > 0
