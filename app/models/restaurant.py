"""SQLAlchemy ORM model for restaurants."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, Index, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.menu_item import MenuItem
    from app.models.order import Order


class Restaurant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Restaurant domain model representing a merchant partner on BiteRoute."""

    __tablename__ = "restaurants"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cuisine_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_tier: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.00"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    # Address components
    address_street: Mapped[str] = mapped_column(String(255), nullable=False)
    address_city: Mapped[str] = mapped_column(String(100), nullable=False, default="San Francisco")
    address_postal_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="94103",
    )

    # Operational metrics
    delivery_fee_cents: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    estimated_delivery_minutes: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=30,
    )

    # Relationships
    menu_items: Mapped[list["MenuItem"]] = relationship(
        "MenuItem",
        back_populates="restaurant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="restaurant",
    )

    __table_args__ = (
        CheckConstraint("price_tier BETWEEN 1 AND 4", name="chk_restaurants_price_tier"),
        CheckConstraint("rating BETWEEN 0.00 AND 5.00", name="chk_restaurants_rating"),
        CheckConstraint(
            "delivery_fee_cents >= 0",
            name="chk_restaurants_delivery_fee_cents",
        ),
        CheckConstraint(
            "estimated_delivery_minutes > 0",
            name="chk_restaurants_estimated_delivery_minutes",
        ),
        Index("idx_restaurants_cuisine", "cuisine_type"),
        Index("idx_restaurants_price_tier", "price_tier"),
        Index("idx_restaurants_active", "is_active"),
    )

    @property
    def category(self) -> str:
        """Alias property matching category parameter."""
        return self.cuisine_type

    @property
    def address(self) -> str:
        """Formatted combined address representation."""
        return f"{self.address_street}, {self.address_city}, {self.address_postal_code}"
