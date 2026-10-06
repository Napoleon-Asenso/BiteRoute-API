"""Pydantic V2 schemas package exporting models and response envelopes."""

from app.schemas.envelope import (
    ErrorDetail,
    ErrorEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseItemEnvelope,
    ResponseListEnvelope,
)
from app.schemas.menu_item import MenuItemCreate, MenuItemOut, MenuItemResponse
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemOut,
    OrderItemResponse,
    OrderOut,
    OrderResponse,
    OrderStatusUpdate,
    OrderUpdate,
)
from app.schemas.restaurant import RestaurantCreate, RestaurantOut, RestaurantResponse

__all__ = [
    "PaginationMeta",
    "ResponseEnvelope",
    "ResponseItemEnvelope",
    "ResponseListEnvelope",
    "ErrorDetail",
    "ErrorEnvelope",
    "RestaurantCreate",
    "RestaurantOut",
    "RestaurantResponse",
    "MenuItemCreate",
    "MenuItemOut",
    "MenuItemResponse",
    "OrderItemCreate",
    "OrderCreate",
    "OrderUpdate",
    "OrderStatusUpdate",
    "OrderItemOut",
    "OrderItemResponse",
    "OrderOut",
    "OrderResponse",
]
