# AGENTS.md — Operational Rules & Boundaries for AI Coding Agents

**Project:** BiteRoute API (Food Delivery Marketplace)  
**Bootcamp Context:** Task 1 — "Build and Serve a Consumable REST API"  
**Canonical Specification:** [PRD.md](PRD.md)  
**Enforcement Level:** MANDATORY / ZERO TOLERANCE  

---

## 1. Project Identity & Source of Truth

1. **Project Mission:** Build a standardized, consumable, and production-grade RESTful API for a food delivery marketplace using FastAPI and PostgreSQL, adhering strictly to Task 1 specifications.
2. **Canonical Blueprint:** The file [PRD.md](PRD.md) located in the workspace root is the single source of truth. Every endpoint, database column, envelope structure, status code, error string, and constraint in `PRD.md` is locked.
3. **Hierarchy of Authority:** If any prompt, user message, or autonomous thought appears to conflict with `PRD.md`, `PRD.md` strictly supersedes. Never modify an architectural choice or schema contract without explicit, direct user instructions to update `PRD.md`.

---

## 2. Locked Tech Stack & Tools

AI agents are strictly forbidden from substituting, replacing, or introducing alternative frameworks or core libraries.

| Component | Locked Technology | Prohibited Alternatives |
|---|---|---|
| **Language** | Python 3.14 | Node.js, Go, Rust, Java, C# |
| **Web Framework** | FastAPI (ASGI) | Flask, Django, Litestar, Tornado, Express |
| **ASGI Server** | Uvicorn | Gunicorn (without Uvicorn workers), Hypercorn |
| **Database** | PostgreSQL | MySQL, SQLite (even for local dev), MongoDB, Firebase |
| **Async Driver** | `asyncpg` or `psycopg` (async) | Synchronous `psycopg2` |
| **ORM** | SQLAlchemy 2.0 (`AsyncSession`, declarative) | SQLModel, Tortoise-ORM, Peewee, raw SQL strings |
| **Migrations** | Alembic | Manual SQL scripts, Django migrations |
| **Validation / Schemas** | Pydantic V2 | Marshmallow, Cerberus, dataclasses |
| **Mock Seeding** | `faker` (Python library) | Custom manual data dictionaries, external JSON dumps |
| **Test Client** | `pytest`, `pytest-asyncio`, `httpx` | `unittest`, `requests` (in async tests) |
| **Minimal Consumer** | Vanilla HTML5 + ES6 JavaScript + Vanilla CSS | React, Vue, Svelte, Next.js, TailwindCSS, Bootstrap |

---

## 3. Invariant Rules (Hard Constraints & Absolute Prohibitions)

The following rules are absolute laws. Violating any of these constitutes immediate task failure:

### 3.1 Scope Laws
- **NEVER implement user authentication or authorization:** No user registration, login, JWT tokens, Bearer headers, API keys, sessions, cookies, OAuth, or RBAC. All endpoints are publicly consumable.
- **NEVER create administrative dashboards or back-office interfaces:** No React/Vue admin portals, no HTML admin tables, no management GUI.
- **NEVER introduce design systems or CSS frameworks:** Do not install or import TailwindCSS, Bootstrap, Material UI, or component libraries. The consumer is raw HTML/CSS.
- **NEVER create unapproved endpoints:** Only implement the endpoints specified in `PRD.md` Section 4.2. Do not invent analytics endpoints, review endpoints, user profile endpoints, or payment hooks.

### 3.2 Financial & Data Integrity Laws
- **Store every price, fee, and total in integer cents:** e.g., `1450` represents `$14.50`. NEVER use floating-point types (`float`), `REAL`, or `DOUBLE PRECISION` for currency in models, schemas, or calculations.
- **NEVER expose auto-incrementing integer IDs:** Every entity primary key (`id`, `restaurant_id`, `menu_item_id`, `order_id`) MUST be a UUIDv4. Do not expose `1, 2, 3`.

