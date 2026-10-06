"""Pydantic V2 schemas for menu items."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MenuItemBase(BaseModel):
    """Base schema for menu item attributes."""

    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    category: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Menu category (e.g. Mains, Sides, Drinks)",
    )
    price_cents: int = Field(..., ge=0, description="Price stored in integer cents")
    description: str | None = Field(default=None, description="Detailed item description")
    is_available: bool = Field(default=True, description="Availability flag for ordering")
    image_url: str | None = Field(default=None, description="URL pointing to item image")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MenuItemCreate(MenuItemBase):
    """Payload schema for creating a menu item under a restaurant."""

    pass


class MenuItemOut(BaseModel):
    """Public serialization schema for menu item responses."""

    id: UUID = Field(..., description="Unique UUIDv4 identifier")
    restaurant_id: UUID = Field(..., description="Parent restaurant identifier")
    name: str = Field(..., description="Item name")
    category: str = Field(..., description="Menu category")
    price: int = Field(..., description="Price in integer cents")
    price_cents: int = Field(..., description="Price in integer cents (canonical PRD field)")
    is_available: bool = Field(..., description="Availability status")
    description: str | None = Field(default=None, description="Detailed item description")
    image_url: str | None = Field(default=None, description="Image URL")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last updated timestamp")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Alias matching PRD naming conventions
MenuItemResponse = MenuItemOut
