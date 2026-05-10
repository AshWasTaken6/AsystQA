"""
Security Middleware
FastAPI middleware for authentication, rate limiting, and security headers.
"""

import ipaddress
import time
from typing import Callable, Optional

from core.auth import decode_token, verify_session
from core.authorization import check_authorization
from core.config import settings
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from utils.audit import audit_login_attempt, extract_audit_actor_from_request
from utils.logger import get_logger

logger = get_logger(__name__)


# ============== Rate Limiting ==============

class RateLimiter:
    """
    Simple token-bucket rate limiter with in-memory storage.
    For production, use Redis with sliding window algorithm.
    """

    def __init__(self):
        self._clients: dict[str, dict] = {}
        self._rate_limit = settings.rate_limit_per_minute
        self._window_seconds = 60

    def is_allowed(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if client is allowed to proceed.

        Returns:
            (allowed: bool, headers: dict) with rate limit headers
        """
        now = time.time()

        if client_id not in self._clients:
            self._clients[client_id] = {
                "tokens": self._rate_limit,
                "last_refill": now
            }

        bucket = self._clients[client_id]

        # Refill tokens based on time passed
        time_passed = now - bucket["last_refill"]
        refill_amount = time_passed * (self._rate_limit / self._window_seconds)
        bucket["tokens"] = min(self._rate_limit, bucket["tokens"] + refill_amount)
        bucket["last_refill"] = now

        # Check if we have tokens available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            allowed = True
        else:
            allowed = False

        # Rate limit headers
        headers = {
            "X-RateLimit-Limit": str(self._rate_limit),
            "X-RateLimit-Remaining": str(int(bucket["tokens"])),
            "X-RateLimit-Reset": str(int(now + (self._window_seconds - (time_passed % self._window_seconds))))
        }

        return allowed, headers


rate_limiter = RateLimiter()


# ============== Authentication Middleware ==============

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates JWT tokens and enforces authentication.
    Extracts user context and injects into request.state.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.public_paths = {
            "/",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/healthz",
            "/readyz",
            "/livez",
            "/startupz",
            "/metrics",
            "/auth/login",
            "/auth/register",
            "/auth/refresh",
            "/auth/mfa/setup",
            "/auth/mfa/verify",
            "/auth/token",
        }
        self.public_paths.update({
            f"{prefix}{path}"
            for prefix in {settings.api_prefix, "/api/v1", "/v1"}
            for path in [
                "/healthz",
                "/readyz",
                "/livez",
                "/startupz",
                "/metrics",
                "/auth/login",
                "/auth/register",
                "/auth/refresh",
                "/auth/mfa/setup",
                "/auth/mfa/verify",
                "/auth/token",
            ]
        })

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        # Skip public paths
        if request.url.path in self.public_paths:
            return await call_next(request)

        # In local development, auth can be disabled while still decoding a token if supplied.
        auth_header = request.headers.get("authorization")
        protected_api_path = request.url.path.startswith((settings.api_prefix, "/api/v1"))
        if not settings.auth_required and not protected_api_path and not auth_header:
            return await call_next(request)

        # Extract token from Authorization header
        if not auth_header or not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing or invalid authorization header"},
                headers={"WWW-Authenticate": "Bearer"}
            )

        token = auth_header.split(" ")[1]

        try:
            # Decode and validate token
            token_data = decode_token(token)

            # Verify session is active
            if not verify_session(token_data.session_id):
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Session expired"},
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Check MFA requirement
            if settings.mfa_required and not token_data.mfa_verified:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "MFA verification required"},
                    headers={"X-MFA-Required": "true"}
                )

            # Store user context in request state
            request.state.user = token_data
            request.state.session_id = token_data.session_id

            # Update session activity
            from core.auth import update_session_activity
            update_session_activity(token_data.session_id)

            # Check authorization for this endpoint
            check_authorization(token_data, request)

            # Process request
            response = await call_next(request)

            # Add security headers to response
            if settings.enable_security_headers:
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            return response

        except HTTPException as e:
            # Log failed auth attempt
            actor = extract_audit_actor_from_request(request)
            error_msg = e.detail if hasattr(e, 'detail') else str(e)

            audit_login_attempt(
                username="unknown",
                ip=actor.ip,
                user_agent=actor.user_agent,
                success=False,
                error=error_msg
            )

            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail},
                headers=e.headers if hasattr(e, 'headers') else {}
            )
        except Exception as e:
            logger.error(f"Auth middleware error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal authentication error"}
            )


# ============== Rate Limiting Middleware ==============

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-IP rate limiting.
    Protects against brute force and DoS attacks.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Get client identifier (IP or session)
        client_ip = request.client.host if request.client else "unknown"
        # Optionally include authenticated user for per-user rate limits
        # user_id = getattr(request.state, "user", None)

        client_id = client_ip

        # Check rate limit
        allowed, headers = rate_limiter.is_allowed(client_id)

        if not allowed:
            # Log rate limit exceeded
            logger.warning(f"Rate limit exceeded: {client_ip}")

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": headers.get("X-RateLimit-Reset")
                },
                headers=headers
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value

        return response


# ============== Security Headers Middleware ==============

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security-related HTTP headers to all responses.
    """

    docs_paths = {"/docs", "/redoc", "/openapi.json"}

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        response = await call_next(request)

        if settings.enable_security_headers:
            # HSTS - HTTPS only
            response.headers["Strict-Transport-Security"] = \
                f"max-age={settings.hsts_max_age}; includeSubDomains; preload"

            # CSP - FastAPI's built-in docs load Swagger UI assets from known CDNs.
            # Keep the app CSP strict, but allow those assets only for documentation pages.
            if request.url.path in self.docs_paths:
                response.headers["Content-Security-Policy"] = settings.docs_csp_policy
            else:
                response.headers["Content-Security-Policy"] = settings.csp_policy

            # Prevent MIME sniffing
            response.headers["X-Content-Type-Options"] = "nosniff"

            # Prevent clickjacking
            response.headers["X-Frame-Options"] = "DENY"

            # XSS protection
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Referrer policy
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Permissions policy (geolocation, camera, etc.)
            response.headers["Permissions-Policy"] = \
                "geolocation=(), microphone=(), camera=()"

        return response


# ============== IP Filtering Middleware (Optional) ==============

class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Restricts access to specific IP ranges (whitelist).
    Useful for admin endpoints.
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_cidrs: Optional[list[str]] = None
    ):
        super().__init__(app)
        self.allowed_networks = [
            ipaddress.ip_network(cidr)
            for cidr in (allowed_cidrs or [])
        ]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        if not self.allowed_networks:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        client_ip = ipaddress.ip_address(client_host)
        allowed = any(
            client_ip in network
            for network in self.allowed_networks
        )

        if not allowed:
            logger.warning(f"IP blocked: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied from this IP address"}
            )

        return await call_next(request)
