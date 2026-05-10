"""
Core Authentication Module
Implements JWT-based authentication with support for MFA, session management,
and token lifecycle controls following Zero Trust principles.
"""

import base64
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, List, Optional

import jwt
import pyotp
from core.config import settings
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from utils.logger import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# JWT configuration
JWT_ALGORITHM = settings.jwt_algorithm or "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

# In-memory session store (consider Redis for production)
_active_sessions: Dict[str, Dict[str, Any]] = {}
_revoked_tokens: set[str] = set()  # Simple blacklist


def _get_jwt_keypair() -> tuple[str, str, str]:
    """Return (algorithm, private_key, public_key) for JWT operations."""
    algorithm = (settings.jwt_algorithm or "RS256").upper()

    if algorithm.startswith("RS"):
        private_key = _normalize_pem_key(settings.jwt_private_key)
        public_key = _normalize_pem_key(settings.jwt_public_key)
        if not private_key or not public_key:
            logger.warning(
                "RSA JWT keys not configured. Falling back to HS256 with development secret."
            )
            secret = settings.jwt_secret_key or "demo_dev_secret_change_me"
            return "HS256", secret, secret

        try:
            jwt.algorithms.get_default_algorithms()[algorithm].prepare_key(private_key)
            jwt.algorithms.get_default_algorithms()[algorithm].prepare_key(public_key)
            return algorithm, private_key, public_key
        except Exception as e:
            logger.warning(
                "RSA JWT keys invalid or malformed (%s). Falling back to HS256 with development secret.",
                e
            )
            secret = settings.jwt_secret_key or "demo_dev_secret_change_me"
            return "HS256", secret, secret

    secret = settings.jwt_secret_key or "demo_dev_secret_change_me"
    return algorithm, secret, secret


def _normalize_pem_key(value: Optional[str]) -> Optional[str]:
    """Accept raw PEM, escaped-newline PEM, or base64-encoded PEM."""
    if not value:
        return None

    value = value.strip().strip('"').strip("'")
    if "\\n" in value:
        value = value.replace("\\n", "\n")

    if value.startswith("-----BEGIN"):
        return value

    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8").strip()
    except Exception:
        return value

    return decoded if decoded.startswith("-----BEGIN") else value


# ============== Data Models ==============

class Token(BaseModel):
    """JWT token response model"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    mfa_required: bool = False
    mfa_enrolled: bool = False


class TokenData(BaseModel):
    """Decoded token payload"""
    username: str
    user_id: str
    roles: List[str] = []
    session_id: str
    mfa_verified: bool = False
    exp: int


class UserCreate(BaseModel):
    """User registration request"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[^@]+@[^@]+\.[^@]+$")
    password: str = Field(..., min_length=8, max_length=128)
    roles: List[str] = Field(default_factory=lambda: ["viewer"])


class UserInDB(BaseModel):
    """User stored in database (includes hashed password)"""
    username: str
    email: str
    hashed_password: str
    user_id: str
    roles: List[str]
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    is_active: bool = True
    created_at: str
    last_login: Optional[str] = None


class MFASetup(BaseModel):
    """MFA enrollment response"""
    secret: str
    qr_code_uri: str
    backup_codes: List[str]


