import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from core.config import settings
from core.context import get_correlation_id
from fastapi import Request
from utils.logger import get_logger

logger = get_logger(__name__)


# ============== Configuration ==============

_BACKEND_DIR = Path(__file__).resolve().parents[1]
_configured_audit_dir = Path(settings.audit_log_dir)
AUDIT_DIR = _configured_audit_dir if _configured_audit_dir.is_absolute() else _BACKEND_DIR / _configured_audit_dir
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
AUDIT_HASH_FILE = AUDIT_DIR / "audit.hashes"  # For integrity chain
INTEGRITY_SECRET = os.getenv("AUDIT_INTEGRITY_SECRET", "change-me-in-production")


# ============== Immutable Audit Logger ==============

def audit_log(
    *,
    action: str,
    outcome: str,
    resource: str,
    resource_id: Optional[str] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Write an immutable audit log entry.

    security: This function is designed to never fail, even if storage is full.
    Log entries are appended atomically and hashed for integrity verification.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    client_host = request.client.host if request and request.client else None
    user_agent = request.headers.get("user-agent") if request else None

    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "event_id": str(uuid4()),
        "correlation_id": get_correlation_id(),
        "actor": {
            "user_id": user_id,
            "ip": client_host,
            "user_agent": user_agent,
        },
        "action": action,
        "resource": resource,
        "resource_id": resource_id,
        "outcome": outcome,
        "metadata": metadata or {},
    }

    try:
        # 1. Serialize entry
        entry_json = json.dumps(entry, separators=(",", ":"), default=str)
        entry_hash = hashlib.sha256(entry_json.encode()).hexdigest()

        # 2. Write entry atomically
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(entry_json + "\n")

        # 3. Update integrity chain (HMAC for tamper detection)
        update_integrity_chain(entry_hash)

        logger.debug(
            "Audit logged: action=%s, outcome=%s, actor=%s",
            action, outcome, user_id or "system"
        )

    except Exception as e:
        # Audit logging should never break the application
        logger.error(f"Failed to write audit log: {e}")


# ============== Integrity Verification ==============

def update_integrity_chain(entry_hash: str) -> None:
    """
    Update integrity chain by appending hash to chain file.
    Uses HMAC for tamper detection (requires secret key).
    """
    try:
        # Get previous hash
        prev_hash = ""
        if AUDIT_HASH_FILE.exists():
            with AUDIT_HASH_FILE.open("r") as f:
                lines = f.readlines()
                if lines:
                    prev_hash = lines[-1].strip()  # Last line is previous hash

        # Compute chain hash: HMAC(prev_hash + new_hash)
        chain_input = f"{prev_hash}:{entry_hash}"
        chain_hash = hmac.new(
            INTEGRITY_SECRET.encode(),
            chain_input.encode(),
            hashlib.sha256
        ).hexdigest()

        # Append to chain file
        with AUDIT_HASH_FILE.open("a") as f:
            f.write(f"{chain_hash}\n")

    except Exception as e:
        logger.warning(f"Failed to update integrity chain: {e}")


def verify_integrity(backtrack: int = 100) -> bool:
    """
    Verify the integrity of the audit log by checking the hash chain.
    Returns True if all entries in the chain are intact.

    Args:
        backtrack: Number of recent entries to verify (default 100)
    """
    try:
        if not AUDIT_FILE.exists() or not AUDIT_HASH_FILE.exists():
            logger.warning("Audit files not found for integrity check")
            return False

        with AUDIT_FILE.open("r") as f:
            entries = f.readlines()

        with AUDIT_HASH_FILE.open("r") as f:
            chain_hashes = [line.strip() for line in f.readlines()]

        if len(entries) != len(chain_hashes):
            logger.error(
                f"Integrity mismatch: {len(entries)} entries, {len(chain_hashes)} chain hashes"
            )
            return False

        # Verify last N entries
        start_idx = max(0, len(entries) - backtrack)
        prev_hash = ""

        for i in range(start_idx, len(entries)):
            entry = entries[i].strip()
            entry_hash = hashlib.sha256(entry.encode()).hexdigest()
            chain_hash = chain_hashes[i]

            # Recompute chain hash
            chain_input = f"{prev_hash}:{entry_hash}"
            expected = hmac.new(
                INTEGRITY_SECRET.encode(),
                chain_input.encode(),
                hashlib.sha256
            ).hexdigest()

            if expected != chain_hash:
                logger.error(f"Integrity violation at entry {i}")
                return False

            prev_hash = chain_hash

        logger.info(f"Integrity verified for last {len(entries) - start_idx} entries")
        return True

    except Exception as e:
        logger.error(f"Integrity verification failed: {e}")
        return False


