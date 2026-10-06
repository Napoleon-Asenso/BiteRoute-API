"""SQLAlchemy ORM model for menu items."""

import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import GUID, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant


class MenuItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """MenuItem domain model representing a food or drink item under a restaurant."""

    __tablename__ = "menu_items"

    restaurant_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Relationships
    restaurant: Mapped["Restaurant"] = relationship(
        "Restaurant",
        back_populates="menu_items",
    )

    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="chk_menu_items_price_cents"),
        Index("idx_menu_items_restaurant", "restaurant_id"),
        Index("idx_menu_items_category", "restaurant_id", "category"),
        Index("idx_menu_items_availability", "restaurant_id", "is_available"),
    )

    @property
    def price(self) -> int:
        """Alias property representing price in cents."""
        return self.price_cents

    @price.setter
    def price(self, value: int) -> None:
        """Setter alias for price in cents."""
        self.price_cents = value
