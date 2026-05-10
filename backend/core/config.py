import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _load_local_env() -> None:
    """Load backend/.env without requiring python-dotenv."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    lines = env_path.read_text(encoding="utf-8").splitlines()
    index = 0
    while index < len(lines):
        raw_line = lines[index]
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            index += 1
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("-----BEGIN ") and " KEY-----" in value and "-----END " not in value:
            pem_lines = [value]
            index += 1
            while index < len(lines):
                pem_lines.append(lines[index].rstrip())
                if lines[index].strip().startswith("-----END "):
                    break
                index += 1
            value = "\n".join(pem_lines)
        else:
            value = _clean_env_value(value)
        os.environ.setdefault(key, value)
        index += 1


def _clean_env_value(value: str) -> str:
    """Strip quotes and unquoted inline comments from a dotenv value."""
    value = value.strip()
    quote: str | None = None

    for index, char in enumerate(value):
        if char in {"'", '"'}:
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            value = value[:index].rstrip()
            break

    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _env_list(name: str, default: List[str]) -> List[str]:
    value = os.getenv(name)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


_load_local_env()


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AsystQA Backend")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    allowed_origins: List[str] = field(
        default_factory=lambda: _env_list(
            "ALLOWED_ORIGINS",
            [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
                "http://localhost:5174",
                "http://127.0.0.1:5174",
                "http://localhost:5175",
                "http://127.0.0.1:5175",
            ],
        )
    )

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Security
    auth_required: bool = os.getenv("AUTH_REQUIRED", "false").lower() == "true"
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "RS256")
    jwt_private_key: Optional[str] = os.getenv("JWT_PRIVATE_KEY")
    jwt_public_key: Optional[str] = os.getenv("JWT_PUBLIC_KEY")
    jwt_secret_key: Optional[str] = os.getenv("JWT_SECRET_KEY")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    encryption_key: Optional[str] = os.getenv("ENCRYPTION_KEY")
    key_vault_url: Optional[str] = os.getenv("KEY_VAULT_URL")
    key_vault_token: Optional[str] = os.getenv("KEY_VAULT_TOKEN")

    mfa_required: bool = os.getenv("MFA_REQUIRED", "false").lower() == "true"

    data_dir: str = os.getenv("DATA_DIR", "data")

    audit_log_dir: str = os.getenv("AUDIT_LOG_DIR", "logs/audit")
    audit_remote_siem: bool = os.getenv("AUDIT_REMOTE_SIEM", "false").lower() == "true"
    audit_siem_url: Optional[str] = os.getenv("AUDIT_SIEM_URL")

    # Rate limiting
    rate_limit_enabled: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "100"))

    # Security headers
    enable_security_headers: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"
    hsts_max_age: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))
    csp_policy: str = os.getenv(
        "CSP_POLICY",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    )
    docs_csp_policy: str = os.getenv(
        "DOCS_CSP_POLICY",
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "font-src 'self' data: https://cdn.jsdelivr.net; "
        "connect-src 'self'"
    )

    # Pipeline settings
    pipeline_timeout_seconds: int = int(os.getenv("PIPELINE_TIMEOUT", "30"))
    agent_retry_attempts: int = int(os.getenv("AGENT_RETRY_ATTEMPTS", "2"))
    agent_timeout_seconds: float = float(os.getenv("AGENT_TIMEOUT_SECONDS", "10"))
    circuit_breaker_failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
    circuit_breaker_reset_seconds: int = int(os.getenv("CIRCUIT_BREAKER_RESET_SECONDS", "30"))

    # OpenTelemetry
    otlp_endpoint: Optional[str] = os.getenv("OTLP_ENDPOINT")


settings = Settings()