### 3.3 Envelope & Response Contract Laws
- **Collections MUST return the uniform list envelope:**
  ```json
  {
    "data": [ ... ],
    "meta": {
      "total": 50,
      "limit": 20,
      "offset": 0,
      "hasMore": true
    }
  }
  ```
- **Single items MUST return the uniform item envelope:**
  ```json
  {
    "data": { ... }
  }
  ```
- **Errors MUST ALWAYS return the uniform error envelope:**
  ```json
  {
    "error": {
      "code": "STATUS_CODE_NAME",
      "message": "Human readable detail"
    }
  }
  ```
  NEVER let raw FastAPI / Pydantic `{"detail": [...]}` leak to the client.

### 3.4 Defensive Clamping & Validation Laws
- `limit` parameter MUST default to 20, capped at 100. If `limit > 100` or `limit < 1`, return HTTP `400 BAD_REQUEST`.
- `offset` parameter MUST default to 0. If `offset < 0`, return HTTP `400 BAD_REQUEST`.
- If `offset >= total`: Return HTTP `200 OK` with `data: []` and `hasMore: false`.
- Calculate `hasMore` strictly as: `(offset + limit) < total`.
- Malformed UUID in path parameters MUST return HTTP `400 MALFORMED_IDENTIFIER` (NOT 422).
- Missing or invalid request body fields MUST return HTTP `422 UNPROCESSABLE_ENTITY`.
- Disallowed `sort_by` fields MUST return HTTP `400 INVALID_SORT_FIELD`.
- Disallowed `sort_order` values MUST return HTTP `400 INVALID_SORT_ORDER`.
- Cross-restaurant orders MUST return HTTP `400 CROSS_RESTAURANT_CONFLICT`.
- Unavailable items in orders MUST return HTTP `400 ITEM_UNAVAILABLE`.
- Orders for an inactive restaurant MUST return HTTP `400 RESTAURANT_NOT_ACCEPTING_ORDERS`.
- Order status changes outside the PRD §4.3.6 transition matrix MUST return HTTP `400 ILLEGAL_STATUS_TRANSITION`.

### 3.5 Rate Limiting Laws
- In-memory rate limiting MUST enforce a quota of 100 requests per 60 seconds per client IP.
- Every response MUST include: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Quota exhaustion MUST return HTTP `429 Too Many Requests` with `Retry-After: <seconds>` and envelope:
  ```json
  {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "Too many requests. Please wait X seconds before retrying."}}
  ```
- `GET /api/v1/health` is exempt from rate limits (it never consumes quota and never returns 429). It still emits the current `X-RateLimit-*` headers so the "every response" rule holds.
- Inactive client IPs MUST be pruned after 120 seconds to prevent memory leaks.

### 3.6 Seeding Laws
- Seeding via `scripts/seed.py` MUST be deterministic using `seed = 42` for `random` and `Faker`.
- Identifier generation for seeded records MUST be deterministic **and still valid UUIDv4** (to satisfy §3.2 and the `MALFORMED_IDENTIFIER` "UUIDv4" contract): derive 16 bytes from `sha256(stable_natural_key)` and build `uuid.UUID(bytes=digest[:16], version=4)`. This makes executing `python scripts/seed.py` multiple times without `--clean` 100% idempotent and never throws unique constraint errors on `restaurants.slug`. Do NOT use `uuid.uuid5()` (it yields version-5 IDs).

---

## 4. Repository Layout & Folder Structure

All code must be organized into this exact directory structure:

