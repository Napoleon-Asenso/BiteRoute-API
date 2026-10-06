# BiteRoute API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Pytest](https://img.shields.io/badge/Pytest-Green%20Passing-brightgreen?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Production-grade, highly consumable RESTful API simulating a modern food delivery marketplace backend.**

BiteRoute API provides a clean, predictable, and robust contract for restaurant discovery, menu exploration, order creation with atomic server-side calculation, and order lifecycle management. Engineered with strict architectural boundaries, deterministic seeding, and uniform response envelopes.

---

## 🌟 Key Architectural Highlights

* **🔒 Strict Uniform Envelopes**: No raw arrays or unformatted payloads. All collections return `{ "data": [...], "meta": { ... } }`, single resources return `{ "data": { ... } }`, and all error conditions return `{ "error": { "code": "...", "message": "..." } }`.
* **💰 Zero Floating-Point Currency Drift**: Every price, fee, tax, and total is stored as an integer number of **cents** (e.g. `$14.50` is stored as `1450`).
* **🛡️ Defensive Validation & Non-Sequential IDs**: Primary keys are strictly **UUIDv4** across all models. Invalid path IDs immediately translate to `400 MALFORMED_IDENTIFIER`. Query parameters are clamped (`limit <= 100`, `offset >= 0`).
* **⏱️ IP Sliding Window Rate Limiting**: Built-in in-memory rate limiter enforcing **100 requests per 60 seconds per client IP**. Emits standard compliance headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`) and returns HTTP `429 Too Many Requests` with `Retry-After`.
* **🌱 Deterministic & Idempotent Seeding**: Standalone CLI seeder using `Faker` with a fixed seed (`seed = 42`). Generates 100 restaurants, 1,000 menu items, and 200 orders. Running consecutive seeds creates zero duplicate records.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
|---|---|---|
| **Language** | Python 3.14 | Modern native generics & type annotations |
| **Framework** | FastAPI | High-performance asynchronous REST API |
| **ASGI Server** | Uvicorn | Lightning-fast ASGI web server |
| **ORM** | SQLAlchemy 2.0 | Declarative models with `AsyncSession` & `asyncpg` |
| **Database** | SQLite / PostgreSQL | Dual-compatible local SQLite & PostgreSQL support |
| **Validation** | Pydantic V2 | Strong schema validation and serialization |
| **Seeding** | Faker | Repeatable, deterministic test dataset generation |
| **Testing** | Pytest + HTTPX | Asynchronous test suite with strict contract assertions |

---

## 📋 API Endpoint Matrix

All application endpoints are strictly versioned under `/api/v1`:

| Method | Endpoint | Description | Status Code |
|---|---|---|---|
| `GET` | `/health` | Root service health probe | `200 OK` |
| `GET` | `/api/v1/health` | Versioned PRD compliance health probe | `200 OK` |
| `GET` | `/api/v1/restaurants` | List restaurants (filterable by cuisine & price tier, sorted, paginated) | `200 OK` |
| `GET` | `/api/v1/restaurants/{id}` | Retrieve individual restaurant details | `200 OK` |
| `POST`| `/api/v1/restaurants` | Create a new restaurant partner | `201 Created` |
| `GET` | `/api/v1/restaurants/{id}/menu-items` | Browse menu items grouped/filtered by category | `200 OK` |
| `POST`| `/api/v1/restaurants/{id}/menu-items` | Add a new menu item to a restaurant | `201 Created` |
| `GET` | `/api/v1/menu-items/{id}` | Retrieve individual menu item details | `200 OK` |
| `POST`| `/api/v1/orders` | Place a delivery order with atomic pricing engine calculation | `201 Created` |
| `GET` | `/api/v1/orders/{id}` | Inspect order summary and itemized receipts | `200 OK` |
| `PATCH`| `/api/v1/orders/{id}/status` | Transition order lifecycle status | `200 OK` |

---

## 📦 Uniform Envelope Contracts

### Collection Response
```json
{
  "data": [
    {
      "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
      "name": "Napoli Artisan Pizza",
      "slug": "napoli-artisan-pizza",
      "cuisine_type": "Pizza",
      "price_tier": 2,
      "rating": 4.75,
      "is_active": true,
      "delivery_fee_cents": 299,
      "estimated_delivery_minutes": 25,
      "created_at": "2026-10-01T12:00:00Z",
      "updated_at": "2026-10-01T12:00:00Z"
    }
  ],
  "meta": {
    "total": 100,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}
```

### Single Resource Response
```json
{
  "data": {
    "id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "name": "Napoli Artisan Pizza",
    "description": "Authentic wood-fired Neapolitan pizza."
  }
}
```

### Standard Error Response
```json
{
  "error": {
    "code": "MALFORMED_IDENTIFIER",
    "message": "Value 'invalid-id' is not a valid UUIDv4 identifier."
  }
}
```

---

## 🚀 Quickstart & Setup

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Napoleon-Asenso/BiteRoute-API.git
cd BiteRoute-API

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

### 4. Deterministic Database Seeding
Populate the database with 100 restaurants, 1,000 menu items, and 200 orders:
```bash
python -m scripts.seed
```
*Tip: To reset and reseed from scratch, use `--clean`:*
```bash
python -m scripts.seed --clean
```

### 5. Run Development Server
```bash
uvicorn app.main:app --reload
```
The server will be live at `http://127.0.0.1:8000`.

* **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Testing & Verification

Run the full automated test suite covering success envelopes, error handling, rate limiting exhaustion, and health probes:

```bash
python -m pytest -v
```

---

## 📄 License
This project is open source and available under the [MIT License](LICENSE).
