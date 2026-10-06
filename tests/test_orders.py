"""Comprehensive tests for atomic order calculation, snapshotting, and lifecycle transitions."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_order_creation_atomic_pricing_engine(async_client: AsyncClient) -> None:
    """Verify order placement, tax calculation, and atomic pricing accuracy."""
    # 1. Fetch an active restaurant
    res_list = await async_client.get("/api/v1/restaurants?limit=1&is_active=true")
    restaurant = res_list.json()["data"][0]
    rest_id = restaurant["id"]
    delivery_fee = restaurant["delivery_fee_cents"]

    # 2. Fetch menu items for this restaurant
    menu_res = await async_client.get(f"/api/v1/restaurants/{rest_id}/menu")
    items = menu_res.json()["data"]
    assert len(items) >= 2
    item1 = items[0]
    item2 = items[1]

    # 3. Submit Order payload
    payload = {
        "restaurant_id": rest_id,
        "customer_name": "Alice Tester",
        "customer_email": "alice@example.com",
        "customer_phone": "+1-415-555-0123",
        "delivery_address": "789 Howard St, San Francisco, CA 94103",
        "special_instructions": "Leave at apartment door.",
        "items": [
            {"menu_item_id": item1["id"], "quantity": 2},
            {"menu_item_id": item2["id"], "quantity": 1},
        ],
    }

    create_res = await async_client.post("/api/v1/orders", json=payload)
    assert create_res.status_code == 201

    order = create_res.json()["data"]
    assert order["customer_name"] == "Alice Tester"
    assert order["status"] == "PENDING"

    # Verify Financial Engine Math
    expected_subtotal = (item1["price"] * 2) + (item2["price"] * 1)
    expected_tax = round(expected_subtotal * 0.0875)
    expected_total = expected_subtotal + delivery_fee + expected_tax

    assert order["subtotal_cents"] == expected_subtotal
    assert order["delivery_fee_cents"] == delivery_fee
    assert order["tax_cents"] == expected_tax
    assert order["total_cents"] == expected_total
    assert order["total_amount"] == expected_total

    # Verify Item Snapshots
    assert len(order["items"]) == 2
    order_id = order["id"]

    # 4. GET /orders/{id}
    get_res = await async_client.get(f"/api/v1/orders/{order_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == order_id

    # 5. PATCH /orders/{id} - Valid transition PENDING -> CONFIRMED
    patch_res = await async_client.patch(
        f"/api/v1/orders/{order_id}",
        json={"status": "CONFIRMED"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["data"]["status"] == "CONFIRMED"

    # 6. PATCH /orders/{id} - Illegal transition CONFIRMED -> DELIVERED (Must return 400)
    illegal_res = await async_client.patch(
        f"/api/v1/orders/{order_id}",
        json={"status": "DELIVERED"},
    )
    assert illegal_res.status_code == 400
    assert illegal_res.json()["error"]["code"] == "ILLEGAL_STATUS_TRANSITION"

    # 7. DELETE /orders/{id}
    del_res = await async_client.delete(f"/api/v1/orders/{order_id}")
    assert del_res.status_code == 200

    # 8. GET after delete returns 404
    re_get = await async_client.get(f"/api/v1/orders/{order_id}")
    assert re_get.status_code == 404


@pytest.mark.asyncio
async def test_order_creation_edge_cases(async_client: AsyncClient) -> None:
    """Verify order validation edge cases: empty items, missing body, missing restaurant."""
    missing_rest_id = "00000000-0000-0000-0000-000000000000"
    res = await async_client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": missing_rest_id,
            "customer_name": "Bob",
            "customer_email": "bob@example.com",
            "items": [{"menu_item_id": missing_rest_id, "quantity": 1}],
        },
    )
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # Empty items array returns 422
    empty_items_res = await async_client.post(
        "/api/v1/orders",
        json={
            "restaurant_id": missing_rest_id,
            "customer_name": "Bob",
            "customer_email": "bob@example.com",
            "items": [],
        },
    )
    assert empty_items_res.status_code == 422
    assert empty_items_res.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"
