"""SQLAlchemy ORM models for orders and order items."""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import CreatedAtTimestampMixin, GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.menu_item import MenuItem
    from app.models.restaurant import Restaurant


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Order domain model representing a customer food order transaction."""

    __tablename__ = "orders"

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("restaurants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    delivery_address: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="PENDING",
        index=True,
    )

    # Itemized financial calculations stored in integer cents
    subtotal_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivery_fee_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tax_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    special_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(
        "Restaurant",
        back_populates="orders",
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'PREPARING', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')",
            name="chk_orders_status",
        ),
        CheckConstraint("subtotal_cents >= 0", name="chk_orders_subtotal_cents"),
        CheckConstraint("delivery_fee_cents >= 0", name="chk_orders_delivery_fee_cents"),
        CheckConstraint("tax_cents >= 0", name="chk_orders_tax_cents"),
        CheckConstraint("total_cents >= 0", name="chk_orders_total_cents"),
        Index("idx_orders_restaurant", "restaurant_id"),
        Index("idx_orders_status", "status"),
        Index("idx_orders_created", "created_at"),
    )

    @property
    def total_amount(self) -> int:
        """Alias property representing order total in integer cents."""
        return self.total_cents

    @total_amount.setter
    def total_amount(self, value: int) -> None:
        """Setter alias for order total in integer cents."""
        self.total_cents = value


class OrderItem(Base, UUIDPrimaryKeyMixin, CreatedAtTimestampMixin):
    """OrderItem domain model snapshotting pricing and item attributes at purchase time."""

    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("menu_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    item_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="order_items",
    )
    menu_item: Mapped["MenuItem"] = relationship("MenuItem")

    __table_args__ = (
        CheckConstraint("unit_price_cents >= 0", name="chk_order_items_unit_price_cents"),
        CheckConstraint("quantity > 0", name="chk_order_items_quantity"),
        CheckConstraint("line_total_cents >= 0", name="chk_order_items_line_total_cents"),
        Index("idx_order_items_order", "order_id"),
    )

    @property
    def unit_price(self) -> int:
        """Alias property representing item price in integer cents."""
        return self.unit_price_cents

    @unit_price.setter
    def unit_price(self, value: int) -> None:
        """Setter alias for item price in integer cents."""
        self.unit_price_cents = value
