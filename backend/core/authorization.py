"""
Authorization Module
Implements Role-Based Access Control (RBAC) with the Principle of Least Privilege.
Provides permission checking decorators and access control utilities.
"""

from enum import Enum
from functools import wraps
from typing import Awaitable, Callable, Dict, Set

from core.auth import TokenData
from core.config import settings
from fastapi import HTTPException, Request, status
from utils.logger import get_logger

logger = get_logger(__name__)


# ============== Permission Definitions ==============

class Permission(str, Enum):
    """Canonical permission list for the AsystQA system"""
    # Code analysis
    CODE_ANALYZE = "code:analyze"
    CODE_SUBMIT = "code:submit"

    # History/Data access
    HISTORY_READ = "history:read"
    HISTORY_DELETE_OWN = "history:delete_own"
    HISTORY_DELETE_ALL = "history:delete"

    # Configuration
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_MFA = "user:manage_mfa"

    # Audit and compliance
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Administration
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_CONFIG = "system:config"


class Role(str, Enum):
    """System roles in ascending order of privilege"""
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMIN = "admin"
    SECURITY_OFFICER = "security_officer"  # Read-only audit access
    SYSTEM = "system"  # Service-to-service authentication


# ============== Role-Permission Matrix ==============

ROLE_PERMISSION_MATRIX: Dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.CODE_ANALYZE,
        Permission.HISTORY_READ,
    },
    Role.ANALYST: {
        Permission.CODE_ANALYZE,
        Permission.CODE_SUBMIT,
        Permission.HISTORY_READ,
        Permission.HISTORY_DELETE_OWN,
    },
    Role.ADMIN: {
        Permission.CODE_ANALYZE,
        Permission.CODE_SUBMIT,
        Permission.HISTORY_READ,
        Permission.HISTORY_DELETE_ALL,
        Permission.CONFIG_READ,
        Permission.CONFIG_WRITE,
        Permission.USER_CREATE,
        Permission.USER_READ,
        Permission.AUDIT_READ,
        Permission.SYSTEM_MONITOR,
        Permission.SYSTEM_CONFIG,
    },
    Role.SECURITY_OFFICER: {
        Permission.HISTORY_READ,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        Permission.SYSTEM_MONITOR,
    },
    Role.SYSTEM: {
        # Service accounts have all internal permissions
        Permission.CODE_ANALYZE,
        Permission.CODE_SUBMIT,
        Permission.HISTORY_READ,
        Permission.CONFIG_READ,
        Permission.AUDIT_READ,
        Permission.SYSTEM_MONITOR,
    }
}


def get_permissions_for_role(role: Role) -> Set[Permission]:
    """Get all permissions for a given role"""
    return ROLE_PERMISSION_MATRIX.get(role, set())


def get_all_user_permissions(token_data: TokenData) -> Set[Permission]:
    """Get combined permissions for user's roles"""
    permissions = set()
    for role_str in token_data.roles:
        try:
            role = Role(role_str)
            permissions.update(get_permissions_for_role(role))
        except ValueError:
            logger.warning(f"Unknown role: {role_str}")
    return permissions


def has_permission(token_data: TokenData, permission: Permission) -> bool:
    """Check if user has a specific permission"""
    permissions = get_all_user_permissions(token_data)
    return permission in permissions


def require_any_permission(*permissions: Permission):
    """Decorator requiring at least one of the specified permissions"""
    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token_data: TokenData = kwargs.get("token_data")

            if not token_data:
                for arg in args:
                    if isinstance(arg, TokenData):
                        token_data = arg
                        break

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_perms = get_all_user_permissions(token_data)
            if not any(p in user_perms for p in permissions):
                logger.warning(
                    f"Permission denied: user={token_data.username}, "
                    f"roles={token_data.roles}, required_any={permissions}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_all_permissions(*permissions: Permission):
    """Decorator requiring all specified permissions"""
    def decorator(func: Callable[..., Awaitable]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            token_data: TokenData = kwargs.get("token_data")

            if not token_data:
                for arg in args:
                    if isinstance(arg, TokenData):
                        token_data = arg
                        break

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_perms = get_all_user_permissions(token_data)
            if not all(p in user_perms for p in permissions):
                missing = [p for p in permissions if p not in user_perms]
                logger.warning(
                    f"Permission denied: user={token_data.username}, "
                    f"missing={missing}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing permissions: {', '.join(missing)}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============== Role-Based Access Control Functions ==============

def can_access_user_data(requester: TokenData, target_user_id: str) -> bool:
    """Check if requester can access another user's data"""
    # Admins can access anyone's data
    if Role.ADMIN.value in requester.roles:
        return True

    # Users can only access their own data
    if requester.user_id == target_user_id:
        return True

    return False


def can_delete_history(requester: TokenData, owner_user_id: str) -> bool:
    """Check if user can delete history entry"""
    # Admins can delete any history
    if Role.ADMIN.value in requester.roles:
        return True

    # Users can delete only their own
    if requester.user_id == owner_user_id and Role.ANALYST.value in requester.roles:
        return True

    return False


def _normalize_path(path: str) -> str:
    """Normalize path by stripping the configured API prefix."""
    for prefix in {settings.api_prefix, "/api/v1", "/v1"}:
        if prefix and path.startswith(prefix):
            normalized = path[len(prefix):]
            return normalized if normalized else "/"
    return path


def is_authorized_for_route(
    token_data: TokenData,
    method: str,
    path: str
) -> bool:
    """
    Determine if user is authorized for a specific HTTP method + path.
    Implements route-level authorization rules.
    """
    path = _normalize_path(path)

    # Public routes (no auth required)
    public_paths = {
        "/",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/healthz",
        "/readyz",
        "/livez",
        "/startupz",
        "/metrics",
    }
    if path in public_paths:
        return True

    # Auth routes (any authenticated user)
    auth_paths = {"/auth/login", "/auth/refresh", "/auth/mfa/setup", "/auth/mfa/verify"}
    if path in auth_paths:
        return True

    # Admin routes
    admin_paths = {"/admin", "/admin/users", "/admin/config"}
    if any(path.startswith(p) for p in admin_paths):
        return Role.ADMIN.value in token_data.roles

    # Audit routes
    if path.startswith("/audit"):
        if Permission.AUDIT_READ not in get_all_user_permissions(token_data):
            return False

    # History routes - users can only access their own if not admin
    if path == "/history":
        # GET /history - user can read their own
        if method == "GET":
            return Permission.HISTORY_READ in get_all_user_permissions(token_data)
        # DELETE /history - requires admin or own deletion permission
        elif method == "DELETE":
            return (Permission.HISTORY_DELETE_ALL in get_all_user_permissions(token_data) or
                   Permission.HISTORY_DELETE_OWN in get_all_user_permissions(token_data))

    # Analysis endpoint - all authenticated roles can access
    if path == "/analyze" and method == "POST":
        return Permission.CODE_ANALYZE in get_all_user_permissions(token_data)

    # Default deny
    logger.warning(
        f"Unauthorized access attempt: user={token_data.username}, "
        f"method={method}, path={path}"
    )
    return False


# ============== Authorization Middleware ==============

def check_authorization(
    token_data: TokenData,
    request: Request
) -> None:
    """
    Middleware to check authorization for each request.
    Raises HTTPException if access is denied.
    """
    method = request.method
    path = request.url.path

    if not is_authorized_for_route(token_data, method, path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions for {method} {path}"
        )