# ============== Log Rotation & Retention ==============

def rotate_logs_if_needed(max_age_days: int = 7, max_size_mb: int = 100) -> None:
    """
    Rotate audit logs based on age and size.
    Compresses old logs for archival.
    """
    try:
        if not AUDIT_FILE.exists():
            return

        stat = AUDIT_FILE.stat()
        file_age = datetime.now(UTC) - datetime.fromtimestamp(stat.st_mtime, tz=UTC)
        file_size_mb = stat.st_size / (1024 * 1024)

        # Rotate if too old or too large
        needs_rotation = (
            file_age > timedelta(days=max_age_days) or
            file_size_mb > max_size_mb
        )

        if needs_rotation:
            timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
            archive = AUDIT_DIR / f"audit-{timestamp}.jsonl.gz"

            # Compress current log
            import gzip
            with AUDIT_FILE.open("rb") as f_in:
                with gzip.open(archive, "wb") as f_out:
                    f_out.writelines(f_in)

            # Truncate current log (create new empty with hash chain continuity)
            # Move current chain to archive
            if AUDIT_HASH_FILE.exists():
                chain_archive = AUDIT_DIR / f"chain-{timestamp}.txt"
                AUDIT_HASH_FILE.replace(chain_archive)
                # Create new empty chain
                AUDIT_HASH_FILE.write_text("")

            # Clear current log
            AUDIT_FILE.write_text("")

            logger.info(f"Audit logs rotated: {archive}")

    except Exception as e:
        logger.error(f"Log rotation failed: {e}")


# ============== Query & Analysis ==============

def query_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> list[dict]:
    """
    Query audit logs with filtering.
    For production, implement indexed query via Elasticsearch.
    """
    results = []

    try:
        if not AUDIT_FILE.exists():
            return []

        with AUDIT_FILE.open("r") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Apply filters
                    if action and entry.get("action") != action:
                        continue
                    if user_id and entry.get("actor", {}).get("user_id") != user_id:
                        continue

                    ts = datetime.fromisoformat(entry["timestamp"])
                    if start_date and ts < start_date:
                        continue
                    if end_date and ts > end_date:
                        continue

                    results.append(entry)

                    if len(results) >= limit:
                        break

                except json.JSONDecodeError:
                    continue

        return results

    except Exception as e:
        logger.error(f"Audit query failed: {e}")
        return []


def get_audit_statistics(days: int = 7) -> dict:
    """
    Get audit statistics for security monitoring.
    """
    start = datetime.now(UTC) - timedelta(days=days)

    logs = query_audit_logs(start_date=start, limit=10000)

    stats: dict[str, Any] = {
        "total_events": len(logs),
        "by_action": {},
        "by_outcome": {},
        "failed_logins": 0,
        "unique_users": set(),
        "unique_ips": set()
    }

    for entry in logs:
        action = entry.get("action", "unknown")
        outcome = entry.get("outcome", "unknown")

        stats["by_action"][action] = stats["by_action"].get(action, 0) + 1
        stats["by_outcome"][outcome] = stats["by_outcome"].get(outcome, 0) + 1

        if action == "auth.login.failure":
            stats["failed_logins"] += 1

        if user_id := entry.get("actor", {}).get("user_id"):
            stats["unique_users"].add(user_id)

        if ip := entry.get("actor", {}).get("ip"):
            stats["unique_ips"].add(ip)

    stats["unique_users"] = list(stats["unique_users"])
    stats["unique_ips"] = list(stats["unique_ips"])

    return stats


# ============== Anomaly Detection Helpers ==============

def detect_brute_force(
    ip: Optional[str] = None,
    user_id: Optional[str] = None,
    window_minutes: int = 5,
    threshold: int = 5
) -> bool:
    """
    Detect brute force attacks by counting failed logins.
    Returns True if threshold exceeded.
    """
    window = timedelta(minutes=window_minutes)
    start = datetime.now(UTC) - window

    logs = query_audit_logs(
        action="auth.login.failure",
        start_date=start,
        limit=1000
    )

    count = 0
    for entry in logs:
        actor = entry.get("actor", {})
        if ip and actor.get("ip") == ip:
            count += 1
        if user_id and actor.get("user_id") == user_id:
            count += 1

    return count >= threshold
