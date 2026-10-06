---
name: rate-limiting
trigger:
  glob:
    - "app/api/**/*.py"
    - "app/main.py"
    - "app/core/config.py"
    - "app/core/middleware.py"
description: Rate limiting rules enforcing IP-based sliding window (100 req/min), standard headers, and 429 Retry-After responses.
---

# Rate Limiting Rule

**Scope:** Middleware, request throttling, compliance headers, and error responses  
**Rule File:** `.agents/rules/rate-limiting.md`  
**Trigger Globs:** `app/api/**/*.py`, `app/main.py`, `app/core/config.py`, `app/core/middleware.py`  
**Enforcement:** MANDATORY  

---

## 1. Keying Strategy & Client IP Resolution
- **ALWAYS** key the rate limiter by client IP address.
- **ALWAYS** check the `X-Forwarded-For` HTTP header first, taking the leftmost IP address.
- **ALWAYS** fall back to `request.client.host` if `X-Forwarded-For` is absent or empty.
- **NEVER** key rate limits by global state, user agent, or session cookies.

---

## 2. Configuration & Quota Parameters
- **ALWAYS** store rate limit parameters inside `app/core/config.py` using Pydantic `BaseSettings`:
  - `RATE_LIMIT_REQUESTS: int = 100`
  - `RATE_LIMIT_WINDOW_SECONDS: int = 60`
  - `RATE_LIMIT_INACTIVE_TTL_SECONDS: int = 120`
- **NEVER** hardcode quota numbers (e.g. `100` or `60`) directly inside middleware or route handler functions.

---

## 3. Required Compliance Headers
- **ALWAYS** inject the following standard rate limit headers on **every** API response (both success and error):
  - `X-RateLimit-Limit`: The total allowed requests in the active window (e.g. `100`).
  - `X-RateLimit-Remaining`: The integer number of requests remaining in the current window.
  - `X-RateLimit-Reset`: The Unix epoch timestamp (in seconds) when the active window resets.
- **ALWAYS** expose these headers via CORS middleware (`expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset", "Retry-After"]`).

---

## 4. Quota Exhaustion & 429 Handling
- **ALWAYS** return **HTTP 429 Too Many Requests** immediately once the quota is exhausted.
- **ALWAYS** include the standard `Retry-After: <seconds>` response header containing the number of seconds until quota resets.
- **ALWAYS** format the 429 response body using the uniform error envelope:
  ```json
  {
    "error": {
      "code": "RATE_LIMIT_EXCEEDED",
      "message": "Too many requests. Please wait 45 seconds before retrying."
    }
  }
  ```

---

## 5. Memory Management & Health Check Exemption
- **ALWAYS** exempt `GET /api/v1/health` from rate limiting to allow continuous monitoring without penalties: it **never** decrements quota and **never** returns 429, but it **still** emits the current `X-RateLimit-*` headers (satisfying Section 3).
- **ALWAYS** implement an eviction policy that prunes inactive client IP records after 120 seconds of inactivity to prevent memory exhaustion in long-running instances.
