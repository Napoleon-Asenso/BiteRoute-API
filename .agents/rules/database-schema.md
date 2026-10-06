---
trigger: glob
description: Rules for database models, migrations, foreign key constraints, integer cents currency, and UTC timestamps.
---

# Database Schema & ORM Rule

**Scope:** PostgreSQL, SQLAlchemy 2.0, Alembic Migrations  
**Rule File:** `.agents/rules/database-schema.md`  
**Trigger Globs:** `app/models/**/*.py`, `app/schemas/**/*.py`, `scripts/**/*.py`  
**Enforcement:** MANDATORY  

---

## 1. Identifiers & Primary Keys
- **ALWAYS** use UUIDv4 for all entity primary keys (`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`).
- **NEVER** use auto-incrementing integer IDs (`SERIAL`, `BIGSERIAL`, `INTEGER`) for primary keys.
- **ALWAYS** type model primary keys as `uuid.UUID` in Python and `UUID(as_uuid=True)` in SQLAlchemy columns.
- **ALWAYS** keep seeded IDs valid UUIDv4: derive them deterministically as `uuid.UUID(bytes=sha256(key).digest()[:16], version=4)`. **NEVER** use `uuid.uuid5()`.

---

## 2. Foreign Keys & Integrity Constraints
- **ALWAYS** define explicit foreign key constraints on relational child tables:
  - `menu_items.restaurant_id` REFERENCES `restaurants(id) ON DELETE CASCADE`.
  - `orders.restaurant_id` REFERENCES `restaurants(id) ON DELETE RESTRICT`.
  - `order_items.order_id` REFERENCES `orders(id) ON DELETE CASCADE`.
  - `order_items.menu_item_id` REFERENCES `menu_items(id) ON DELETE RESTRICT`.
- **ALWAYS** create explicit database indexes on all foreign key columns (`idx_menu_items_restaurant`, `idx_orders_restaurant`, `idx_order_items_order`).
- **ALWAYS** create composite or single-column indexes on columns used in filtering and sorting:
  - `restaurants`: `cuisine_type`, `price_tier`, `is_active`, `rating DESC`.
  - `menu_items`: `(restaurant_id, category)`, `(restaurant_id, is_available)`.
  - `orders`: `status`, `created_at DESC`.

---

## 3. Monetary Values (Minor Units)
- **ALWAYS** store every monetary amount in positive **integer cents**:
  - `price_cents`, `subtotal_cents`, `delivery_fee_cents`, `tax_cents`, `total_cents`.
  - Example: Store $14.50 as `1450`.
- **NEVER** use floating-point types (`float`), `REAL`, or `DOUBLE PRECISION` for currency in database tables, ORM models, or business logic.
- **ALWAYS** apply a `CHECK (column_cents >= 0)` constraint on all financial columns.

---

## 4. Timestamps
- **ALWAYS** include `created_at` and `updated_at` on `restaurants`, `menu_items`, and `orders`.
- **EXCEPTION (per PRD §3.3 DDL):** `order_items` is an immutable price/name snapshot and has **only** `created_at`. **NEVER** add `updated_at` to `order_items`.
- **ALWAYS** define timestamp columns as timezone-aware UTC (`TIMESTAMPTZ`, `server_default=func.now()`).
- **ALWAYS** update `updated_at` automatically on modification via `server_default=func.now()` and `onupdate=func.now()`.

---

## 5. Migrations & Alembic
- **ALWAYS** use Alembic to manage database schema evolution.
- **ALWAYS** generate an explicit migration file in `alembic/versions/` for every table creation, column addition, or index modification.
- **NEVER** execute manual `ALTER TABLE` or `CREATE TABLE` commands outside Alembic migrations.
- **ALWAYS** verify that `alembic upgrade head` runs cleanly on a blank PostgreSQL instance.