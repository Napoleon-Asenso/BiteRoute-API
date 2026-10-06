---
name: testing-and-evidence
trigger:
  glob:
    - "tests/**/*.py"
description: Testing rules enforcing automated pytest test suite, seed idempotency checks, and curl command verification.
---

# Testing & Evidence Rule

**Scope:** Automated testing, CLI verification, and seed idempotency checks  
**Rule File:** `.agents/rules/testing-and-evidence.md`  
**Trigger Globs:** `tests/**/*.py`  
**Enforcement:** MANDATORY  

---

## 1. Automated Test Suite (pytest)
- **ALWAYS** write comprehensive asynchronous tests using `pytest`, `pytest-asyncio`, and `httpx.AsyncClient`.
- **ALWAYS** structure test files under `tests/` matching domain resources:
  - `tests/test_health.py`
  - `tests/test_restaurants.py`
  - `tests/test_menu_items.py`
  - `tests/test_orders.py`
  - `tests/test_rate_limiter.py`
  - `tests/test_envelopes.py`
- **ALWAYS** verify that all tests pass with 100% green status before completing any phase.
- **NEVER** mock away the database entirely when validating SQLAlchemy schemas and query contracts; use a real PostgreSQL test database or dedicated test schema.

---

## 2. Mandatory Verification Scenarios
- **ALWAYS** include test assertions for:
  1. **Success Envelopes:** Ensure `data` and `meta` (with `total`, `limit`, `offset`, `hasMore`) exist on all collection endpoints.
  2. **Error Envelopes:** Ensure `error.code` and `error.message` exist on all error responses.
  3. **Clamping & Validation:**
     - Querying `?limit=101` returns `400 BAD_REQUEST`.
     - Querying `?offset=-1` returns `400 BAD_REQUEST`.
     - Querying `?sort_by=unsupported` returns `400 INVALID_SORT_FIELD`.
     - Requesting an invalid UUID string `/restaurants/abc-123` returns `400 MALFORMED_IDENTIFIER` (NOT 422).
     - Submitting a body missing required fields returns `422 UNPROCESSABLE_ENTITY`.
  4. **Financial Calculation Accuracy:**
     - `subtotal_cents = sum(item.price_cents * quantity)`
     - `tax_cents = round(subtotal_cents * 0.0875)`
     - `total_cents = subtotal_cents + delivery_fee_cents + tax_cents`
  5. **Rate Limiting:**
     - Bursting 101 requests returns HTTP 429 on request 101.
     - Verify `Retry-After`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining` headers.

---

## 3. Seed Idempotency Evidence
- **ALWAYS** execute the seed script verification protocol to prove idempotency:
  1. Run `python scripts/seed.py` (record count: 50 restaurants, 1000+ items, 200 orders).
  2. Run `python scripts/seed.py` a second consecutive time.
  3. **ALWAYS** verify that the second run completes with exit code 0, throws zero unique constraint violations, and results in a net database row change of zero.

---

## 4. Exact curl Command Verification Routines
- **ALWAYS** provide exact, reproducible `curl` commands for manual smoke testing:

```bash
# 1. Health Probe
curl -i -X GET http://127.0.0.1:8000/api/v1/health

# 2. List Restaurants with Filtering & Pagination
curl -i -X GET "http://127.0.0.1:8000/api/v1/restaurants?cuisine=Italian&limit=5&offset=0&sort_by=rating&sort_order=desc"

# 3. Malformed UUID (Must return 400 MALFORMED_IDENTIFIER)
curl -i -X GET http://127.0.0.1:8000/api/v1/restaurants/invalid-uuid-123

# 4. Out of Bounds Limit (Must return 400 BAD_REQUEST)
curl -i -X GET "http://127.0.0.1:8000/api/v1/restaurants?limit=500"

# 5. Place an Order
curl -i -X POST http://127.0.0.1:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "<VALID_RESTAURANT_UUID>",
    "customer_name": "Test Customer",
    "customer_email": "test@example.com",
    "customer_phone": "+1-555-0100",
    "delivery_address": "123 Market St, San Francisco, CA",
    "items": [{"menu_item_id": "<VALID_MENU_ITEM_UUID>", "quantity": 2}]
  }'
```