class MFAVerify(BaseModel):
    """MFA verification request"""
    username: str
    totp_code: str
    backup_code: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request with optional MFA"""
    username: str
    password: str
    mfa_code: Optional[str] = None


# ============== User Database (In-Memory for Demo) ==============
# In production, replace with PostgreSQL + pgcrypto

_user_store: Dict[str, UserInDB] = {}


def _get_user_db_path() -> str:
    """Get path to user database file"""
    import os

    from core.config import settings
    return os.path.join(settings.data_dir, "users.json")


def _load_users() -> Dict[str, UserInDB]:
    """Load users from persistent storage"""
    import json
    import os
    path = _get_user_db_path()
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r") as f:
            data = json.load(f)
        return {
            uid: UserInDB(**user_data)
            for uid, user_data in data.items()
        }
    except Exception as e:
        logger.error(f"Failed to load users: {e}")
        return {}


def _save_users(users: Dict[str, UserInDB]) -> None:
    """Save users to persistent storage"""
    import json
    import os
    path = _get_user_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        with open(path, "w") as f:
            json.dump(
                {uid: user.model_dump() for uid, user in users.items()},
                f,
                indent=2
            )
    except Exception as e:
        logger.error(f"Failed to save users: {e}")


def create_user(
    username: str,
    email: str,
    password: str,
    roles: Optional[List[str]] = None,
) -> UserInDB:
    """Create a new user with hashed password"""
    if username in _user_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )

    # Check for duplicate email
    for existing in _user_store.values():
        if existing.email == email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

    hashed_password = pwd_context.hash(password)
    user_id = str(uuid.uuid4())

    user = UserInDB(
        username=username,
        email=email,
        hashed_password=hashed_password,
        user_id=user_id,
        roles=roles or ["viewer"],
        mfa_enabled=False,
        is_active=True,
        created_at=datetime.now(timezone.utc).isoformat()
    )

    _user_store[username] = user
    _save_users(_user_store)

    logger.info(f"Created user: {username} (ID: {user_id})")
    return user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_user(username: str) -> Optional[UserInDB]:
    """Retrieve user by username"""
    return _user_store.get(username)


def get_user_by_id(user_id: str) -> Optional[UserInDB]:
    """Retrieve user by ID"""
    for user in _user_store.values():
        if user.user_id == user_id:
            return user
    return None


def update_user_mfa(username: str, secret: str, enabled: bool = True) -> None:
    """Update user MFA settings"""
    user = get_user(username)
    if user:
        user.mfa_secret = secret
        user.mfa_enabled = enabled
        _save_users(_user_store)


# ============== JWT Token Management ==============

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token with short expiration"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),  # JWT ID for tracking/revocation
        "type": "access"
    })

    algorithm, private_key, _ = _get_jwt_keypair()
    encoded = jwt.encode(
        to_encode,
        private_key,
        algorithm=algorithm
    )
    return encoded


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create refresh token with longer expiration"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
        "type": "refresh"
    })

    algorithm, private_key, _ = _get_jwt_keypair()
    encoded = jwt.encode(
        to_encode,
        private_key,
        algorithm=algorithm
    )
    return encoded


def decode_token(token: str) -> TokenData:
    """Decode and validate JWT token"""
    try:
        # Check if token is revoked
        if token in _revoked_tokens:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"}
            )

        algorithm, _, public_key = _get_jwt_keypair()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=[algorithm],
            options={"verify_exp": True}
        )

        username = payload.get("sub")
        user_id = payload.get("user_id")
        session_id = payload.get("session_id")
        roles = payload.get("roles", [])
        mfa_verified = payload.get("mfa_verified", False)

        if not username or not user_id or not session_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Verify session is still active
        if session_id not in _active_sessions:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or invalid",
                headers={"WWW-Authenticate": "Bearer"}
            )

        token_data = TokenData(
            username=username,
            user_id=user_id,
            roles=roles,
            session_id=session_id,
            mfa_verified=mfa_verified,
            exp=payload["exp"]
        )

        return token_data

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        ) from e


def revoke_token(token: str) -> None:
    """Add token to blacklist"""
    _revoked_tokens.add(token)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependency to get and validate current user from JWT token"""
    return decode_token(token)


