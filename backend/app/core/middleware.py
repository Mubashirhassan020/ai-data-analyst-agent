"""Request-scoped middleware."""
from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a request id, bind it to structlog context, expose via response header."""

    HEADER = "X-Request-ID"

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get(self.HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            structlog.contextvars.bind_contextvars(duration_ms=elapsed_ms)
        response.headers[self.HEADER] = req_id
        return response
