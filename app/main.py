"""FastAPI application factory, global middleware, and exception handlers."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
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
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

# 6. Mount Minimal Consumer Client at /client
app.mount("/client", StaticFiles(directory="static", html=True), name="client")
