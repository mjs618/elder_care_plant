"""
Elder Care Platform - Global Middleware
Handles:
  - Request ID injection (for distributed tracing)
  - Structured request logging
  - Rate limiting by tenant SLA tier
  - Security headers
  - Request metrics collection
"""
import time
import uuid

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings
from app.core.security import decode_token

settings = get_settings()
log = structlog.get_logger()


def _get_rate_limit_key(request: Request) -> str:
    """Use tenant_id from JWT payload if available, else fallback to IP."""
    tenant_id = getattr(request.state, "tenant_id", None)
    return f"tenant:{tenant_id}" if tenant_id else get_remote_address(request)

limiter = Limiter(key_func=_get_rate_limit_key)


# ── Request Context Middleware ────────────────────────────────────────────────

class RequestContextMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique request ID and start timestamp into request.state.
    Also logs each request with its duration on completion.
    Tracks request metrics for monitoring.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        request.state.start_time = time.perf_counter()
        request.state.tenant_id = None
        request.state.user_id = None

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]
            try:
                payload = decode_token(token)
                request.state.user_id = payload.get("sub")
                request.state.tenant_id = payload.get("tid")
            except JWTError:
                pass

        from app.core.metrics import request_tracker, performance_monitor
        start_time = request_tracker.start_request(request_id)
        performance_monitor.record_request()

        with structlog.contextvars.bound_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        ):
            response = await call_next(request)
            duration_ms = (time.perf_counter() - request.state.start_time) * 1000
            
            request_tracker.end_request(
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                start_time=start_time,
            )
            
            performance_monitor.record_response_time((time.perf_counter() - start_time))
            
            if response.status_code >= 400:
                performance_monitor.record_error()
            
            log.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )
            response.headers["X-Request-ID"] = request_id
            return response


# ── Security Headers Middleware ───────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds hardened HTTP security headers to every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


# ── Exception handlers ────────────────────────────────────────────────────────

def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "Too many requests. Please upgrade your plan for higher rate limits.",
            "data": None,
        },
    )


# ── Registration helper ───────────────────────────────────────────────────────

def register_middleware(app: FastAPI) -> None:
    """Registers all middleware and exception handlers on the FastAPI app."""

    # CORS (must be registered before custom middleware in Starlette)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestContextMiddleware)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
