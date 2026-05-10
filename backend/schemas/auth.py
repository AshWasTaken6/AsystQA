"""
Authentication-related Pydantic schemas.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """User login request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    mfa_code: Optional[str] = Field(None, min_length=6, max_length=8)


class LoginResponse(BaseModel):
    """Successful login response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str
    user: dict
    mfa_required: bool
    mfa_enrolled: bool


class UserCreateRequest(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)
    roles: List[str] = Field(default_factory=lambda: ["viewer"])


class UserCreateResponse(BaseModel):
    """User creation response"""
    user_id: str
    username: str
    email: str
    roles: List[str]
    message: str = "User created successfully"


class TokenRefreshRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class TokenRefreshResponse(BaseModel):
    """New tokens after refresh"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: str


class MFAEnableResponse(BaseModel):
    """MFA setup response with secret and QR code"""
    secret: str
    qr_code_uri: str
    backup_codes: List[str]


class MFAVerifyRequest(BaseModel):
    """MFA verification request"""
    username: str
    totp_code: str = Field(..., min_length=6, max_length=8)
    backup_code: Optional[str] = None


class UserInfoResponse(BaseModel):
    """Current user info"""
    user_id: str
    username: str
    email: Optional[str] = None
    roles: List[str]
    mfa_enabled: bool
    mfa_enrolled: bool
