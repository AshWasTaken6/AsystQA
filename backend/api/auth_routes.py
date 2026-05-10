"""
Authentication API Routes
Endpoints for login, logout, token refresh, and MFA management.
"""

from datetime import datetime, timezone
from typing import Optional

from core.auth import (
    TokenData,
    authenticate_user,
    create_user,
    decode_token,
    generate_mfa_secret,
    get_user,
    get_user_by_id,
    invalidate_session,
    issue_tokens,
    revoke_token,
    update_user_mfa,
    verify_backup_code,
    verify_totp,
)
from core.auth import (
    get_current_user as require_current_user,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from utils.audit import AuditAction, audit_login_attempt, audit_mfa_event
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


# ============== Temporary MFA Storage ==============
# In production, use Redis with TTL (e.g., 10 minutes)
_temp_mfa_store: dict[str, dict] = {}


# ============== Models ==============

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: dict
    mfa_required: bool
    mfa_enrolled: bool


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)
    roles: list[str] = Field(default_factory=lambda: ["viewer"])


class UserCreateResponse(BaseModel):
    user_id: str
    username: str
    email: str
    roles: list[str]
    message: str = "User created successfully"


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class MFAEnableResponse(BaseModel):
    secret: str
    qr_code_uri: str
    backup_codes: list[str]


class MFAVerifyRequest(BaseModel):
    totp_code: str = Field(..., min_length=6, max_length=8)
    backup_code: Optional[str] = None


