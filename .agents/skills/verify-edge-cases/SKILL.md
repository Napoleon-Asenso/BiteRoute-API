---
name: verify-edge-cases
description: Playbook for validating and asserting API error responses, input clamping (400), malformed identifiers (400), missing body fields (422), and rate limiting exhaustion (429).
version: 1.0.0
---

# Skill: Verify Edge Cases, Error Envelopes, and Status Codes

## Objective
Execute a comprehensive validation battery against the live BiteRoute API to confirm strict adherence to defensive clamping, honest status codes (400, 404, 422, 429), and the uniform error envelope structure: `{"error": {"code": "...", "message": "..."}}`.

---

## Step 1: Start API Service
Ensure the Uvicorn server is running locally:
```bash
uvicorn app.main:app --port 8000 --reload
```

---

## Step 2: Test Query Clamping (HTTP 400)

### 2.1 Negative Offset
- **Request:**
  ```bash
  curl -i -s "http://127.0.0.1:8000/api/v1/restaurants?offset=-5"
  ```
- **Assertions:**
  - HTTP Status: `400 Bad Request`
  - Response Body contains: `{"error": {"code": "BAD_REQUEST", "message": "Parameter 'offset' cannot be negative."}}`

### 2.2 Limit Over Maximum (100)
- **Request:**
  ```bash
  curl -i -s "http://127.0.0.1:8000/api/v1/restaurants?limit=101"
  ```
- **Assertions:**
  - HTTP Status: `400 Bad Request`
  - Response Body contains: `{"error": {"code": "BAD_REQUEST", "message": "Parameter 'limit' cannot exceed 100."}}`

### 2.3 Invalid Sort Field
- **Request:**
  ```bash
  curl -i -s "http://127.0.0.1:8000/api/v1/restaurants?sort_by=hack_column"
  ```
- **Assertions:**
  - HTTP Status: `400 Bad Request`
  - Response Body contains: `{"error": {"code": "INVALID_SORT_FIELD", ...}}`

---

## Step 3: Test Identifier Validation (HTTP 400 vs 404)

### 3.1 Malformed UUID in Path
Verify custom exception handler intercepts path validation and returns **HTTP 400** (NOT FastAPI's default 422):
- **Request:**
  ```bash
  curl -i -s "http://127.0.0.1:8000/api/v1/restaurants/not-a-valid-uuid-123"
  ```
- **Assertions:**
  - HTTP Status: `400 Bad Request`
  - Response Body contains: `{"error": {"code": "MALFORMED_IDENTIFIER", ...}}`

### 3.2 Non-Existent Valid UUID
- **Request:**
  ```bash
  curl -i -s "http://127.0.0.1:8000/api/v1/restaurants/00000000-0000-0000-0000-000000000000"
  ```
- **Assertions:**
  - HTTP Status: `404 Not Found`
  - Response Body contains: `{"error": {"code": "RESOURCE_NOT_FOUND", ...}}`

---

## Step 4: Test Schema Payload Validation (HTTP 422)

### 4.1 Missing Required Field
- **Request:**
  ```bash
  curl -i -s -X POST "http://127.0.0.1:8000/api/v1/restaurants" \
    -H "Content-Type: application/json" \
    -d '{"description": "No name provided"}'
  ```
- **Assertions:**
  - HTTP Status: `422 Unprocessable Entity`
  - Response Body contains: `{"error": {"code": "UNPROCESSABLE_ENTITY", ...}}`

### 4.2 Empty Items Array in Order
- **Request:**
  ```bash
  curl -i -s -X POST "http://127.0.0.1:8000/api/v1/orders" \
    -H "Content-Type: application/json" \
    -d '{
      "restaurant_id": "00000000-0000-0000-0000-000000000000",
      "customer_name": "Test",
      "customer_email": "test@example.com",
      "customer_phone": "1234567890",
      "delivery_address": "Test Street",
      "items": []
    }'
  ```
- **Assertions:**
  - HTTP Status: `422 Unprocessable Entity`
  - Response Body contains: `{"error": {"code": "UNPROCESSABLE_ENTITY", ...}}`

---

## Step 5: Test Rate Limiting Exhaustion (HTTP 429)

### 5.1 Execute Rapid Request Burst (105 Requests)
Run asynchronous bash/python loop to send 105 rapid calls:
```python
import asyncio
import httpx

async def burst():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        responses = await asyncio.gather(*[client.get("/api/v1/restaurants?limit=1") for _ in range(105)])
        statuses = [r.status_code for r in responses]
        print(f"200 count: {statuses.count(200)}, 429 count: {statuses.count(429)}")
        
        # Verify 429 response structure
        r_429 = next(r for r in responses if r.status_code == 429)
        print("Headers:", r_429.headers.get("retry-after"))
        print("Body:", r_429.json())

asyncio.run(burst())
```

### 5.2 Assertions:
1. First 100 requests return `200 OK`.
2. Requests 101–105 return `429 Too Many Requests`.
3. Response contains header: `Retry-After: <integer>`.
4. Response body matches uniform error envelope:
   ```json
   {
     "error": {
       "code": "RATE_LIMIT_EXCEEDED",
       "message": "Too many requests. Please wait X seconds before retrying."
     }
   }
   ```
