"""
Audit Logging Module
Provides structured, tamper-evident audit logging for all security-relevant events.
Follows immutable logging principles for compliance and forensics.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from fastapi import Request
from pydantic import BaseModel, Field
from utils.logger import get_logger

if TYPE_CHECKING:
    from core.auth import TokenData

logger = get_logger(__name__)


# ============== Audit Event Types ==============

class AuditAction(str, Enum):
    """Canonical audit action types"""
    # Authentication
    LOGIN_SUCCESS = "auth.login.success"
    LOGIN_FAILURE = "auth.login.failure"
    LOGOUT = "auth.logout"
    MFA_ENROLL = "auth.mfa.enroll"
    MFA_VERIFY = "auth.mfa.verify"
    MFA_BYPASS = "auth.mfa.bypass"
    TOKEN_REFRESH = "auth.token.refresh"
    TOKEN_REVOKE = "auth.token.revoke"

    # Authorization
    PERMISSION_DENIED = "authz.denied"
    ACCESS_GRANTED = "authz.granted"

    # Data Access
    CODE_SUBMIT = "code.submit"
    CODE_ANALYZE = "code.analyze"
    HISTORY_READ = "history.read"
    HISTORY_DELETE = "history.delete"
    DATA_EXPORT = "data.export"

    # Administration
    USER_CREATE = "admin.user.create"
    USER_UPDATE = "admin.user.update"
    USER_DELETE = "admin.user.delete"
    CONFIG_CHANGE = "admin.config.change"
    SYSTEM_HEALTH = "system.health"

    # Security Events
    SUSPICIOUS_ACTIVITY = "security.suspicious"
    RATE_LIMIT_EXCEEDED = "security.rate_limit"
    BRUTE_FORCE = "security.brute_force"
    ENCRYPTION_KEY_ROTATE = "security.key_rotate"

    # System
    SERVICE_START = "system.start"
    SERVICE_STOP = "system.stop"
    ERROR = "system.error"


class AuditOutcome(str, Enum):
    """Result of an audited action"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


# ============== Audit Log Schema ==============

