"""Vercel Serverless Function entrypoint for BiteRoute API."""

import sys
import urllib.parse
from pathlib import Path
from typing import Any

# Ensure project root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app as fastapi_app


class VercelPathMiddleware:
    """ASGI middleware to normalize request path and query string rewritten by Vercel."""

    def __init__(self, asgi_app: Any) -> None:
        self.asgi_app = asgi_app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") in ("http", "websocket"):
            qs = scope.get("query_string", b"").decode("latin1")
            parsed_qs = urllib.parse.parse_qs(qs, keep_blank_values=True)
            if "__path__" in parsed_qs:
                target_path = parsed_qs.pop("__path__")[0]
                # Rebuild clean query string without __path__
                clean_qs = urllib.parse.urlencode(
                    [(k, v) for k, vals in parsed_qs.items() for v in vals]
                )
                scope["path"] = target_path
                scope["raw_path"] = target_path.encode("latin1")
                scope["query_string"] = clean_qs.encode("latin1")
        await self.asgi_app(scope, receive, send)


app = VercelPathMiddleware(fastapi_app)
