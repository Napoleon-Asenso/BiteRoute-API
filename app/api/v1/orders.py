"""FastAPI router for order placement, calculation, and lifecycle transitions."""

from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem
from app.models.restaurant import Restaurant
from app.schemas.envelope import ResponseEnvelope
from app.schemas.order import OrderCreate, OrderOut, OrderStatusUpdate, OrderUpdate

router = APIRouter(prefix="/orders", tags=["Orders"])

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"PREPARING", "CANCELLED"},
    "PREPARING": {"OUT_FOR_DELIVERY"},
    "OUT_FOR_DELIVERY": {"DELIVERED"},
    "DELIVERED": set(),
    "CANCELLED": set(),
}

VALID_STATUSES: set[str] = {
    "PENDING",
    "CONFIRMED",
    "PREPARING",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "CANCELLED",
}


@router.post(
    "",
    response_model=ResponseEnvelope[OrderOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create and place order",
    description="Atomically validate restaurant/items, execute server-side pricing, and persist order.",
)
async def create_order(
    payload: OrderCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[OrderOut]:
    """Validate and atomically compute an order."""
    # 1. Validate Restaurant existence and active status
    restaurant = await db.get(Restaurant, payload.restaurant_id)
    if not restaurant:
        raise NotFoundException(entity_name="Restaurant", entity_id=str(payload.restaurant_id))

    if not restaurant.is_active:
        raise BadRequestException(
            f"Restaurant '{payload.restaurant_id}' is not currently accepting orders.",
            code="RESTAURANT_NOT_ACCEPTING_ORDERS",
        )

    # 2. Collect and load requested Menu Items
    requested_ids = [item.menu_item_id for item in payload.items]
    stmt = select(MenuItem).where(MenuItem.id.in_(requested_ids))
    result = await db.scalars(stmt)
    loaded_items: dict[UUID, MenuItem] = {item.id: item for item in result.all()}

    # 3. Validate item existence, ownership, and availability
    subtotal_cents = 0
    order_item_models: list[OrderItem] = []

    for item_input in payload.items:
        menu_item = loaded_items.get(item_input.menu_item_id)
        if not menu_item:
            raise NotFoundException(entity_name="MenuItem", entity_id=str(item_input.menu_item_id))

        if menu_item.restaurant_id != restaurant.id:
            raise BadRequestException(
                f"Item '{menu_item.id}' does not belong to restaurant '{restaurant.id}'.",
                code="CROSS_RESTAURANT_CONFLICT",
            )

        if not menu_item.is_available:
            raise BadRequestException(
                f"Item '{menu_item.name}' is currently unavailable for order.",
                code="ITEM_UNAVAILABLE",
            )

        line_total_cents = menu_item.price_cents * item_input.quantity
        subtotal_cents += line_total_cents

        order_item = OrderItem(
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            unit_price_cents=menu_item.price_cents,
            quantity=item_input.quantity,
            line_total_cents=line_total_cents,
        )
        order_item_models.append(order_item)

    # 4. Execute Financial Pricing Engine
    delivery_fee_cents = restaurant.delivery_fee_cents
    tax_cents = round(subtotal_cents * 0.0875)  # Flat 8.75% tax rate
    total_cents = subtotal_cents + delivery_fee_cents + tax_cents

    # 5. Persist Order and Items atomically
    order = Order(
        restaurant_id=restaurant.id,
        customer_name=payload.customer_name,
        customer_email=payload.customer_email,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        special_instructions=payload.special_instructions,
        status="PENDING",
        subtotal_cents=subtotal_cents,
        delivery_fee_cents=delivery_fee_cents,
        tax_cents=tax_cents,
        total_cents=total_cents,
    )
    order.order_items = order_item_models

    db.add(order)
    await db.commit()
    await db.refresh(order)

    # Re-fetch order with items eagerly loaded
    refetch_stmt = select(Order).options(selectinload(Order.order_items)).where(Order.id == order.id)
    saved_order = await db.scalar(refetch_stmt)

    return ResponseEnvelope(data=OrderOut.model_validate(saved_order), meta=None)


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[OrderOut],
    summary="Get order details",
    description="Retrieve an existing order with its itemized lines.",
)
async def get_order(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[OrderOut]:
    """Fetch order details and item lines."""
    stmt = select(Order).options(selectinload(Order.order_items)).where(Order.id == id)
    order = await db.scalar(stmt)
    if not order:
        raise NotFoundException(entity_name="Order", entity_id=str(id))

    return ResponseEnvelope(data=OrderOut.model_validate(order), meta=None)


@router.patch(
    "/{id}",
    response_model=ResponseEnvelope[OrderOut],
    summary="Update order (partial update)",
    description="Partially update order attributes such as status.",
)
@router.patch(
    "/{id}/status",
    response_model=ResponseEnvelope[OrderOut],
    summary="Transition order status (canonical PRD route)",
    description="Transition order lifecycle state adhering to the transition matrix.",
)
async def update_order_status(
    id: UUID,
    payload: OrderStatusUpdate | OrderUpdate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[OrderOut]:
    """Execute order status state machine transition."""
    if not payload.status:
        raise BadRequestException("Field 'status' must be provided.")

    target_status = payload.status.upper()
    if target_status not in VALID_STATUSES:
        raise BadRequestException(
            f"Invalid order status '{payload.status}'. Allowed: {sorted(list(VALID_STATUSES))}.",
            code="BAD_REQUEST",
        )

    stmt = select(Order).options(selectinload(Order.order_items)).where(Order.id == id)
    order = await db.scalar(stmt)
    if not order:
        raise NotFoundException(entity_name="Order", entity_id=str(id))

    current_status = order.status.upper()
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if target_status not in allowed:
        raise BadRequestException(
            f"Cannot transition order from '{current_status}' to '{target_status}'.",
            code="ILLEGAL_STATUS_TRANSITION",
        )

    order.status = target_status
    await db.commit()
    await db.refresh(order)

    return ResponseEnvelope(data=OrderOut.model_validate(order), meta=None)


@router.delete(
    "/{id}",
    response_model=ResponseEnvelope[dict[str, str]],
    summary="Delete order",
    description="Remove an existing order by ID.",
)
async def delete_order(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[dict[str, str]]:
    """Delete an order entity and its item snapshot lines."""
    order = await db.get(Order, id)
    if not order:
        raise NotFoundException(entity_name="Order", entity_id=str(id))

    await db.delete(order)
    await db.commit()

    return ResponseEnvelope(
        data={"message": f"Order '{id}' deleted successfully."},
        meta=None,
    )
