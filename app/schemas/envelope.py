"""Uniform response and error envelopes for BiteRoute API."""

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata for paginated collection responses."""

    total: int = Field(..., ge=0, description="Total number of items available")
    limit: int = Field(..., ge=1, le=100, description="Maximum number of items requested")
    offset: int = Field(..., ge=0, description="Zero-based index offset of the first item")
    hasMore: bool = Field(
        ...,
        description="Boolean indicating whether additional items exist beyond the current window",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResponseEnvelope(BaseModel, Generic[T]):
    """Generic response envelope supporting both single item and collection payloads."""

    data: T = Field(..., description="Payload data")
    meta: PaginationMeta | None = Field(
        default=None,
        description="Pagination metadata, present on collections and optional on single items",
    )

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResponseItemEnvelope(BaseModel, Generic[T]):
    """Standard success envelope for single resource entities."""

    data: T = Field(..., description="Single resource entity")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ResponseListEnvelope(BaseModel, Generic[T]):
    """Standard success envelope for collection responses."""

    data: list[T] = Field(..., description="List of resource entities")
    meta: PaginationMeta = Field(..., description="Pagination metadata")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorDetail(BaseModel):
    """Detailed error structure containing standardized status code and human-readable message."""

    code: str = Field(..., description="Standardized UPPERCASE_SNAKE_CASE error code")
    message: str = Field(..., description="Human-readable explanation of the error condition")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorEnvelope(BaseModel):
    """Uniform error response envelope."""

    error: ErrorDetail = Field(..., description="Error details payload")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