```
/
├── PRD.md                           # Canonical product specification
├── AGENTS.md                        # AI agent operational rules (this file)
├── README.md                        # Setup and run instructions
├── requirements.txt                 # Exact pinned Python dependencies
├── .env.example                     # Sample environment variables
├── alembic.ini                      # Alembic migration configuration
├── alembic/
│   ├── env.py                       # Migration environment runner
│   ├── script.py.mako               # Migration template
│   └── versions/                    # Ordered migration script files
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application factory, middleware, exceptions
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                # Pydantic Settings (DATABASE_URL, RATE_LIMIT)
│   │   ├── database.py              # AsyncEngine, async_sessionmaker, get_db dependency
│   │   ├── exceptions.py            # Custom AppException and global exception handlers
│   │   └── middleware.py            # RateLimiterMiddleware and CORSMiddleware
│   ├── models/                      # SQLAlchemy 2.0 Declarative Models
│   │   ├── __init__.py
│   │   ├── base.py                  # DeclarativeBase with UUID PK and timestamps
│   │   ├── restaurant.py            # Restaurant ORM model
│   │   ├── menu_item.py             # MenuItem ORM model
│   │   └── order.py                 # Order and OrderItem ORM models
│   ├── schemas/                     # Pydantic V2 Schemas (DTOs & Envelopes)
│   │   ├── __init__.py
│   │   ├── envelope.py              # ResponseListEnvelope, ResponseItemEnvelope, ErrorEnvelope
│   │   ├── restaurant.py            # RestaurantCreate, RestaurantResponse, etc.
│   │   ├── menu_item.py             # MenuItemCreate, MenuItemResponse, etc.
│   │   └── order.py                 # OrderCreate, OrderResponse, OrderItemResponse, etc.
│   └── api/
│       ├── __init__.py
│       ├── router.py                # Main /api/v1 APIRouter aggregator
│       └── v1/
│           ├── __init__.py
│           ├── health.py            # Health probe endpoint
│           ├── restaurants.py       # Restaurant CRUD & search endpoints
│           ├── menu_items.py        # Menu item endpoints
│           └── orders.py            # Order creation, calculation, and status endpoints
├── scripts/
│   ├── __init__.py
│   └── seed.py                      # Deterministic, idempotent Faker seed script
├── consumer/
│   └── index.html                   # Zero-dependency vanilla HTML/JS test consumer
└── tests/
    ├── __init__.py
    ├── conftest.py                  # Pytest fixtures, test DB session, async client
    ├── test_health.py               # Health probe tests
    ├── test_restaurants.py          # Restaurant query, filter, sort, pagination tests
    ├── test_menu_items.py           # Menu item retrieval and creation tests
    ├── test_orders.py               # Order calculation, snapshotting, and status tests
    ├── test_rate_limiter.py         # 100 req/min limit & 429 Retry-After tests
    └── test_envelopes.py            # Schema contract and error formatting tests
```

---

## 5. Code Standards & Patterns

### 5.1 Strict Type Hinting
- Every function, method, and route handler must include explicit parameter and return type hints.
- Use native generic aliases (Python 3.14): `list[str]`, `dict[str, int]`, `UUID | None` (never use `Any` as a shortcut — see coding-standards rule).
- Never use unannotated `def func(x):`.

### 5.2 Schema Separation
- Never return SQLAlchemy ORM models directly from endpoint functions.
- Always convert ORM models through Pydantic V2 schemas (`model_validate(from_attributes=True)`).
- Never allow Pydantic validation errors on path variables to return HTTP 422; intercept via custom `RequestValidationError` handler and return `400 MALFORMED_IDENTIFIER`.

### 5.3 Database Session Management
- Always inject database sessions into route handlers using FastAPI's dependency injection (`db: AsyncSession = Depends(get_db)`).
- Use `async with` context managers for transactions when executing multi-table mutations (e.g., `orders` + `order_items`).
- Never leave dangling uncommitted sessions.

### 5.4 Centralized Exceptions
- Define custom application exceptions in `app/core/exceptions.py`:
  - `AppException(status_code: int, code: str, message: str)`
  - Subclasses: `BadRequestException`, `NotFoundException`, `ConflictException`, etc.
- In route handlers, raise `AppException` rather than returning raw dicts or generic `HTTPException`.

