# BiteRoute API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pytest](https://img.shields.io/badge/Pytest-15%20Passed%20(100%25)-brightgreen?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Production-grade, highly consumable RESTful API simulating a modern food delivery marketplace backend.** Built with FastAPI, SQLAlchemy 2.0, PostgreSQL/SQLite, and Pydantic V2.

BiteRoute API provides a clean, predictable, and robust contract for restaurant discovery, menu exploration, order creation with atomic server-side calculation, and order lifecycle management. Engineered with strict architectural boundaries, deterministic seeding, and uniform response envelopes.

---

## Table of Contents
1. [Project Overview & Architecture](#1-project-overview--architecture)
2. [Quickstart & Local Setup](#2-quickstart--local-setup)
3. [Complete Endpoint Reference](#3-complete-endpoint-reference)
4. [Error Handling & Status Codes](#4-error-handling--status-codes)
5. [Mandatory Design Decisions & Defense Q&A](#5-mandatory-design-decisions--defense-qa)
6. [Testing & Rate Limiter Verification](#6-testing--rate-limiter-verification)
7. [Minimal Consumer Frontend](#7-minimal-consumer-frontend)

---

## 1. Project Overview & Architecture

BiteRoute API is a backend RESTful service modeling a food delivery marketplace. It decouples customer catalog exploration from order processing, providing a unified contract for web, mobile, and third-party consumers.

### Tech Stack
* **Runtime & Framework**: Python 3.14 / 3.10+ with FastAPI (ASGI) and Uvicorn.
* **ORM & Database Layer**: SQLAlchemy 2.0 (Declarative Base, `AsyncSession`, asyncpg driver) supporting PostgreSQL in production and local SQLite for instant development.
* **Validation & Schemas**: Pydantic V2 with strict type coercion and defensive clamping.
* **Throttling**: Dual-tier rate limiting (in-memory sliding window middleware + slowapi limiter) keyed by client IP with RFC-compliant headers.
* **Mock Seeding**: Deterministic, idempotent seeding script using Python `faker` with fixed seeds.

### Relational Entity-Relationship Diagram

```
+------------------------------------+          +------------------------------------+
|            restaurants             |          |             menu_items             |
+------------------------------------+          +------------------------------------+
| id (UUIDv4, PK)                    |<----+    | id (UUIDv4, PK)                    |
| name (VARCHAR(255))                |     |    | restaurant_id (UUID, FK, CASCADE)  |----+
| slug (VARCHAR(255), UNIQUE)        |     +---o| name (VARCHAR(255))                |    |
| description (TEXT)                 |     |    | description (TEXT)                 |    |
| cuisine_type (VARCHAR(64))         |     |    | category (VARCHAR(64))             |    |
| price_tier (SMALLINT, 1-4)         |     |    | price_cents (INTEGER)              |    |
| rating (NUMERIC(3,2))              |     |    | is_available (BOOLEAN)             |    |
| is_active (BOOLEAN)                |     |    | image_url (VARCHAR(1024))          |    |
| address_street (VARCHAR(255))      |     |    | created_at (TIMESTAMPTZ)           |    |
| address_city (VARCHAR(100))        |     |    | updated_at (TIMESTAMPTZ)           |    |
| address_postal_code (VARCHAR(20))  |     |    +------------------------------------+    |
| delivery_fee_cents (INTEGER)       |     |                                              |
| estimated_delivery_minutes (INT)   |     |                                              |
| created_at (TIMESTAMPTZ)           |     |                                              |
| updated_at (TIMESTAMPTZ)           |     |                                              |
+------------------------------------+     |                                              |
                  ^                        |                                              |
                  |                        |                                              |
+------------------------------------+     |    +------------------------------------+    |
|               orders               |     |    |            order_items             |    |
+------------------------------------+     |    +------------------------------------+    |
| id (UUIDv4, PK)                    |     |    | id (UUIDv4, PK)                    |    |
| restaurant_id (UUID, FK, RESTRICT) +-----+    | order_id (UUID, FK, CASCADE)       |<---+
| customer_name (VARCHAR(128))       |          | menu_item_id (UUID, FK, RESTRICT)  |----+
| customer_email (VARCHAR(255))      |          | item_name (VARCHAR(255))           |
| customer_phone (VARCHAR(32))       |          | unit_price_cents (INTEGER)         |
| delivery_address (TEXT)            |          | quantity (INTEGER)                 |
| status (VARCHAR(32))               |          | line_total_cents (INTEGER)         |
| subtotal_cents (INTEGER)           |          | created_at (TIMESTAMPTZ)           |
| delivery_fee_cents (INTEGER)       |          +------------------------------------+
| tax_cents (INTEGER)                |
| total_cents (INTEGER)              |
| special_instructions (TEXT)        |
| created_at (TIMESTAMPTZ)           |
| updated_at (TIMESTAMPTZ)           |
+------------------------------------+
```

---

## 2. Quickstart & Local Setup

### Prerequisites
* Python 3.10+ (Developed and tested on Python 3.14).
* Git.

### Step 1: Clone the Repository
```bash
git clone https://github.com/Napoleon-Asenso/BiteRoute-API.git
cd BiteRoute-API
```

### Step 2: Create and Activate Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell):
.\venv\Scripts\activate

# Activate on macOS / Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Environment Variables Setup
Copy the sample environment configuration:
```bash
# Windows PowerShell:
Copy-Item .env.example .env

# Linux / macOS:
cp .env.example .env
```
*(By default, `DATABASE_URL` is configured to `sqlite:///./biteroute.db` for instant local development with zero external dependencies. For PostgreSQL, simply uncomment the PostgreSQL connection string in `.env`)*.

### Step 5: Seed the Database
Populate the database with 100 restaurants, 1,000 menu items, and 200 orders:
```bash
python -m scripts.seed
```
*Note: Running `python -m scripts.seed` consecutively is 100% idempotent and produces zero duplicate rows. To clear and reset, run `python -m scripts.seed --clean`.*

### Step 6: Launch Uvicorn Development Server
```bash
uvicorn app.main:app --reload
```
The application will boot at `http://127.0.0.1:8000`.

* **Interactive OpenAPI (Swagger UI)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Minimal Consumer Frontend**: [http://127.0.0.1:8000/client/](http://127.0.0.1:8000/client/)

---

## 3. Complete Endpoint Reference

### 1. `GET /health`
Root health check probe.

* **Method**: `GET`
* **Path**: `/health`
* **Query Parameters**: None
* **Request Body**: None

```bash
curl -i -X GET http://127.0.0.1:8000/health
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "status": "healthy",
    "service": "BiteRoute API"
  },
  "meta": null
}
```

---

### 2. `GET /api/v1/health`
Versioned service liveness and PRD compliance health probe.

* **Method**: `GET`
* **Path**: `/api/v1/health`
* **Query Parameters**: None
* **Request Body**: None

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/health
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "status": "healthy",
    "timestamp": "2026-10-06T06:00:00+00:00",
    "version": "1.0.0",
    "service": "BiteRoute API"
  }
}
```

---

### 3. `GET /api/v1/restaurants`
Retrieve paginated, sorted, and filtered restaurants.

* **Method**: `GET`
* **Path**: `/api/v1/restaurants`
* **Query Parameters**:
  * `limit` (*integer*, default: `20`): Page size. Clamped between `1` and `100`.
  * `offset` (*integer*, default: `0`): Zero-based pagination offset. Must be `>= 0`.
  * `cuisine` / `category` (*string*, optional): Filter by exact cuisine type (case-insensitive, e.g. `Pizza`, `Sushi`, `Mexican`).
  * `min_rating` (*float*, optional): Minimum rating threshold (e.g. `4.5`).
  * `price_tier` (*integer*, optional): Filter by economic tier (`1`, `2`, `3`, `4`).
  * `is_active` (*boolean*, optional): Filter active availability (`true`/`false`).
  * `sort` / `sort_by` (*string*, default: `"name"`): Sort column. Allowed: `name`, `rating`, `created_at`, `delivery_fee_cents`.
  * `order` / `sort_order` (*string*, default: `"asc"`): Direction. Allowed: `asc`, `desc`.

```bash
curl -i -X GET "http://127.0.0.1:8000/api/v1/restaurants?cuisine=Pizza&limit=2&offset=0&sort=name&order=asc"
```

**Expected Response (`200 OK`)**:
```json
{
  "data": [
    {
      "id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
      "name": "Artisan Napoli Pizza",
      "slug": "artisan-napoli-pizza-1",
      "category": "Pizza",
      "cuisine_type": "Pizza",
      "price_tier": 2,
      "rating": 4.85,
      "is_active": true,
      "address": "142 Commercial St, San Francisco, 94111",
      "address_street": "142 Commercial St",
      "address_city": "San Francisco",
      "address_postal_code": "94111",
      "delivery_fee_cents": 299,
      "estimated_delivery_minutes": 25,
      "description": "Authentic wood-fired Neapolitan pizza and fresh pasta.",
      "created_at": "2026-10-06T05:23:12",
      "updated_at": "2026-10-06T05:23:12"
    },
    {
      "id": "7f8e9d0a-1b2c-3d4e-5f6a-7b8c9d0e1f2a",
      "name": "Bella Vista Pizza",
      "slug": "bella-vista-pizza-2",
      "category": "Pizza",
      "cuisine_type": "Pizza",
      "price_tier": 1,
      "rating": 4.70,
      "is_active": true,
      "address": "890 Mission St, San Francisco, 94103",
      "address_street": "890 Mission St",
      "address_city": "San Francisco",
      "address_postal_code": "94103",
      "delivery_fee_cents": 199,
      "estimated_delivery_minutes": 20,
      "description": "Hand-stretched thin crust pies.",
      "created_at": "2026-10-06T05:23:12",
      "updated_at": "2026-10-06T05:23:12"
    }
  ],
  "meta": {
    "total": 10,
    "limit": 2,
    "offset": 0,
    "hasMore": true
  }
}
```

---

### 4. `GET /api/v1/restaurants/{id}`
Retrieve individual restaurant details.

* **Method**: `GET`
* **Path**: `/api/v1/restaurants/{id}`
* **Path Parameters**: `id` (*UUIDv4*)
* **Request Body**: None

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/restaurants/e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
    "name": "Artisan Napoli Pizza",
    "slug": "artisan-napoli-pizza-1",
    "category": "Pizza",
    "cuisine_type": "Pizza",
    "price_tier": 2,
    "rating": 4.85,
    "is_active": true,
    "address": "142 Commercial St, San Francisco, 94111",
    "address_street": "142 Commercial St",
    "address_city": "San Francisco",
    "address_postal_code": "94111",
    "delivery_fee_cents": 299,
    "estimated_delivery_minutes": 25,
    "description": "Authentic wood-fired Neapolitan pizza and fresh pasta.",
    "created_at": "2026-10-06T05:23:12",
    "updated_at": "2026-10-06T05:23:12"
  },
  "meta": null
}
```

---

### 5. `GET /api/v1/restaurants/{id}/menu`
Retrieve menu items for a restaurant.

* **Method**: `GET`
* **Path**: `/api/v1/restaurants/{id}/menu` (also mounted at `/api/v1/restaurants/{id}/menu-items`)
* **Path Parameters**: `id` (*UUIDv4*)
* **Query Parameters**:
  * `category` (*string*, optional): Filter items by category (e.g. `Mains`, `Desserts`, `Beverages`).
  * `is_available` (*boolean*, optional): Filter by current availability.

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/restaurants/e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e/menu
```

**Expected Response (`200 OK`)**:
```json
{
  "data": [
    {
      "id": "9a8b7c6d-5e4f-3a2b-1c0d-e1f2a3b4c5d6",
      "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
      "name": "Margherita D.O.P.",
      "category": "Mains",
      "price": 1650,
      "price_cents": 1650,
      "is_available": true,
      "description": "San Marzano tomatoes, fresh buffalo mozzarella, fresh basil.",
      "image_url": "https://images.biteroute.io/pizza/1.jpg",
      "created_at": "2026-10-06T05:23:12",
      "updated_at": "2026-10-06T05:23:12"
    },
    {
      "id": "8b7c6d5e-4f3a-2b1c-0d9e-f2a3b4c5d6e7",
      "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
      "name": "Classic Tiramisu",
      "category": "Desserts",
      "price": 850,
      "price_cents": 850,
      "is_available": true,
      "description": "Espresso-soaked ladyfingers with mascarpone cream.",
      "image_url": "https://images.biteroute.io/pizza/7.jpg",
      "created_at": "2026-10-06T05:23:12",
      "updated_at": "2026-10-06T05:23:12"
    }
  ],
  "meta": null
}
```

---

### 6. `POST /api/v1/orders`
Place a delivery order with atomic server-side price computation.

* **Method**: `POST`
* **Path**: `/api/v1/orders`
* **Request Headers**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
  "customer_name": "Jane Doe",
  "customer_email": "jane.doe@example.com",
  "customer_phone": "+1-415-555-0199",
  "delivery_address": "500 Howard St, Apt 4B, San Francisco, CA 94105",
  "special_instructions": "Leave at front desk with doorman.",
  "items": [
    {
      "menu_item_id": "9a8b7c6d-5e4f-3a2b-1c0d-e1f2a3b4c5d6",
      "quantity": 2
    },
    {
      "menu_item_id": "8b7c6d5e-4f3a-2b1c-0d9e-f2a3b4c5d6e7",
      "quantity": 1
    }
  ]
}
```

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
    "customer_name": "Jane Doe",
    "customer_email": "jane.doe@example.com",
    "customer_phone": "+1-415-555-0199",
    "delivery_address": "500 Howard St, Apt 4B, San Francisco, CA 94105",
    "special_instructions": "Leave at front desk with doorman.",
    "items": [
      {"menu_item_id": "9a8b7c6d-5e4f-3a2b-1c0d-e1f2a3b4c5d6", "quantity": 2},
      {"menu_item_id": "8b7c6d5e-4f3a-2b1c-0d9e-f2a3b4c5d6e7", "quantity": 1}
    ]
  }'
```

**Expected Response (`201 Created`)**:
```json
{
  "data": {
    "id": "f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c",
    "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
    "customer_name": "Jane Doe",
    "customer_email": "jane.doe@example.com",
    "customer_phone": "+1-415-555-0199",
    "delivery_address": "500 Howard St, Apt 4B, San Francisco, CA 94105",
    "status": "PENDING",
    "subtotal_cents": 4150,
    "delivery_fee_cents": 299,
    "tax_cents": 363,
    "total_cents": 4812,
    "total_amount": 4812,
    "special_instructions": "Leave at front desk with doorman.",
    "items": [
      {
        "id": "11223344-5566-7788-9900-aabbccddeeff",
        "menu_item_id": "9a8b7c6d-5e4f-3a2b-1c0d-e1f2a3b4c5d6",
        "item_name": "Margherita D.O.P.",
        "quantity": 2,
        "unit_price": 1650,
        "unit_price_cents": 1650,
        "line_total_cents": 3300
      },
      {
        "id": "22334455-6677-8899-0011-bbccddeeff00",
        "menu_item_id": "8b7c6d5e-4f3a-2b1c-0d9e-f2a3b4c5d6e7",
        "item_name": "Classic Tiramisu",
        "quantity": 1,
        "unit_price": 850,
        "unit_price_cents": 850,
        "line_total_cents": 850
      }
    ],
    "created_at": "2026-10-06T06:10:00",
    "updated_at": "2026-10-06T06:10:00"
  },
  "meta": null
}
```

---

### 7. `GET /api/v1/orders/{id}`
Retrieve an existing order with itemized lines.

* **Method**: `GET`
* **Path**: `/api/v1/orders/{id}`
* **Path Parameters**: `id` (*UUIDv4*)
* **Request Body**: None

```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/orders/f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "id": "f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c",
    "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
    "customer_name": "Jane Doe",
    "customer_email": "jane.doe@example.com",
    "customer_phone": "+1-415-555-0199",
    "delivery_address": "500 Howard St, Apt 4B, San Francisco, CA 94105",
    "status": "PENDING",
    "subtotal_cents": 4150,
    "delivery_fee_cents": 299,
    "tax_cents": 363,
    "total_cents": 4812,
    "total_amount": 4812,
    "special_instructions": "Leave at front desk with doorman.",
    "items": [
      {
        "id": "11223344-5566-7788-9900-aabbccddeeff",
        "menu_item_id": "9a8b7c6d-5e4f-3a2b-1c0d-e1f2a3b4c5d6",
        "item_name": "Margherita D.O.P.",
        "quantity": 2,
        "unit_price": 1650,
        "unit_price_cents": 1650,
        "line_total_cents": 3300
      }
    ],
    "created_at": "2026-10-06T06:10:00",
    "updated_at": "2026-10-06T06:10:00"
  },
  "meta": null
}
```

---

### 8. `PATCH /api/v1/orders/{id}`
Transition order lifecycle status adhering to the state machine.

* **Method**: `PATCH`
* **Path**: `/api/v1/orders/{id}` (also mounted at `/api/v1/orders/{id}/status`)
* **Path Parameters**: `id` (*UUIDv4*)
* **Request Headers**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "status": "CONFIRMED"
}
```

```bash
curl -i -X PATCH http://127.0.0.1:8000/api/v1/orders/f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c \
  -H "Content-Type: application/json" \
  -d '{"status": "CONFIRMED"}'
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "id": "f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c",
    "restaurant_id": "e4a2bc1d-8f90-4a1e-8bc3-0d1a2b3c4d5e",
    "customer_name": "Jane Doe",
    "customer_email": "jane.doe@example.com",
    "status": "CONFIRMED",
    "subtotal_cents": 4150,
    "delivery_fee_cents": 299,
    "tax_cents": 363,
    "total_cents": 4812,
    "total_amount": 4812,
    "items": [],
    "created_at": "2026-10-06T06:10:00",
    "updated_at": "2026-10-06T06:12:00"
  },
  "meta": null
}
```

---

### 9. `DELETE /api/v1/orders/{id}`
Remove an order entity and cascade delete item snapshots.

* **Method**: `DELETE`
* **Path**: `/api/v1/orders/{id}`
* **Path Parameters**: `id` (*UUIDv4*)
* **Request Body**: None

```bash
curl -i -X DELETE http://127.0.0.1:8000/api/v1/orders/f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c
```

**Expected Response (`200 OK`)**:
```json
{
  "data": {
    "message": "Order 'f5e4d3c2-b1a0-9f8e-7d6c-5b4a3f2e1d0c' deleted successfully."
  },
  "meta": null
}
```

---

## 4. Error Handling & Status Codes

All errors strictly conform to the uniform `ErrorEnvelope` schema. Raw internal exceptions, stack traces, and unformatted framework arrays are never leaked to the consumer.

### Standard Error Envelope Structure
```json
{
  "error": {
    "code": "STATUS_CODE_NAME",
    "message": "Human readable detail"
  }
}
```

### Error Scenarios & Status Codes

| HTTP Status | Code | Trigger Scenario | Example Message |
|---|---|---|---|
| `400 Bad Request` | `BAD_REQUEST` | Negative offset | `"Parameter 'offset' cannot be negative."` |
| `400 Bad Request` | `INVALID_SORT_FIELD` | Unsupported sort field | `"Invalid sort field 'foo'. Allowed fields: [name, rating, created_at, delivery_fee_cents]."` |
| `400 Bad Request` | `INVALID_SORT_ORDER` | Unsupported sort order | `"Invalid sort order 'foo'. Allowed values: [asc, desc]."` |
| `400 Bad Request` | `MALFORMED_IDENTIFIER` | Malformed UUID in path | `"Value '123' is not a valid UUIDv4 identifier."` |
| `400 Bad Request` | `CROSS_RESTAURANT_CONFLICT` | Menu item belongs to different restaurant | `"Item '4a2b1c8f...' does not belong to restaurant '9b1deb4d...'."` |
| `400 Bad Request` | `ITEM_UNAVAILABLE` | Item marked unavailable | `"Item 'Truffle Mushroom Pizza' is currently unavailable for order."` |
| `400 Bad Request` | `RESTAURANT_NOT_ACCEPTING_ORDERS` | Target restaurant is inactive | `"Restaurant '9b1deb4d...' is not currently accepting orders."` |
| `400 Bad Request` | `ILLEGAL_STATUS_TRANSITION` | Transition violation | `"Cannot transition order from 'DELIVERED' to 'CANCELLED'."` |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Valid UUID not in database | `"Restaurant with id '00000000-0000-0000-0000-000000000000' was not found."` |
| `422 Unprocessable Entity` | `UNPROCESSABLE_ENTITY` | Missing body field / empty items | `"Missing required field: 'customer_name'."` |
| `429 Too Many Requests` | `RATE_LIMIT_EXCEEDED` | Exceeded 100 req/60s quota | `"Too many requests. Please wait 45 seconds before retrying."` |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | Unexpected server fault | `"An internal server error occurred."` |

#### Example: 400 Malformed Identifier
```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/restaurants/invalid-id-123
```
```json
{
  "error": {
    "code": "MALFORMED_IDENTIFIER",
    "message": "Value 'invalid-id-123' is not a valid UUIDv4 identifier."
  }
}
```

#### Example: 404 Resource Not Found
```bash
curl -i -X GET http://127.0.0.1:8000/api/v1/restaurants/00000000-0000-0000-0000-000000000000
```
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Restaurant with id '00000000-0000-0000-0000-000000000000' was not found."
  }
}
```

#### Example: 422 Unprocessable Entity
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Bob", "items": []}'
```
```json
{
  "error": {
    "code": "UNPROCESSABLE_ENTITY",
    "message": "Order must contain at least one item."
  }
}
```

#### Example: 429 Rate Limit Exceeded
When exceeding 100 requests in 60 seconds:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Please wait 35 seconds before retrying."
  }
}
```
**Response Headers include**:
* `Retry-After: 35`
* `X-RateLimit-Limit: 100`
* `X-RateLimit-Remaining: 0`
* `X-RateLimit-Reset: 1791266976`

---

## 5. Mandatory Design Decisions & Defense Q&A

This section provides technical justifications and answers to architectural defense questions.

### 5.1 Why These Resources Were Chosen
The resource hierarchy follows standard domain modeling for two-sided delivery marketplaces:
* `restaurants`: Represents supplier entities with operational availability flags, ratings, delivery fees, and estimated delivery windows.
* `menu_items`: Sub-resources mapped one-to-many to restaurants, establishing categorized offerings and independent item availability.
* `orders`: Represents atomic customer purchase intent. Decoupled from merchant operational dashboards to maintain clean boundary segregation.
* `order_items`: Price and name snapshot table capturing point-in-time financial truth. If a restaurant later updates a menu item's price from $12.00 to $16.00, past completed orders must retain their historical $12.00 price without data corruption.

### 5.2 Identifier Strategy: UUIDv4 vs Sequential Integers
* **Prevention of Enumeration Attacks**: Auto-incrementing integer IDs (`/orders/1`, `/orders/2`) leak business volume to competitors and allow malicious scrapers to iterate across all customer orders and restaurants.
* **Distributed Generation**: UUIDv4 can be safely generated application-side or on distributed database nodes without roundtrips to coordinate sequence locks.
* **Malformation Interception**: UUIDv4 syntax is strictly validated at the routing boundary, translating malformed input to `400 MALFORMED_IDENTIFIER` before hitting database query engines.

### 5.3 Pagination Strategy: Limit/Offset vs Cursor-Based Pagination
* **Why Offset Pagination Was Chosen for BiteRoute API**:
  * Simplicity and flexibility: Allows frontend consumers to navigate arbitrarily (e.g. jumping directly to Page 3 or changing page sizes on the fly).
  * Direct compatibility with standard SQL `LIMIT` and `OFFSET` clauses.
* **Trade-Offs & When Cursor Pagination Would Be Better**:
  * *High-Frequency Writes / Deletions*: In rapidly changing collections (e.g., live Twitter feeds or order transaction logs), offset pagination suffers from page-drift (items shifting forward or backward between requests, causing duplicates or skipped rows).
  * *Deep Pagination Performance*: `OFFSET 1000000` forces the database engine to scan and discard 1,000,000 index rows before returning the target page. Cursor-based pagination (`WHERE id > :last_seen_id ORDER BY id LIMIT 20`) performs a constant-time indexed b-tree seek, making it vastly superior for high-frequency writes and infinite scrolling.

### 5.4 Uniform Response & Error Envelope Architecture
* **Predictability**: External clients (web frontends, mobile SDKs, partner aggregators) require consistent deserialization models. Collections always have `meta.total`, `meta.limit`, `meta.offset`, and `meta.hasMore`.
* **Zero Leakage**: Standardizing errors in `{ "error": { "code": "...", "message": "..." } }` ensures internal framework validation details (such as Pydantic's internal JSON arrays) never expose server internals to external callers.

### 5.5 Defense Question: "What happens if someone requests page 50 of a resource that has 30 pages?"
* **Answer**: The API returns an **HTTP 200 OK** status code with an empty data array:
  ```json
  {
    "data": [],
    "meta": {
      "total": 100,
      "limit": 20,
      "offset": 980,
      "hasMore": false
    }
  }
  ```
* **Rationale**: Out-of-bounds pagination is not an error condition; it simply indicates that no records exist in the requested window. Returning HTTP 200 with `hasMore: false` allows clients to disable their "Next Page" button gracefully without catching exceptions.

### 5.6 Defense Question: "Show me where your rate limit number lives and tell me why it lives there."
* **Answer**: The rate limit configuration lives in **[`app/core/config.py`](file:///c:/Dev/BiteRoute%20API/app/core/config.py)**:
  ```python
  RATE_LIMIT: str = Field(default="100/minute")
  RATE_LIMIT_REQUESTS: int = Field(default=100)
  RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60)
  RATE_LIMIT_INACTIVE_TTL_SECONDS: int = Field(default=120)
  ```
* **Why it lives there**:
  * **12-Factor App Compliance**: Application configuration must be separated from business logic and code.
  * **Environment Overridability**: Ops and SRE teams can adjust throttling thresholds via environment variables (`RATE_LIMIT_REQUESTS=200`, `.env`) in staging, production, or high-traffic periods without requiring code modifications or rebuilds.
  * **DRY Centralization**: Both the custom sliding-window middleware and slowapi limiter pull from the same single source of truth.

### 5.7 Defense Question: "How to add a field to the restaurant resource without breaking existing clients?"
* **Answer**: Follow the **additive-only backward compatibility pattern**:
  1. **Database Migration**: Add the new column (e.g. `is_dine_in_available BOOLEAN DEFAULT FALSE`) with a sensible `DEFAULT` value or as nullable (`NULL`), preventing migration lockouts on existing rows.
  2. **Pydantic Model Evolution**: Update `RestaurantOut` with an optional type and default value:
     ```python
     is_dine_in_available: bool = Field(default=False)
     ```
  3. **Client Deserialization Safety**: Existing API consumers ignore unexpected additional JSON keys, while new consumers can opt-in to reading the new field. Existing endpoints, routes, and required parameters remain untouched.

---

## 6. Testing & Rate Limiter Verification

### Automated Pytest Suite
The repository includes comprehensive asynchronous tests covering envelopes, queries, sorting, input clamping, error states, and financial calculations:

```bash
python -m pytest -v
```

**Test Execution Results (15/15 Passing)**:
```text
tests/test_envelopes.py::test_not_found_returns_uniform_error_envelope PASSED
tests/test_envelopes.py::test_method_not_allowed_returns_uniform_error_envelope PASSED
tests/test_health.py::test_root_health_endpoint PASSED
tests/test_health.py::test_api_v1_health_endpoint PASSED
tests/test_orders.py::test_order_creation_atomic_pricing_engine PASSED
tests/test_orders.py::test_order_creation_edge_cases PASSED
tests/test_rate_limiter.py::test_rate_limit_headers_on_all_responses PASSED
tests/test_rate_limiter.py::test_health_check_exempt_from_quota_decrement PASSED
tests/test_rate_limiter.py::test_quota_exhaustion_returns_429 PASSED
tests/test_restaurants.py::test_list_restaurants_pagination_and_envelope PASSED
tests/test_restaurants.py::test_list_restaurants_category_and_cuisine_filtering PASSED
tests/test_restaurants.py::test_list_restaurants_sorting PASSED
tests/test_restaurants.py::test_list_restaurants_defensive_clamping_and_validation PASSED
tests/test_restaurants.py::test_get_restaurant_by_id_and_not_found PASSED
tests/test_restaurants.py::test_get_restaurant_menu PASSED
============================= 15 passed in 9.40s =============================
```

### Rate Limiter Live Stress Test
Execute the standalone test script to verify that burst traffic triggers HTTP 429 throttling:

```bash
python -m scripts.test_rate_limit
```

Fires 110 requests, printing remaining headers, the 429 status trigger, and the `Retry-After` response header upon exhaustion.

---

## 7. Minimal Consumer Frontend

Per Step 8 of Task 1, a lightweight, single-page consumer client is mounted and served directly by the API.

* **Client URL**: [http://127.0.0.1:8000/client/](http://127.0.0.1:8000/client/)
* **Implementation**: [`static/index.html`](file:///c:/Dev/BiteRoute%20API/static/index.html) (Pure vanilla HTML5 + ES6 JavaScript, zero external dependencies).
* **Features**:
  * Category dropdown filtering (Pizza, Sushi, Burgers, Bakery, Vegan, Mexican, etc.).
  * Page size selector (5, 10, 20, 50).
  * Previous / Next pagination navigation.
  * Restaurant cards rendering category badges, star ratings, and formatted dollar delivery fees.
  * Empty state and network error handling.

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
