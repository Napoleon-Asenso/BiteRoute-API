"""Pydantic V2 schemas for restaurants."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RestaurantBase(BaseModel):
    """Base schema for restaurant attributes."""

    name: str = Field(..., min_length=1, max_length=255, description="Restaurant name")
    description: str | None = Field(default=None, description="Detailed description")
    cuisine_type: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Cuisine classification (e.g. Pizza, Sushi)",
    )
    price_tier: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Economic tier from 1 ($) to 4 ($$$$)",
    )
    address_street: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Street address",
    )
    address_city: str = Field(
        default="San Francisco",
        min_length=1,
        max_length=100,
        description="City name",
    )
    address_postal_code: str = Field(
        default="94103",
        min_length=1,
        max_length=20,
        description="Postal code",
    )
    delivery_fee_cents: int = Field(
        default=0,
        ge=0,
        description="Delivery fee in integer cents",
    )
    estimated_delivery_minutes: int = Field(
        default=30,
        gt=0,
        description="Estimated delivery window in minutes",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RestaurantCreate(RestaurantBase):
    """Payload schema for creating a new restaurant."""

    pass


class RestaurantOut(BaseModel):
    """Public serialization schema for restaurant entity responses."""

    id: UUID = Field(..., description="Unique UUIDv4 identifier")
    name: str = Field(..., description="Restaurant name")
    slug: str = Field(..., description="Unique URL-friendly slug")
    category: str = Field(..., description="Cuisine category alias")
    cuisine_type: str = Field(..., description="Cuisine type classification")
    price_tier: int = Field(..., description="Price tier (1 to 4)")
    rating: float = Field(..., description="Average customer rating")
    is_active: bool = Field(..., description="Operational active status")
    address: str = Field(..., description="Formatted combined address")
    address_street: str = Field(..., description="Street address")
    address_city: str = Field(..., description="City")
    address_postal_code: str = Field(..., description="Postal code")
    delivery_fee_cents: int = Field(..., description="Delivery fee in cents")
    estimated_delivery_minutes: int = Field(..., description="Estimated delivery time in minutes")
    description: str | None = Field(default=None, description="Detailed description")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record last updated timestamp")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# Alias matching PRD naming conventions
RestaurantResponse = RestaurantOut
