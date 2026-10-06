"""Pydantic V2 schemas for orders and order items."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderItemCreate(BaseModel):
    """Payload schema for an item in an order placement request."""

    menu_item_id: UUID = Field(..., description="Target menu item UUIDv4 identifier")
    quantity: int = Field(..., gt=0, description="Positive quantity of items ordered")

    model_config = ConfigDict(from_attributes=True)


class OrderCreate(BaseModel):
    """Payload schema for placing a new order."""

    restaurant_id: UUID = Field(..., description="UUIDv4 identifier of the target restaurant")
    customer_name: str = Field(..., min_length=1, max_length=128, description="Customer full name")
    customer_email: str = Field(..., min_length=1, max_length=255, description="Customer email")
    customer_phone: str = Field(
        default="+1-415-555-0100",
        max_length=32,
        description="Customer phone number",
    )
    delivery_address: str = Field(
        default="123 Market St, San Francisco, CA 94105",
        min_length=1,
        description="Delivery destination address",
    )
    special_instructions: str | None = Field(
        default=None,
        description="Optional delivery notes or kitchen instructions",
    )
    items: list[OrderItemCreate] = Field(
        ...,
        min_length=1,
        description="List of ordered items; must contain at least one item",
    )

    model_config = ConfigDict(from_attributes=True)

    @field_validator("items")
    @classmethod
    def validate_non_empty_items(
        cls, items: list[OrderItemCreate]
    ) -> list[OrderItemCreate]:
        """Ensure order contains at least one item."""
        if not items:
            raise ValueError("Order must contain at least one item.")
        return items


class OrderUpdate(BaseModel):
    """Payload schema for updating order status."""

    status: str | None = Field(default=None, description="Target lifecycle status")

    model_config = ConfigDict(from_attributes=True)


class OrderStatusUpdate(BaseModel):
    """Payload schema for PRD-compliant order status transitions."""

    status: str = Field(..., description="Target lifecycle status")

    model_config = ConfigDict(from_attributes=True)


class OrderItemOut(BaseModel):
    """Public serialization schema for itemized order receipt items."""

    id: UUID = Field(..., description="Unique order item identifier")
    menu_item_id: UUID = Field(..., description="Target menu item identifier")
    item_name: str = Field(..., description="Snapshot item name at time of order")
    quantity: int = Field(..., description="Item quantity ordered")
    unit_price: int = Field(..., description="Unit price in integer cents")
    unit_price_cents: int = Field(..., description="Unit price in integer cents (canonical PRD)")
    line_total_cents: int = Field(..., description="Line total in integer cents")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class OrderOut(BaseModel):
    """Public serialization schema for order entity responses."""

    id: UUID = Field(..., description="Unique order UUIDv4 identifier")
    restaurant_id: UUID = Field(..., description="Restaurant identifier")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: str = Field(..., description="Customer email")
    customer_phone: str = Field(..., description="Customer phone")
    delivery_address: str = Field(..., description="Delivery address")
    status: str = Field(..., description="Current order lifecycle status")
    subtotal_cents: int = Field(..., description="Subtotal in integer cents")
    delivery_fee_cents: int = Field(..., description="Delivery fee in integer cents")
    tax_cents: int = Field(..., description="Tax in integer cents (8.75%)")
    total_cents: int = Field(..., description="Total price in integer cents")
    total_amount: int = Field(..., description="Total price in integer cents (alias)")
    special_instructions: str | None = Field(default=None, description="Special instructions")
    items: list[OrderItemOut] = Field(
        default_factory=list,
        validation_alias="order_items",
        description="Itemized order items list",
    )
    created_at: datetime = Field(..., description="Order creation timestamp")
    updated_at: datetime = Field(..., description="Order last updated timestamp")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Aliases matching PRD naming conventions
OrderResponse = OrderOut
OrderItemResponse = OrderItemOut
