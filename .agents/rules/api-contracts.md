---
name: api-contracts
trigger: always_on
description: Always-active API contract rules enforcing /api/v1 versioning, uniform envelopes (data, meta, error), and honest status codes.
---

# API Contracts & Envelopes Rule

**Scope:** FastAPI routing, request validation, response serialization, and status codes  
**Rule File:** `.agents/rules/api-contracts.md`  
**Trigger:** `always_on` (Global)  
**Enforcement:** MANDATORY  

---

## 1. Route Versioning
- **ALWAYS** prefix every application endpoint with `/api/v1`.
- **NEVER** expose unversioned domain endpoints (e.g. `/restaurants` is forbidden; must be `/api/v1/restaurants`).
- **ALWAYS** maintain consistent URL structure: plural nouns for resource collections (`/api/v1/restaurants`, `/api/v1/menu-items`, `/api/v1/orders`).

---

## 2. Standard Success Envelopes

### 2.1 Collection (List) Envelope
- **ALWAYS** wrap collection responses in the following structure:
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
- **ALWAYS** compute `hasMore` strictly as: `(offset + limit) < total`.
- **ALWAYS** return HTTP 200 with `data: []` and `hasMore: false` when `offset >= total`.
- **NEVER** return a raw JSON array `[...]` at the root of a response.

### 2.2 Single Resource Envelope
- **ALWAYS** wrap single entity responses in the standard item envelope:
  ```json
  {
    "data": { ... }
  }
  ```
- **NEVER** return raw entity fields directly at the root of a response.

---

## 3. Standard Error Envelope
- **ALWAYS** format all error responses using the uniform error envelope:
  ```json
  {
    "error": {
      "code": "STATUS_CODE_NAME",
      "message": "Human readable detail"
    }
  }
  ```
- **ALWAYS** use UPPERCASE_SNAKE_CASE for `code` (e.g. `BAD_REQUEST`, `MALFORMED_IDENTIFIER`, `RESOURCE_NOT_FOUND`, `UNPROCESSABLE_ENTITY`, `RATE_LIMIT_EXCEEDED`).
- **NEVER** leak raw FastAPI / Pydantic validation arrays (`{"detail": [...]}`) to the consumer.

---

## 4. Honest HTTP Status Codes
- **ALWAYS** return honest and semantically accurate HTTP status codes:
  - `200 OK`: Successful read or update operation.
  - `201 Created`: Successful resource creation (`POST /api/v1/restaurants`, `POST /api/v1/orders`).
  - `400 Bad Request`: Client-side semantic or input clamping violation:
    - `limit > 100` or `limit < 1`
    - `offset < 0`
    - Invalid `sort_by` field or `sort_order`
    - Malformed UUID in path parameters (`MALFORMED_IDENTIFIER`)
    - Cross-restaurant order items (`CROSS_RESTAURANT_CONFLICT`)
    - Unavailable items in order (`ITEM_UNAVAILABLE`)
    - Inactive restaurant (`RESTAURANT_NOT_ACCEPTING_ORDERS`)
    - Disallowed order status change per PRD §4.3.6 (`ILLEGAL_STATUS_TRANSITION`)
  - `404 Not Found`: Target resource with valid UUID syntax does not exist in the database (`RESOURCE_NOT_FOUND`).
  - `422 Unprocessable Entity`: Missing or malformed fields in the JSON request body (`UNPROCESSABLE_ENTITY`).
  - `429 Too Many Requests`: Client IP exceeded rate limit quota (`RATE_LIMIT_EXCEEDED`).
  - `500 Internal Server Error`: Unhandled server-side fault (`INTERNAL_SERVER_ERROR`).
- **NEVER** return `200 OK` for an error payload.

---

## 5. Path Parameter UUID Exception Translation
- **ALWAYS** override FastAPI's default `RequestValidationError` handler.
- **ALWAYS** inspect `err["loc"]`: if the failure occurs on a `path` parameter representing an identifier, return **HTTP 400** with code `MALFORMED_IDENTIFIER`.
- **NEVER** allow an invalid path UUID (`/restaurants/invalid-id`) to return HTTP 422.
