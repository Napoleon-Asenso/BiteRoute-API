"""FastAPI application factory, global middleware, and exception handlers."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401 - Register all models with Base.metadata
from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, async_engine
from app.core.exceptions import AppException
from app.core.limiter import limiter
from app.core.middleware import RateLimiterMiddleware
from app.schemas.envelope import ResponseEnvelope


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Execute startup database schema initialization and application cleanup."""
    if not os.environ.get("VERCEL"):
        try:
            async with async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            pass
    yield



app = FastAPI(
    title=settings.API_TITLE,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Attach slowapi limiter state
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def slowapi_rate_limit_handler(_request: Request, _exc: RateLimitExceeded) -> JSONResponse:
    """Handle slowapi rate limit exceeded exceptions with uniform ErrorEnvelope."""
    retry_after = 60
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Too many requests. Please wait {retry_after} seconds before retrying.",
            }
        },
        headers={"Retry-After": str(retry_after)},
    )

# 1. Register CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
        "Retry-After",
    ],
)

# 2. Register Rate Limiter Middleware
app.add_middleware(RateLimiterMiddleware)


# 3. Global Exception Handlers ensuring uniform ErrorEnvelope responses
@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application domain exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Translate Pydantic and FastAPI validation errors into standardized error contracts."""
    errors = exc.errors()
    if not errors:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "UNPROCESSABLE_ENTITY",
                    "message": "Request validation failed.",
                }
            },
        )

    first_err = errors[0]
    loc = first_err.get("loc", ())
    err_type = str(first_err.get("type", ""))
    err_msg = str(first_err.get("msg", ""))

    # Path parameter validation errors (specifically UUIDv4 format violations)
    if len(loc) > 1 and loc[0] == "path":
        param_name = str(loc[1])
        raw_val = request.path_params.get(param_name, "provided")
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "MALFORMED_IDENTIFIER",
                    "message": f"Value '{raw_val}' is not a valid UUIDv4 identifier.",
                }
            },
        )

    # Query parameter clamping and boundary errors
    if len(loc) > 1 and loc[0] == "query":
        param_name = str(loc[1])
        if param_name == "limit":
            if "greater_than" in err_type:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Parameter 'limit' cannot exceed 100.",
                        }
                    },
                )
            if "less_than" in err_type:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "Parameter 'limit' must be at least 1.",
                        }
                    },
                )
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": f"Invalid limit parameter: {err_msg}",
                    }
                },
            )
        if param_name == "offset":
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Parameter 'offset' cannot be negative.",
                    }
                },
            )
        if param_name == "sort_by":
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_SORT_FIELD",
                        "message": err_msg,
                    }
                },
            )
        if param_name == "sort_order":
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_SORT_ORDER",
                        "message": err_msg,
                    }
                },
            )
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "BAD_REQUEST",
                    "message": f"Invalid query parameter '{param_name}': {err_msg}",
                }
            },
        )

    # Request body field errors
    if len(loc) > 1 and loc[0] == "body":
        field_name = str(loc[-1])
        if "missing" in err_type:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "UNPROCESSABLE_ENTITY",
                        "message": f"Missing required field: '{field_name}'.",
                    }
                },
            )
        if err_msg.startswith("Value error, "):
            clean_msg = err_msg.replace("Value error, ", "", 1)
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "UNPROCESSABLE_ENTITY",
                        "message": clean_msg,
                    }
                },
            )
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "UNPROCESSABLE_ENTITY",
                    "message": f"Invalid field '{field_name}': {err_msg}",
                }
            },
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "UNPROCESSABLE_ENTITY",
                "message": err_msg or "Unprocessable entity.",
            }
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    _request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Translate generic HTTP exceptions into uniform error envelopes."""
    code_mapping: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }
    error_code = code_mapping.get(exc.status_code, "HTTP_ERROR")
    message = str(exc.detail) if exc.detail else "An HTTP error occurred."
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": error_code, "message": message}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Catch unhandled runtime exceptions and return standard 500 error envelope."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
            }
        },
    )


# 4. Root Health Probe Endpoint (Milestone 1 requirement)
@app.get(
    "/health",
    response_model=ResponseEnvelope[dict[str, str]],
    summary="Root health check",
    description="Basic service liveness probe.",
)
async def get_health_root() -> dict[str, Any]:
    """Root health check returning service status."""
    return {
        "data": {
            "status": "healthy",
            "service": "BiteRoute API",
        },
        "meta": None,
    }


