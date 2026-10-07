"""Vercel Serverless Function entrypoint for BiteRoute API."""

import sys
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app as fastapi_app


class VercelASGIMiddleware:
    """ASGI middleware to normalize request paths rewritten by Vercel."""

    def __init__(self, asgi_app: Any) -> None:
        self.asgi_app = asgi_app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") in ("http", "websocket"):
            headers = dict(scope.get("headers", []))
            # Vercel supplies the original requested path in x-matched-path or x-forwarded-uri
            matched_path = headers.get(b"x-matched-path") or headers.get(b"x-forwarded-uri")
            if matched_path:
                clean_path = matched_path.decode("latin1").split("?")[0]
                if clean_path and clean_path != "/api/index.py":
                    scope["path"] = clean_path
                    scope["raw_path"] = clean_path.encode("latin1")
        await self.asgi_app(scope, receive, send)


app = VercelASGIMiddleware(fastapi_app)
