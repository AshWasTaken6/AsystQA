import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from core.config import settings
from core.context import reset_correlation_id, set_correlation_id
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from services.audit import audit_log
from services.metrics import observe_request
from utils.logger import get_logger

logger = get_logger(__name__)

_rate_windows: dict[str, deque[float]] = defaultdict(deque)


async def correlation_and_metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started_at = time.perf_counter()
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid4())
    token = set_correlation_id(correlation_id)
    request.state.correlation_id = correlation_id

    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started_at
        observe_request(request.url.path, "500", duration)
        logger.exception(
            "Unhandled request error",
            extra={"path": request.url.path, "method": request.method},
        )
        audit_log(
            action="request.failed",
            outcome="failure",
            resource="http_request",
            resource_id=correlation_id,
            metadata={"path": request.url.path, "method": request.method},
            request=request,
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "server_error",
                    "message": "An unexpected error occurred.",
                    "correlation_id": correlation_id,
                }
            },
        )

    duration = time.perf_counter() - started_at
    response.headers["X-Correlation-ID"] = correlation_id
    observe_request(request.url.path, str(response.status_code), duration)
    reset_correlation_id(token)
    return response


PUBLIC_PATHS = {
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/login",
    "/auth/register",
    "/auth/refresh",
    "/auth/mfa/setup",
    "/auth/mfa/verify",
}
PUBLIC_PATHS.update({
    f"{settings.api_prefix}{path}"
    for path in [
        "/auth/login",
        "/auth/register",
        "/auth/refresh",
        "/auth/mfa/setup",
        "/auth/mfa/verify",
    ]
})


async def rate_limit_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    if settings.rate_limit_per_minute <= 0 or request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    now = time.monotonic()
    client_host = request.client.host if request.client else "unknown"
    key = f"{client_host}:{request.url.path}"
    window = _rate_windows[key]

    while window and now - window[0] >= 60:
        window.popleft()

    if len(window) >= settings.rate_limit_per_minute:
        correlation_id = getattr(request.state, "correlation_id", None)
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": "60"},
            content={
                "error": {
                    "type": "rate_limited",
                    "message": "Too many requests. Please retry shortly.",
                    "correlation_id": correlation_id,
                }
            },
        )

    window.append(now)
    return await call_next(request)