---

## 6. Definition of Done (Validation Checklist)

Before claiming any task or phase is complete, the agent must verify all items:

1. **Clean Boot:**  
   `uvicorn app.main:app --port 8000` starts with zero syntax errors, deprecation warnings, or import crashes.
2. **Clean Migrations:**  
   `alembic upgrade head` runs smoothly on a blank PostgreSQL database without schema errors.
3. **Seed Idempotency:**  
   - Running `python scripts/seed.py` inserts 50 restaurants, 1,000+ menu items, and 200 orders.
   - Running `python scripts/seed.py` a second consecutive time completes with exit code 0, creates zero duplicate rows, and throws zero constraint errors.
   - Running `python scripts/seed.py --clean` truncates and re-seeds accurately.
4. **All Tests Pass:**  
   `pytest` runs green across all test suites (`tests/test_*.py`) with zero failures.
5. **Contract Uniformity:**  
   All successful collection queries return `meta.total`, `meta.limit`, `meta.offset`, `meta.hasMore`. All errors return `error.code` and `error.message`.
6. **Consumer Verification:**  
   Opening `consumer/index.html` in a web browser allows browsing restaurants, filtering, paginating, inspecting menu items, placing an order, and triggering the 429 rate limit counter.

---

## 7. Protocol When Unsure

1. **STOP IMMEDIATELY:** Do not invent features, add unrequested libraries, or guess user intent.
2. **CHECK PRD.MD:** The answer is almost always explicitly defined in [PRD.md](PRD.md).
3. **DO NOT EXTRAPOLATE SCOPE:** If an edge case is unspecified, choose the simplest solution conforming to standard REST conventions, or ask the user.
4. **ASK THE USER DIRECTLY:** Present the specific conflict, trade-off, or ambiguity clearly in 1–2 sentences and request guidance before proceeding.

---

## 8. Rule Activation Matrix & Agent Trigger Protocol

To enforce modularity and prevent context saturation while maintaining strict compliance, workspace rules in `.agents/rules/` are bound dynamically using either global (`always_on`) or path-glob triggers.

### 8.1 Active Rule Matrix

| Rule Name | Rule File Link | Activation Trigger | Bound Scope & Glob Patterns |
|---|---|---|---|
| **Coding Standards** | [coding-standards.md](.agents/rules/coding-standards.md) | `always_on` | Global: Active unconditionally on all tasks, files, and coding operations. |
| **API Contracts** | [api-contracts.md](.agents/rules/api-contracts.md) | `always_on` | Global: Active unconditionally on all endpoint contracts, routing, and error schemas. |
| **Database Schema & ORM** | [database-schema.md](.agents/rules/database-schema.md) | Glob Trigger | `app/models/**/*.py`<br>`app/schemas/**/*.py`<br>`scripts/**/*.py` |
| **Rate Limiting** | [rate-limiting.md](.agents/rules/rate-limiting.md) | Glob Trigger | `app/api/**/*.py`<br>`app/main.py`<br>`app/core/config.py`<br>`app/core/middleware.py` |
| **Testing & Evidence** | [testing-and-evidence.md](.agents/rules/testing-and-evidence.md) | Glob Trigger | `tests/**/*.py` |

### 8.2 Mandatory Agent Pre-Execution Protocol
Whenever an AI agent is requested to inspect, scaffold, modify, or test any code in the workspace, it **MUST** observe this sequence:
1. **Identify Target File Paths:** Identify the exact file path(s) to be created or edited.
2. **Consult Active Rule Matrix:** Determine which glob-triggered rules match the target path in addition to the two global `always_on` rules.
3. **Explicitly Read and Obey Rules:** Review the active rule file(s) in `.agents/rules/` and strictly obey all `ALWAYS` and `NEVER` constraints before outputting any code or proposing modifications.
4. **Zero Deviations:** No implementation decision may override the rules declared in this matrix.
