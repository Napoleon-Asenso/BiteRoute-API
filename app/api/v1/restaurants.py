"""FastAPI router for restaurant endpoints."""

import re
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.menu_item import MenuItem
from app.models.restaurant import Restaurant
from app.schemas.envelope import PaginationMeta, ResponseEnvelope
from app.schemas.menu_item import MenuItemOut
from app.schemas.restaurant import RestaurantCreate, RestaurantOut

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])

ALLOWED_SORT_FIELDS: list[str] = ["name", "rating", "created_at", "delivery_fee_cents"]
ALLOWED_SORT_ORDERS: list[str] = ["asc", "desc"]


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    clean = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", clean).strip("-")


@router.get(
    "",
    response_model=ResponseEnvelope[list[RestaurantOut]],
    summary="List restaurants",
    description="Retrieve paginated list of restaurants with optional filtering and sorting.",
)
async def list_restaurants(
    limit: int = Query(default=20, description="Page limit (1-100)"),
    offset: int = Query(default=0, description="Page offset (>= 0)"),
    cuisine: str | None = Query(default=None, description="Filter by cuisine (exact, case-insensitive)"),
    category: str | None = Query(default=None, description="Alias filter for cuisine"),
    min_rating: float | None = Query(default=None, ge=0.0, le=5.0, description="Minimum customer rating"),
    price_tier: int | None = Query(default=None, ge=1, le=4, description="Filter by price tier (1-4)"),
    is_active: bool | None = Query(default=None, description="Filter active status"),
    sort: str | None = Query(default=None, description="Sort field alias"),
    sort_by: str | None = Query(default=None, description="Sort field (name, rating, created_at, delivery_fee_cents)"),
    order: str | None = Query(default=None, description="Sort order alias (asc, desc)"),
    sort_order: str | None = Query(default=None, description="Sort order (asc, desc)"),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[RestaurantOut]]:
    """Query restaurants with pagination, multi-field filtering, and sorting."""
    # 1. Parameter Clamping and Validation
    if offset < 0:
        raise BadRequestException("Parameter 'offset' cannot be negative.")
    
    # Defensive Clamping: clamp limit to [1, 100]
    if limit > 100:
        limit = 100
    elif limit < 1:
        limit = 1

    active_sort: str = sort_by or sort or "name"
    if active_sort not in ALLOWED_SORT_FIELDS:
        raise BadRequestException(
            f"Invalid sort field '{active_sort}'. Allowed fields: [{', '.join(ALLOWED_SORT_FIELDS)}].",
            code="INVALID_SORT_FIELD",
        )

    active_order: str = sort_order or order or "asc"
    active_order_lower = active_order.lower()
    if active_order_lower not in ALLOWED_SORT_ORDERS:
        raise BadRequestException(
            f"Invalid sort order '{active_order}'. Allowed values: [{', '.join(ALLOWED_SORT_ORDERS)}].",
            code="INVALID_SORT_ORDER",
        )

    # 2. Build Base Query and Filters
    query = select(Restaurant)
    target_cuisine = cuisine or category
    if target_cuisine:
        query = query.where(func.lower(Restaurant.cuisine_type) == target_cuisine.lower())
    if price_tier is not None:
        query = query.where(Restaurant.price_tier == price_tier)
    if is_active is not None:
        query = query.where(Restaurant.is_active == is_active)
    if min_rating is not None:
        query = query.where(Restaurant.rating >= min_rating)

    # 3. Calculate Total Count
    count_stmt = select(func.count()).select_from(query.subquery())
    total: int = (await db.scalar(count_stmt)) or 0

    # 4. Defensive check: offset >= total
    if offset >= total:
        meta = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            hasMore=False,
        )
        return ResponseEnvelope(data=[], meta=meta)

    # 5. Apply Sorting
    sort_column = getattr(Restaurant, active_sort)
    if active_order_lower == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # 6. Apply Pagination Window
    query = query.offset(offset).limit(limit)
    result = await db.scalars(query)
    restaurants = list(result.all())

    # 7. Compute Envelope and Meta
    has_more = (offset + limit) < total
    meta = PaginationMeta(
        total=total,
        limit=limit,
        offset=offset,
        hasMore=has_more,
    )
    data = [RestaurantOut.model_validate(r) for r in restaurants]
    return ResponseEnvelope(data=data, meta=meta)