class AuditActor(BaseModel):
    """Actor performing the action"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    ip: str
    user_agent: str
    session_id: Optional[str] = None
    service: Optional[str] = None  # For service-to-service calls


class AuditResource(BaseModel):
    """Resource being accessed"""
    type: str
    id: Optional[str] = None
    name: Optional[str] = None
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditContext(BaseModel):
    """Additional context for the event"""
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    language: Optional[str] = None
    code_size_bytes: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    """
    Structured audit event following common schema.
    Designed for immutable storage and easy querying.
    """
    # Core fields
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action: AuditAction
    outcome: AuditOutcome

    # Actor
    actor: AuditActor

    # Resource
    resource: Optional[AuditResource] = None

    # Context
    context: AuditContext = Field(default_factory=AuditContext)

    # Error details if outcome=failure
    error_message: Optional[str] = None
    error_code: Optional[str] = None

    # Additional metadata
    tags: List[str] = Field(default_factory=list)


# ============== Audit Log Storage ==============

class AuditLogger:
    """
    Centralized audit logger with immutable storage support.
    Writes to append-only JSONL files with optional remote SIEM shipping.
    """

    def __init__(
        self,
        log_dir: str = "logs/audit",
        enable_remote: bool = False,
        siem_url: Optional[str] = None
    ):
        self.log_dir = log_dir
        self.enable_remote = enable_remote
        self.siem_url = siem_url
        os.makedirs(log_dir, exist_ok=True)

    def _get_log_file_path(self) -> str:
        """Get current audit log file path (daily rotation)"""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        filename = f"audit-{date_str}.jsonl"
        return os.path.join(self.log_dir, filename)

    def log(
        self,
        action: AuditAction,
        outcome: AuditOutcome,
        actor: AuditActor,
        resource: Optional[AuditResource] = None,
        context: Optional[AuditContext] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Write an audit event to immutable storage.

        Returns: event_id for reference
        """
        event = AuditEvent(
            action=action,
            outcome=outcome,
            actor=actor,
            resource=resource,
            context=context or AuditContext(),
            error_message=error_message,
            error_code=error_code,
            tags=tags or []
        )

        event_json = event.model_dump_json(exclude_none=True) + "\n"
        log_file = self._get_log_file_path()

        try:
            # Append to file (atomic write)
            with open(log_file, "a") as f:
                f.write(event_json)

            logger.info(f"Audit log: {action} by {actor.username or actor.service}")

            # Ship to remote SIEM if enabled
            if self.enable_remote and self.siem_url:
                self._ship_to_siem(event)

            return event.event_id

        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            # Don't raise - audit logging should never break the application
            return event.event_id

    def _ship_to_siem(self, event: AuditEvent) -> None:
        """Ship event to remote SIEM (Elasticsearch, Splunk, etc.)"""
        # Implement SIEM integration here
        pass

    def query(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[AuditAction] = None,
        username: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filtering.
        In production, query from Elasticsearch/SIEM instead of file.
        """
        results = []
        log_files = sorted(
            f for f in os.listdir(self.log_dir)
            if f.startswith("audit-") and f.endswith(".jsonl")
        )

        for filename in log_files:
            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, "r") as f:
                for line in f:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Apply filters
                    if start_date:
                        event_time = datetime.fromisoformat(event["timestamp"])
                        if event_time < start_date:
                            continue

                    if end_date:
                        event_time = datetime.fromisoformat(event["timestamp"])
                        if event_time > end_date:
                            continue

                    if action and event.get("action") != action.value:
                        continue

                    if username and event.get("actor", {}).get("username") != username:
                        continue

                    results.append(event)
                    if len(results) >= limit:
                        break

            if len(results) >= limit:
                break

        return results

    def get_user_activity(
        self,
        username: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get all audit events for a specific user"""
        from datetime import timedelta
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        return self.query(start_date=start_date, username=username, limit=1000)

    def get_failed_logins(
        self,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get failed login attempts for brute force detection"""
        from datetime import timedelta
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours)
        return self.query(
            start_date=start_date,
            action=AuditAction.LOGIN_FAILURE,
            limit=1000
        )


# Global audit logger instance
audit_logger = AuditLogger()


# ============== Helper Functions ==============

def audit_login_attempt(
    username: str,
    ip: str,
    user_agent: str,
    success: bool,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    error: Optional[str] = None
) -> None:
    """Log authentication attempts"""
    action = AuditAction.LOGIN_SUCCESS if success else AuditAction.LOGIN_FAILURE
    outcome = AuditOutcome.SUCCESS if success else AuditOutcome.FAILURE

    actor = AuditActor(
        username=username if success else username,
        user_id=user_id,
        ip=ip,
        user_agent=user_agent,
        session_id=session_id
    )

    tags = ["authentication", "security"]
    if not success:
        tags.append("failed")

    audit_logger.log(
        action=action,
        outcome=outcome,
        actor=actor,
        resource=AuditResource(type="user", name=username),
        error_message=error,
        tags=tags
    )


def audit_code_submission(
    user_id: str,
    username: str,
    ip: str,
    language: str,
    code_size: int,
    session_id: str,
    success: bool = True
) -> None:
    """Log code analysis submissions"""
    actor = AuditActor(
        user_id=user_id,
        username=username,
        ip=ip,
        user_agent="service",  # Will be filled from request
        session_id=session_id
    )

    resource = AuditResource(
        type="code_submission",
        id=str(uuid.uuid4()),
        metadata={"language": language, "size_bytes": code_size}
    )

    context = AuditContext(
        language=language,
        code_size_bytes=code_size
    )

    audit_logger.log(
        action=AuditAction.CODE_SUBMIT,
        outcome=AuditOutcome.SUCCESS if success else AuditOutcome.FAILURE,
        actor=actor,
        resource=resource,
        context=context
    )


def audit_permission_denied(
    user_id: str,
    username: str,
    ip: str,
    required_permission: str,
    path: str,
    method: str
) -> None:
    """Log authorization failures"""
    actor = AuditActor(
        user_id=user_id,
        username=username,
        ip=ip,
        user_agent="",
        session_id=None
    )

    resource = AuditResource(
        type="endpoint",
        name=path,
        metadata={"method": method, "required_permission": required_permission}
    )

    audit_logger.log(
        action=AuditAction.PERMISSION_DENIED,
        outcome=AuditOutcome.FAILURE,
        actor=actor,
        resource=resource,
        error_message=f"Missing permission: {required_permission}",
        tags=["security", "authorization"]
    )


def audit_history_access(
    user_id: str,
    username: str,
    ip: str,
    resource_id: Optional[str] = None
) -> None:
    """Log history/record access"""
    actor = AuditActor(
        user_id=user_id,
        username=username,
        ip=ip,
        user_agent="",
        session_id=None
    )

    resource = AuditResource(
        type="history",
        id=resource_id
    )

    audit_logger.log(
        action=AuditAction.HISTORY_READ,
        outcome=AuditOutcome.SUCCESS,
        actor=actor,
        resource=resource
    )


def audit_mfa_event(
    username: str,
    user_id: str,
    ip: str,
    action: AuditAction,
    success: bool = True,
    error: Optional[str] = None
) -> None:
    """Log MFA-related events"""
    actor = AuditActor(
        username=username,
        user_id=user_id,
        ip=ip,
        user_agent="",
        session_id=None
    )

    outcome = AuditOutcome.SUCCESS if success else AuditOutcome.FAILURE
    resource = AuditResource(type="mfa", name=action.value)

    tags = ["mfa", "authentication"]
    if not success:
        tags.append("failed")

    audit_logger.log(
        action=action,
        outcome=outcome,
        actor=actor,
        resource=resource,
        error_message=error,
        tags=tags
    )


# ============== Request Context Extraction ==============

def extract_audit_actor_from_request(
    request: Request,
    token_data: Optional[TokenData] = None
) -> AuditActor:
    """
    Extract actor information from HTTP request and optional token.
    Used to populate audit logs for request handlers.
    """
    ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    session_id = request.headers.get("x-session-id")

    if token_data:
        return AuditActor(
            user_id=token_data.user_id,
            username=token_data.username,
            ip=ip,
            user_agent=user_agent,
            session_id=session_id or token_data.session_id
        )
    else:
        # Unauthenticated request
        return AuditActor(
            ip=ip,
            user_agent=user_agent,
            session_id=session_id
        )
