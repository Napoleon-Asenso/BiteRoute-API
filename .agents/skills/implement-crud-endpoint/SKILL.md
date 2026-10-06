---
name: implement-crud-endpoint
description: Step-by-step recipe for building a versioned FastAPI route (/api/v1/...) with Pydantic validation, defensive filtering, sorting, pagination, and uniform response envelopes.
version: 1.0.0
---

# Skill: Implement Versioned CRUD Endpoint with Uniform Envelopes

## Objective
Implement a production-grade FastAPI route under `/api/v1/` featuring defensive parameter clamping, whitelisted sorting, multi-field filtering, and strict envelope formatting (`data` and `meta`).

---

## Step 1: Define Pydantic V2 Schemas
In `app/schemas/<entity>.py`, define request models and response DTOs:
```python
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class EntityBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    cuisine_type: str = Field(min_length=1, max_length=64)
    price_tier: int = Field(ge=1, le=4)
    delivery_fee_cents: int = Field(ge=0)

class EntityCreate(EntityBase):
    address_street: str
    address_city: str
    address_postal_code: str

class EntityResponse(EntityBase):
    id: UUID
    slug: str
    rating: float  # NUMERIC(3,2) in DB; float so JSON emits a number (4.75), not a string. Not currency.
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

---

## Step 2: Define Envelope Containers
In `app/schemas/envelope.py`, define generic envelope schemas:
```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    hasMore: bool

class CollectionEnvelope(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginationMeta

class ItemEnvelope(BaseModel, Generic[T]):
    data: T

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
```

---

## Step 3: Implement Query Parameter Validation & Clamping
In the route function, clamp `limit` and `offset` defensively:
```python
from fastapi import APIRouter, Depends, Query
from app.core.exceptions import BadRequestException

# Ordered tuples so error messages list fields exactly as in PRD §5.
# (menu-items uses its own tuple: ("price_cents", "name", "created_at").)
ALLOWED_SORT_FIELDS: tuple[str, ...] = ("name", "rating", "delivery_fee_cents", "created_at")
ALLOWED_SORT_ORDERS: tuple[str, ...] = ("asc", "desc")

@router.get("", response_model=CollectionEnvelope[EntityResponse])
async def list_entities(
    limit: int = Query(20),
    offset: int = Query(0),
    cuisine: str | None = Query(None),
    price_tier: int | None = Query(None),
    is_active: bool | None = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    db: AsyncSession = Depends(get_db)
) -> CollectionEnvelope[EntityResponse]:
    # Defensive Clamping & Validation (messages must match PRD §5 verbatim)
    if limit > 100:
        raise BadRequestException(code="BAD_REQUEST", message="Parameter 'limit' cannot exceed 100.")
    if limit < 1:
        raise BadRequestException(code="BAD_REQUEST", message="Parameter 'limit' must be at least 1.")
    if offset < 0:
        raise BadRequestException(code="BAD_REQUEST", message="Parameter 'offset' cannot be negative.")
    if sort_by not in ALLOWED_SORT_FIELDS:
        raise BadRequestException(
            code="INVALID_SORT_FIELD",
            message=f"Invalid sort field '{sort_by}'. Allowed fields: [{', '.join(ALLOWED_SORT_FIELDS)}]."
        )
    sort_order = sort_order.lower()
    if sort_order not in ALLOWED_SORT_ORDERS:
        raise BadRequestException(
            code="INVALID_SORT_ORDER",
            message=f"Invalid sort order '{sort_order}'. Allowed values: [asc, desc]."
        )
```

---

## Step 4: Execute Database Query with Filters & Pagination
Construct the SQLAlchemy 2.0 query:
```python
    from sqlalchemy import select, func

    # Base query with filters
    query = select(Entity)
    if cuisine:
        query = query.where(func.lower(Entity.cuisine_type) == cuisine.lower())
    if price_tier is not None:
        query = query.where(Entity.price_tier == price_tier)
    if is_active is not None:
        query = query.where(Entity.is_active == is_active)

    # Total count query
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Boundary check: if offset >= total, return empty list
    if offset >= total:
        return CollectionEnvelope(
            data=[],
            meta=PaginationMeta(total=total, limit=limit, offset=offset, hasMore=False)
        )

    # Apply sorting
    sort_column = getattr(Entity, sort_by)
    query = query.order_by(sort_column.desc() if sort_order == "desc" else sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    # Wrap in uniform envelope
    return CollectionEnvelope(
        data=[EntityResponse.model_validate(item) for item in items],
        meta=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            hasMore=(offset + limit) < total
        )
    )
```

---

## Step 5: Mount Router via `app/api/router.py`
Per the AGENTS.md layout, resource routers are aggregated in `app/api/router.py`, which `app/main.py` includes once:
```python
# app/api/router.py
from fastapi import APIRouter
from app.api.v1.restaurants import router as restaurants_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(restaurants_router, prefix="/restaurants", tags=["Restaurants"])

# app/main.py
from app.api.router import api_router
app.include_router(api_router)
```

---

## Step 6: Verify Endpoint via Test
Create `tests/test_restaurants.py` asserting:
1. `meta.hasMore` is correctly computed.
2. Query with `?offset=-1` returns HTTP 400.
3. Query with `?limit=150` returns HTTP 400.
4. Query with `?sort_by=invalid` returns HTTP 400.
