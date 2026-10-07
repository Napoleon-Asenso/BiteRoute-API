"""Vercel Serverless Function entrypoint for BiteRoute API."""

import sys
import traceback
from pathlib import Path

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from app.main import app
except Exception:
    err_msg = traceback.format_exc()
    from fastapi import FastAPI
    from starlette.responses import PlainTextResponse

    app = FastAPI(title="BiteRoute Error Diagnostics")

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
    async def catch_all(path: str) -> PlainTextResponse:
        return PlainTextResponse(f"STARTUP EXCEPTION:\n{err_msg}", status_code=500)