async def get_optional_current_user(
    request: Request,
    token: Optional[str] = Depends(optional_oauth2_scheme),
) -> Optional[TokenData]:
    """Return decoded token data when supplied, otherwise allow anonymous local-dev use."""
    if token:
        return decode_token(token)

    if settings.auth_required or request.url.path.startswith((settings.api_prefix, "/api/v1")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return None


def create_session(user_id: str, username: str, ip: str, user_agent: str) -> str:
    """Create a new user session"""
    session_id = str(uuid.uuid4())
    _active_sessions[session_id] = {
        "user_id": user_id,
        "username": username,
        "ip": ip,
        "user_agent": user_agent,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat(),
        "mfa_verified": False
    }
    return session_id


def invalidate_session(session_id: str) -> None:
    """Invalidate a user session"""
    if session_id in _active_sessions:
        session = _active_sessions.pop(session_id)
        logger.info(f"Session invalidated: {session_id} (user: {session.get('username')})")


def update_session_activity(session_id: str) -> None:
    """Update session last activity timestamp"""
    if session_id in _active_sessions:
        _active_sessions[session_id]["last_activity"] = datetime.now(timezone.utc).isoformat()


def verify_session(session_id: str) -> bool:
    """Check if session is active and not expired"""
    if session_id not in _active_sessions:
        return False

    session = _active_sessions[session_id]
    last_activity = datetime.fromisoformat(session["last_activity"])

    # Auto-expire sessions after 24h of inactivity
    if datetime.now(timezone.utc) - last_activity > timedelta(hours=24):
        invalidate_session(session_id)
        return False

    return True


# ============== MFA Functions ==============

def generate_mfa_secret(username: str) -> MFASetup:
    """Generate TOTP secret for MFA enrollment"""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)

    # Generate provisioning URI for QR code
    provision_uri = totp.provisioning_uri(
        name=username,
        issuer_name=settings.app_name
    )

    # Generate backup codes (single-use)
    backup_codes = []
    for _ in range(10):
        code = uuid.uuid4().hex[:8].upper()
        backup_codes.append(code)

    return MFASetup(
        secret=secret,
        qr_code_uri=provision_uri,
        backup_codes=backup_codes
    )


def verify_totp(secret: str, code: str) -> bool:
    """Verify TOTP code"""
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def verify_backup_code(user: UserInDB, code: str) -> bool:
    """Verify backup code (requires storing used codes)"""
    # In production, maintain separate backup code store with used codes
    # For demo, accept any 8-char hex code
    return len(code) == 8 and code.isalnum()


# ============== Authentication Flow ==============

def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Verify username/password and return user"""
    user = get_user(username)
    if not user or not user.is_active:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def issue_tokens(
    user: UserInDB,
    request: Request,
    mfa_verified: bool = False
) -> Token:
    """Issue JWT access and refresh tokens"""
    # Create session
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    session_id = create_session(user.user_id, user.username, ip, user_agent)

    # Build token payload
    token_data = {
        "sub": user.username,
        "user_id": user.user_id,
        "roles": user.roles,
        "session_id": session_id,
        "mfa_verified": mfa_verified,
        "ip": ip
    }

    # Create tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({
        "sub": user.username,
        "user_id": user.user_id,
        "session_id": session_id
    })

    # Update session MFA status
    if mfa_verified:
        _active_sessions[session_id]["mfa_verified"] = True

    logger.info(
        f"Tokens issued for user={user.username}, session={session_id}, mfa_verified={mfa_verified}"
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=refresh_token,
        mfa_required=user.mfa_enabled,
        mfa_enrolled=user.mfa_enabled
    )


# ============== Permission System ==============

# Role definitions with permissions
ROLE_PERMISSIONS = {
    "viewer": ["code:analyze", "history:read"],
    "analyst": ["code:analyze", "history:read", "history:delete_own"],
    "admin": ["code:analyze", "history:read", "history:delete", "config:read", "config:write", "user:manage"]
}


def get_permissions_for_roles(roles: List[str]) -> set[str]:
    """Get all permissions for given roles"""
    perms = set()
    for role in roles:
        perms.update(ROLE_PERMISSIONS.get(role, []))
    return perms


def require_permission(permission: str):
    """Decorator to require specific permission for endpoint access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract request and token from kwargs
            token_data: TokenData = kwargs.get("token_data")

            if not token_data:
                # Try to get token from dependency injection
                for arg in args:
                    if isinstance(arg, TokenData):
                        token_data = arg
                        break

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            user_permissions = get_permissions_for_roles(token_data.roles)

            if permission not in user_permissions:
                logger.warning(
                    f"Permission denied: user={token_data.username}, "
                    f"roles={token_data.roles}, required={permission}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============== Initialization ==============

def init_default_users() -> None:
    """Initialize default users if none exist"""
    global _user_store
    _user_store = _load_users()

    if not _user_store:
        logger.info("Initializing default users...")
        # Create default admin user
        admin = create_user(
            username="admin",
            email="admin@asystqa.local",
            password="ChangeMeNow!",  # Must be changed on first login
            roles=["admin"]
        )
        logger.info(f"Default admin created: {admin.user_id}")
        # MFA setup will be required on first login
