---
name: seed-database
description: Workflow for generating repeatable, deterministic relational test data for BiteRoute API using Faker and SQLAlchemy without duplicates.
version: 1.0.0
---

# Skill: Seed Database with Deterministic Relational Data

## Objective
Populate PostgreSQL with 50 restaurants, 1,000+ categorized menu items, and 200 realistic historical orders. Guarantee 100% idempotency: executing the script repeatedly must never generate duplicates or fail unique constraints.

---

## Step 1: Verify Environment & Schema Migrations
1. Ensure the Python virtual environment is activated and dependencies are installed (`pip install -r requirements.txt`).
2. Verify PostgreSQL connection via `.env` (`DATABASE_URL=postgresql+asyncpg://...`).
3. Ensure all database migrations are applied:
   ```bash
   alembic upgrade head
   ```

---

## Step 2: Establish Deterministic RNG & Faker Seeds
In `scripts/seed.py`, lock random generation to seed `42`:
```python
import random
import uuid
from faker import Faker

SEED = 42
random.seed(SEED)
fake = Faker()
fake.seed_instance(SEED)
```

---

## Step 3: Implement Deterministic Identifier Strategy
To prevent unique key collisions on consecutive executions without `--clean`, generate UUIDs deterministically **while keeping them valid UUIDv4** (required by PRD §3.1 / AGENTS.md §3.2; `uuid.uuid5()` is forbidden because it produces version-5 IDs):
```python
import hashlib

def deterministic_uuid4(key: str) -> uuid.UUID:
    """Stable UUID derived from a natural key, with version/variant bits forced to v4."""
    digest = hashlib.sha256(f"biteroute:{key}".encode()).digest()
    return uuid.UUID(bytes=digest[:16], version=4)
```
1. **Restaurant UUIDs:** `deterministic_uuid4(f"restaurant-{index}")`
2. **Menu Item UUIDs:** `deterministic_uuid4(f"menu-item-{restaurant_id}-{item_index}")`
3. **Order UUIDs:** `deterministic_uuid4(f"order-{order_index}")`
4. **Order Item UUIDs:** `deterministic_uuid4(f"order-item-{order_id}-{line_index}")`

---

## Step 4: Generate Domain Entity Data

### 4.1 Restaurants (50 Records)
- Cuisine Types: `["Italian", "Mexican", "Japanese", "Thai", "American", "Indian", "Vietnamese", "Mediterranean"]`.
- Price Tier: Integer `1` to `4`.
- Rating: Fixed float rounded to 2 decimals between `3.50` and `4.95`.
- Delivery Fee: Random choice in cents: `[99, 149, 199, 299, 399, 499, 599]` (PRD §7.1: $0.99–$5.99).
- Delivery Duration: `15` to `60` minutes.
- Active Flag: Set `is_active = True` for 46 restaurants, `False` for 4 (to test rejections).

### 4.2 Menu Items (15–25 Items per Restaurant, 1,000+ total)
- Categories (exact PRD §7.1 spelling): `["Appetizers", "Mains", "Sides", "Desserts", "Beverages"]`.
- Price: Range `300` to `3500` cents ($3.00 to $35.00).
- Availability: 90% `is_available = True`, 10% `is_available = False`.

### 4.3 Orders & Order Items (200 Records, ~600 Items)
- Statuses (PRD §7.1 set only): `DELIVERED` (150), `OUT_FOR_DELIVERY` (20), `PREPARING` (25), `CANCELLED` (5).
- Each order selects 1 to 5 available menu items belonging **only** to that order's `restaurant_id`.
- Compute financial fields:
  - `subtotal_cents = sum(item.price_cents * qty)`
  - `delivery_fee_cents = restaurant.delivery_fee_cents`
  - `tax_cents = round(subtotal_cents * 0.0875)`
  - `total_cents = subtotal_cents + delivery_fee_cents + tax_cents`

---

## Step 5: Implement Upsert / Clean Execution Modes
Support `--clean` for full table truncation and default upsert for zero-duplicate re-runs:
```python
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

async def upsert_restaurant(
    session: AsyncSession, restaurant_data: dict[str, str | int | bool | uuid.UUID]
) -> None:
    stmt = insert(Restaurant).values(**restaurant_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={k: v for k, v in restaurant_data.items() if k not in ['id', 'created_at']}
    )
    await session.execute(stmt)
```

---

## Step 6: Execute and Verify Idempotency
1. Run the seed script:
   ```bash
   python scripts/seed.py
   ```
2. Verify total records in database:
   - `SELECT COUNT(*) FROM restaurants;` $\rightarrow$ 50
   - `SELECT COUNT(*) FROM menu_items;` $\rightarrow$ 1,000+
   - `SELECT COUNT(*) FROM orders;` $\rightarrow$ 200
3. Run the seed script a **second consecutive time**:
   ```bash
   python scripts/seed.py
   ```
4. Verify:
   - Script completes with exit code 0.
   - Zero duplicate key constraint errors.
   - Total row counts remain identical (net delta = 0).