class UserInfoResponse(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None
    roles: list[str]
    mfa_enabled: bool


# ============== Authentication Endpoints ==============

@router.post("/login", response_model=LoginResponse)
async def login(
    request: Request,
    login_req: LoginRequest
) -> LoginResponse | JSONResponse:
    """
    Authenticate user and issue JWT tokens.
    Supports MFA if enabled for user.
    """
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Verify credentials
    user = authenticate_user(login_req.username, login_req.password)

    if not user or not user.is_active:
        audit_login_attempt(
            username=login_req.username,
            ip=ip,
            user_agent=user_agent,
            success=False,
            error="Invalid credentials or inactive account"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Check MFA requirement
    if user.mfa_enabled:
        if not login_req.mfa_code:
            # MFA required but not provided
            audit_login_attempt(
                username=user.username,
                ip=ip,
                user_agent=user_agent,
                success=False,
                error="MFA required",
                user_id=user.user_id
            )
            # HTTP 200 with special indicator so frontend knows to prompt for MFA
            return JSONResponse(
                status_code=200,
                content={
                    "error": "mfa_required",
                    "message": "Multi-factor authentication code required"
                }
            )

        # Verify MFA code
        valid = verify_totp(user.mfa_secret, login_req.mfa_code) or \
                verify_backup_code(user, login_req.mfa_code)

        if not valid:
            audit_mfa_event(
                username=user.username,
                user_id=user.user_id,
                ip=ip,
                action=AuditAction.MFA_VERIFY,
                success=False,
                error="Invalid MFA code"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code"
            )

        mfa_verified = True
    else:
        mfa_verified = False

    # Issue tokens
    tokens = issue_tokens(user, request, mfa_verified)

    # Audit successful login
    audit_login_attempt(
        username=user.username,
        ip=ip,
        user_agent=user_agent,
        success=True,
        user_id=user.user_id,
        session_id=tokens.access_token[:10]
    )

    logger.info(
        f"Login successful: user={user.username}, ip={ip}, mfa={user.mfa_enabled}"
    )

    return LoginResponse(
        access_token=tokens.access_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        refresh_token=tokens.refresh_token,
        user={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "roles": user.roles
        },
        mfa_required=user.mfa_enabled,
        mfa_enrolled=user.mfa_enabled
    )


@router.post("/logout")
async def logout(
    request: Request,
    token_data: TokenData = Depends(require_current_user)
) -> dict:
    """Logout user by revoking tokens and invalidating session"""
    ip = request.client.host if request.client else "unknown"

    auth_header = request.headers.get("authorization", "")
    token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else ""

    if token:
        revoke_token(token)

    invalidate_session(token_data.session_id)

    logger.info(f"Logout: user={token_data.username}, ip={ip}")
    return {"message": "Logged out successfully"}


@router.post("/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    request: Request,
    refresh_req: TokenRefreshRequest
) -> TokenRefreshResponse:
    """Refresh access token using refresh token"""
    try:
        payload = decode_token(refresh_req.refresh_token)

        user = get_user_by_id(payload.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        tokens = issue_tokens(user, request, mfa_verified=True)

        logger.info(f"Token refreshed: user={user.username}")

        return TokenRefreshResponse(
            access_token=tokens.access_token,
            token_type="bearer",
            expires_in=tokens.expires_in,
            refresh_token=tokens.refresh_token
        )

    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        ) from e


@router.post("/register", response_model=UserCreateResponse)
async def register(
    request: Request,
    user_req: UserCreateRequest
) -> UserCreateResponse:
    """Register a new user account"""
    try:
        user = create_user(
            username=user_req.username,
            email=user_req.email,
            password=user_req.password,
            roles=user_req.roles
        )

        logger.info(f"New user registered: {user.username}")
        return UserCreateResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            roles=user.roles
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        ) from e


@router.get("/mfa/setup", response_model=MFAEnableResponse)
async def setup_mfa(
    request: Request,
    token_data: TokenData = Depends(require_current_user)
) -> MFAEnableResponse:
    """
    Generate MFA secret for enrollment.
    Returns secret, QR code URI, and backup codes.
    """
    user = get_user(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    mfa_setup = generate_mfa_secret(user.username)

    # Store secret temporarily (TTL in production)
    _temp_mfa_store[token_data.user_id] = {
        "mfa_secret": mfa_setup.secret,
        "backup_codes": mfa_setup.backup_codes,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    audit_mfa_event(
        username=user.username,
        user_id=user.user_id,
        ip=request.client.host if request.client else "unknown",
        action=AuditAction.MFA_ENROLL,
        success=True
    )

    return MFAEnableResponse(
        secret=mfa_setup.secret,
        qr_code_uri=mfa_setup.qr_code_uri,
        backup_codes=mfa_setup.backup_codes
    )


@router.post("/mfa/verify")
async def verify_mfa(
    request: Request,
    verify_req: MFAVerifyRequest,
    token_data: TokenData = Depends(require_current_user)
) -> dict:
    """Verify MFA setup and enable it for user"""
    user = get_user(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    temp = _temp_mfa_store.get(token_data.user_id)
    if not temp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA setup not initiated or expired"
        )

    # Verify TOTP
    if not verify_totp(temp["mfa_secret"], verify_req.totp_code):
        audit_mfa_event(
            username=user.username,
            user_id=user.user_id,
            ip=request.client.host if request.client else "unknown",
            action=AuditAction.MFA_VERIFY,
            success=False,
            error="Invalid TOTP code"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code"
        )

    # Enable MFA for user
    update_user_mfa(user.username, temp["mfa_secret"], enabled=True)

    # Clear temp storage
    del _temp_mfa_store[token_data.user_id]

    audit_mfa_event(
        username=user.username,
        user_id=user.user_id,
        ip=request.client.host if request.client else "unknown",
        action=AuditAction.MFA_ENROLL,
        success=True
    )

    logger.info(f"MFA enabled: user={user.username}")

    return {"message": "MFA successfully enabled", "success": True}


@router.get("/me")
async def get_current_user(
    token_data: TokenData = Depends(require_current_user)
) -> dict:
    """Get current authenticated user info"""
    user = get_user(token_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "roles": user.roles,
        "mfa_enabled": user.mfa_enabled,
        "created_at": user.created_at
    }