@router.post(
    "",
    response_model=ResponseEnvelope[RestaurantOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create restaurant",
    description="Register a new restaurant partner.",
)
async def create_restaurant(
    payload: RestaurantCreate,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RestaurantOut]:
    """Create a new restaurant entity."""
    base_slug = slugify(payload.name)
    slug = base_slug
    suffix = 1

    # Ensure slug uniqueness
    while await db.scalar(select(Restaurant.id).where(Restaurant.slug == slug)):
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    restaurant = Restaurant(
        name=payload.name,
        slug=slug,
        description=payload.description,
        cuisine_type=payload.cuisine_type,
        price_tier=payload.price_tier,
        address_street=payload.address_street,
        address_city=payload.address_city,
        address_postal_code=payload.address_postal_code,
        delivery_fee_cents=payload.delivery_fee_cents,
        estimated_delivery_minutes=payload.estimated_delivery_minutes,
    )

    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)

    return ResponseEnvelope(data=RestaurantOut.model_validate(restaurant), meta=None)


@router.get(
    "/{id}",
    response_model=ResponseEnvelope[RestaurantOut],
    summary="Get restaurant detail",
    description="Retrieve an individual restaurant by UUIDv4.",
)
async def get_restaurant(
    id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[RestaurantOut]:
    """Fetch restaurant detail by identifier."""
    restaurant = await db.get(Restaurant, id)
    if not restaurant:
        raise NotFoundException(entity_name="Restaurant", entity_id=str(id))

    return ResponseEnvelope(data=RestaurantOut.model_validate(restaurant), meta=None)


@router.get(
    "/{id}/menu",
    response_model=ResponseEnvelope[list[MenuItemOut]],
    summary="Get restaurant menu items (compact route)",
    description="Retrieve all menu items belonging to the given restaurant.",
)
@router.get(
    "/{id}/menu-items",
    response_model=ResponseEnvelope[list[MenuItemOut]],
    summary="Get restaurant menu items (canonical PRD route)",
    description="Retrieve menu items belonging to the given restaurant with optional filtering.",
)
async def get_restaurant_menu(
    id: UUID,
    category: str | None = Query(default=None, description="Filter items by category"),
    is_available: bool | None = Query(default=None, description="Filter items by availability"),
    limit: int | None = Query(default=None, ge=1, le=100, description="Optional page limit"),
    offset: int = Query(default=0, ge=0, description="Optional page offset"),
    db: AsyncSession = Depends(get_db),
) -> ResponseEnvelope[list[MenuItemOut]]:
    """Retrieve all menu items associated with a given restaurant."""
    # Verify restaurant existence
    restaurant = await db.get(Restaurant, id)
    if not restaurant:
        raise NotFoundException(entity_name="Restaurant", entity_id=str(id))

    stmt = select(MenuItem).where(MenuItem.restaurant_id == id)
    if category:
        stmt = stmt.where(func.lower(MenuItem.category) == category.lower())
    if is_available is not None:
        stmt = stmt.where(MenuItem.is_available == is_available)

    stmt = stmt.order_by(MenuItem.name.asc())

    if limit is not None:
        total_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.scalar(total_stmt)) or 0
        stmt = stmt.offset(offset).limit(limit)
        items = list((await db.scalars(stmt)).all())
        has_more = (offset + limit) < total
        meta = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            hasMore=has_more,
        )
        return ResponseEnvelope(
            data=[MenuItemOut.model_validate(it) for it in items],
            meta=meta,
        )

    items = list((await db.scalars(stmt)).all())
    return ResponseEnvelope(
        data=[MenuItemOut.model_validate(it) for it in items],
        meta=None,
    )