# 5. Include Versioned Routes under /api/v1
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 6. Self-Contained Embedded Consumer Client (Permanent Vercel Serverless Reliability)
CONSUMER_HTML: str = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BiteRoute API — Live Consumer Client</title>
  <style>
    :root {
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text: #0f172a;
      --muted: #64748b;
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --border: #e2e8f0;
      --badge-bg: #eff6ff;
      --badge-text: #1d4ed8;
      --star: #eab308;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 2rem 1rem;
    }

    .container {
      max-width: 800px;
      margin: 0 auto;
    }

    header {
      margin-bottom: 2rem;
      border-bottom: 1px solid var(--border);
      padding-bottom: 1rem;
    }

    h1 {
      font-size: 1.875rem;
      font-weight: 700;
      color: var(--text);
    }

    p.subtitle {
      color: var(--muted);
      font-size: 0.95rem;
      margin-top: 0.25rem;
    }

    /* Controls bar */
    .controls {
      display: flex;
      flex-wrap: wrap;
      gap: 1rem;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.5rem;
      background: var(--card-bg);
      padding: 1rem;
      border-radius: 8px;
      border: 1px solid var(--border);
    }

    .filter-group {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    label {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--text);
    }

    select {
      padding: 0.5rem 0.75rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 0.875rem;
      background-color: #fff;
      color: var(--text);
      cursor: pointer;
    }

    select:focus {
      outline: 2px solid var(--primary);
    }

    /* List container */
    .restaurant-list {
      display: flex;
      flex-direction: column;
      gap: 0.875rem;
      margin-bottom: 1.5rem;
    }

    .restaurant-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }

    .restaurant-card:hover {
      border-color: #cbd5e1;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    }

    .restaurant-info h3 {
      font-size: 1.15rem;
      font-weight: 600;
      margin-bottom: 0.35rem;
      color: var(--text);
    }

    .restaurant-address {
      font-size: 0.875rem;
      color: var(--muted);
      margin-bottom: 0.5rem;
    }

    .restaurant-meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem;
      font-size: 0.85rem;
      color: var(--muted);
    }

    .badge {
      background: var(--badge-bg);
      color: var(--badge-text);
      padding: 0.2rem 0.6rem;
      border-radius: 4px;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.025em;
    }

    .rating {
      font-weight: 600;
      color: var(--text);
      display: flex;
      align-items: center;
      gap: 0.25rem;
    }

    .rating-star {
      color: var(--star);
      font-size: 1rem;
    }

    .fee-container {
      text-align: right;
      min-width: 120px;
    }

    .fee {
      font-size: 1rem;
      font-weight: 700;
      color: var(--text);
    }

    .fee-sub {
      font-size: 0.75rem;
      color: var(--muted);
    }

    /* Pagination controls */
    .pagination {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 1.5rem;
      padding: 1rem;
      background: var(--card-bg);
      border-radius: 8px;
      border: 1px solid var(--border);
    }

    button {
      padding: 0.5rem 1rem;
      background-color: var(--primary);
      color: #fff;
      border: none;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 500;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    button:hover:not(:disabled) {
      background-color: var(--primary-hover);
    }

    button:disabled {
      background-color: #cbd5e1;
      cursor: not-allowed;
    }

    .page-info {
      font-size: 0.875rem;
      color: var(--muted);
      font-weight: 500;
    }

    /* Status and Feedback */
    .status-box {
      text-align: center;
      padding: 3rem 1rem;
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--muted);
    }

    .error-box {
      background: #fef2f2;
      border-color: #fecaca;
      color: #991b1b;
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>BiteRoute API — Live Consumer Client</h1>
      <p class="subtitle">Single-page application consuming <code>/api/v1/restaurants</code></p>
    </header>

    <div class="controls">
      <div class="filter-group">
        <label for="categoryFilter">Category Filter:</label>
        <select id="categoryFilter">
          <option value="">All</option>
          <option value="Pizza">Pizza</option>
          <option value="Burgers">Burgers</option>
          <option value="Mexican">Mexican</option>
          <option value="Sushi">Sushi</option>
          <option value="Bakery">Bakery</option>
          <option value="Italian">Italian</option>
          <option value="Mediterranean">Mediterranean</option>
          <option value="Vegan">Vegan</option>
        </select>
      </div>
    </div>

    <!-- Dynamic Content Area -->
    <div id="contentArea">
      <div class="status-box">Loading restaurants...</div>
    </div>

    <!-- Pagination controls -->
    <div class="pagination" id="paginationControls" style="display: none;">
      <button id="prevBtn" disabled>&larr; Previous</button>
      <span class="page-info" id="pageInfoText">Showing page 1 (offset 0 of 0 total)</span>
      <button id="nextBtn">Next &rarr;</button>
    </div>
  </div>

  <script>
    // Client State
    let currentOffset = 0;
    const currentLimit = 10;
    let currentCategory = "";
    let totalItems = 0;
    let hasMore = false;

    const contentArea = document.getElementById("contentArea");
    const categoryFilter = document.getElementById("categoryFilter");
    const prevBtn = document.getElementById("prevBtn");
    const nextBtn = document.getElementById("nextBtn");
    const pageInfoText = document.getElementById("pageInfoText");
    const paginationControls = document.getElementById("paginationControls");

    function formatCurrency(cents) {
      return "$" + (cents / 100).toFixed(2);
    }

    async function fetchRestaurants() {
      contentArea.innerHTML = `<div class="status-box">Loading restaurants...</div>`;

      const params = new URLSearchParams({
        limit: currentLimit,
        offset: currentOffset,
        sort: "name",
        order: "asc"
      });

      if (currentCategory) {
        params.append("category", currentCategory);
      }

      const apiUrl = window.location.origin + "/api/v1/restaurants?" + params.toString();

      try {
        const response = await fetch(apiUrl);
        const result = await response.json();

        if (!response.ok) {
          const errMsg = (result && result.error && result.error.message) || `HTTP Error ${response.status}`;
          contentArea.innerHTML = `<div class="status-box error-box"><strong>Error:</strong> ${errMsg}</div>`;
          paginationControls.style.display = "none";
          return;
        }

        renderRestaurants(result.data, result.meta);
      } catch (err) {
        contentArea.innerHTML = `<div class="status-box error-box"><strong>Network Error:</strong> Failed to connect to API.</div>`;
        paginationControls.style.display = "none";
      }
    }

    function renderRestaurants(restaurants, meta) {
      if (!restaurants || restaurants.length === 0) {
        contentArea.innerHTML = `<div class="status-box">No restaurants found for this category</div>`;
        paginationControls.style.display = "none";
        return;
      }

      totalItems = meta.total;
      hasMore = meta.hasMore;

      const html = restaurants.map(r => {
        const address = r.address || (r.address_street ? `${r.address_street}, ${r.address_city || 'San Francisco'}, ${r.address_postal_code || '94103'}` : 'San Francisco, CA');
        const category = r.category || r.cuisine_type || 'General';
        const rating = Number(r.rating || 0).toFixed(2);
        const fee = formatCurrency(r.delivery_fee_cents || 0);

        return `
          <div class="restaurant-card">
            <div class="restaurant-info">
              <h3>${r.name}</h3>
              <div class="restaurant-address">${address}</div>
              <div class="restaurant-meta">
                <span class="badge">${category}</span>
                <span class="rating"><span class="rating-star">&#9733;</span> ${rating}</span>
                <span>&bull;</span>
                <span>${r.estimated_delivery_minutes || 30} min delivery</span>
              </div>
            </div>
            <div class="fee-container">
              <div class="fee">${fee}</div>
              <div class="fee-sub">delivery fee</div>
            </div>
          </div>
        `;
      }).join("");

      contentArea.innerHTML = `<div class="restaurant-list">${html}</div>`;

      // Update Pagination UI
      paginationControls.style.display = "flex";
      prevBtn.disabled = currentOffset <= 0;
      nextBtn.disabled = !hasMore;

      const currentPage = Math.floor(currentOffset / currentLimit) + 1;
      pageInfoText.textContent = `Showing page ${currentPage} (offset ${currentOffset} of ${totalItems} total)`;
    }

    // Event Listeners
    categoryFilter.addEventListener("change", (e) => {
      currentCategory = e.target.value;
      currentOffset = 0;
      fetchRestaurants();
    });

    prevBtn.addEventListener("click", () => {
      if (currentOffset > 0) {
        currentOffset = Math.max(0, currentOffset - currentLimit);
        fetchRestaurants();
      }
    });

    nextBtn.addEventListener("click", () => {
      if (hasMore) {
        currentOffset += currentLimit;
        fetchRestaurants();
      }
    });

    // Initial Fetch
    fetchRestaurants();
  </script>
</body>
</html>
"""


@app.get(
    "/client",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Minimal Consumer Client",
)
@app.get(
    "/",
    response_class=HTMLResponse,
    include_in_schema=False,
    summary="Root Consumer Client",
)
async def get_consumer_client() -> HTMLResponse:
    """Serve the minimal consumer single-page application directly."""
    return HTMLResponse(content=CONSUMER_HTML, status_code=200)


# 7. Mount Minimal Consumer Client at /client/ (Static fallback)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


