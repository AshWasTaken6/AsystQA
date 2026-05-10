from contextlib import asynccontextmanager
from typing import Any

from api.auth import auth_router as legacy_auth_router
from api.auth_routes import router as auth_router
from api.routes import router as analysis_router
from core.agent_registry import Principal, require_permission
from core.auth import init_default_users
from core.config import settings
from core.middleware import correlation_and_metrics_middleware, rate_limit_middleware
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from middleware.security import AuthMiddleware, SecurityHeadersMiddleware
from services.audit import audit_log
from services.memory import load_memory, memory_store_writable, verify_memory_integrity
from services.metrics import increment_error, render_metrics
from services.tracing import configure_tracing
from utils.logger import get_logger

logger = get_logger(__name__)

# ============== Startup Initialization ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize security components on startup"""
    from services.memory import migrate_to_encrypted

    init_default_users()

    # Migrate plaintext history to encrypted format if needed
    try:
        migrated = migrate_to_encrypted()
        if migrated:
            logger.info("Migrated memory storage to encrypted format")
    except Exception as e:
        logger.error(f"Memory migration failed: {e}")

    logger.info("Security system initialized")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
configure_tracing(app)


# ============== Global Middleware Stack (Order Matters!) ==============

# 1. Correlation IDs and basic metrics (must be first for tracing)
app.middleware("http")(correlation_and_metrics_middleware)

# 2. Rate limiting (early to prevent abuse)
if settings.rate_limit_enabled:
    app.middleware("http")(rate_limit_middleware)

# 3. Authentication & Authorization (core security)
app.add_middleware(AuthMiddleware)

# 4. Security headers (adds headers to responses)
app.add_middleware(SecurityHeadersMiddleware)

# Optional: IP filtering for admin endpoints
# app.add_middleware(IPFilterMiddleware, allowed_cidrs=["10.0.0.0/8"])

# 5. CORS (after auth so OPTIONS requests work)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Router Registration ==============

# Include routers
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(analysis_router, prefix=settings.api_prefix)
app.include_router(analysis_router)
app.include_router(analysis_router, prefix="/v1")
app.include_router(legacy_auth_router, prefix="/v1")

if settings.api_prefix != "/api/v1":
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(analysis_router, prefix="/api/v1")


# ============== Exception Handlers ==============

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    increment_error("validation_error", "api")
    correlation_id = getattr(request.state, "correlation_id", None)
    errors = jsonable_encoder(exc.errors())
    audit_log(
        action="request.validation_failed",
        outcome="failure",
        resource="http_request",
        resource_id=correlation_id,
        metadata={"path": request.url.path, "errors": errors},
        request=request,
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "validation_error",
                "message": "Request validation failed.",
                "correlation_id": correlation_id,
                "details": errors,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    detail: dict[str, Any] = exc.detail if isinstance(exc.detail, dict) else {
        "type": "http_error",
        "message": str(exc.detail),
    }
    detail.setdefault("correlation_id", correlation_id)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": detail},
        headers=getattr(exc, "headers", None)
    )


# ============== Core Endpoints ==============

@app.get("/")
def root() -> dict[str, str]:
    return {"status": f"{settings.app_name} running", "version": "1.0.0-secure"}


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
def readyz() -> dict[str, str]:
    load_memory()
    return {"status": "ready"}


@app.get("/livez")
def livez() -> dict[str, str | bool]:
    return {
        "status": "alive",
        "memory_integrity": verify_memory_integrity(),
        "memory_writable": memory_store_writable(),
    }


@app.get("/startupz")
def startupz() -> dict[str, str]:
    return {"status": "started", "environment": settings.environment}


@app.get("/metrics")
def metrics() -> Response:
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


# ============== Security Endpoints ==============

@app.get("/security/status")
def security_status() -> dict[str, Any]:
    """
    Get security system status.
    Includes encryption, integrity, and configuration checks.
    """
    from core.auth import _active_sessions, _revoked_tokens
    from services.memory import verify_memory_integrity

    status = {
        "mfa_enabled": settings.mfa_required,
        "encryption_enabled": bool(settings.encryption_key or settings.key_vault_url),
        "audit_logging": True,
        "rate_limiting": settings.rate_limit_enabled,
        "security_headers": settings.enable_security_headers,
        "memory_integrity": verify_memory_integrity(),
        "active_sessions": len(_active_sessions),
        "revoked_tokens": len(_revoked_tokens),
    }

    return status


@app.get("/security/audit/recent")
def recent_audit_events(
    limit: int = 20,
    principal: Principal = Depends(require_permission("audit:read"))
) -> dict:
    """
    Get recent audit events for monitoring.
    Requires audit read permission.
    """
    from services.audit import query_audit_logs

    events = query_audit_logs(limit=limit)
    return {
        "events": events,
        "count": len(events)
    }


# ============== Versioned API (Backwards Compatible) ==============

@app.get("/v1/healthz")
def v1_healthz() -> dict[str, str]:
    return healthz()


@app.get("/v1/readyz")
def v1_readyz() -> dict[str, str]:
    return readyz()


@app.get("/v1/livez")
def v1_livez() -> dict[str, str | bool]:
    return livez()


@app.get("/v1/startupz")
def v1_startupz() -> dict[str, str]:
    return startupz()


@app.get("/v1/metrics")
def v1_metrics() -> Response:
    return metrics()
