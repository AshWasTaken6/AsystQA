import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from core.config import settings
from services.encryption import decrypt, encrypt
from utils.logger import get_logger

logger = get_logger(__name__)

# Use data directory from config
MEMORY_DIR = Path(settings.data_dir)
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_FILE = MEMORY_DIR / "history.json"
CHECKSUM_FILE = MEMORY_DIR / "history.json.sha256"
ENVELOPE_FILE = MEMORY_DIR / "history.json.enc"
SIGNATURE_FILE = MEMORY_DIR / "history.sig"  # Digital signature file
INTEGRITY_SECRET = os.getenv("MEMORY_INTEGRITY_SECRET", "change-me-securely")


def _get_envelope_path() -> Path:
    """Get encrypted envelope file path"""
    if ENVELOPE_FILE.parent == MEMORY_DIR:
        return MEMORY_FILE.with_name(f"{MEMORY_FILE.name}.enc")
    return ENVELOPE_FILE


def _get_signature_path() -> Path:
    """Get signature path next to the active memory file."""
    if SIGNATURE_FILE.parent == MEMORY_DIR:
        return MEMORY_FILE.with_name("history.sig")
    return SIGNATURE_FILE


def load_memory() -> Dict[str, Any]:
    """
    Load memory data from encrypted storage.
    Falls back to plaintext if encrypted file doesn't exist (migration).
    """
    # Try encrypted file first
    envelope_file = _get_envelope_path()
    if envelope_file.exists():
        try:
            with open(envelope_file, "r") as f:
                envelope = json.load(f)
            decrypted = decrypt(envelope)
            return json.loads(decrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt memory file: {e}")
            # Fallback to plaintext if available
            if MEMORY_FILE.exists():
                with open(MEMORY_FILE, "r") as f:
                    return json.load(f)
            raise

    # Plaintext fallback
    if MEMORY_FILE.exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)

    return {
        "total_scans": 0,
        "common_issues": {},
        "history": []
    }


def save_memory(data: Dict[str, Any]) -> None:
    """
    Encrypt and save memory data to disk with integrity protection.
    Uses envelope encryption with HMAC signature for tamper detection.
    """
    try:
        # Serialize data
        plaintext = json.dumps(data, indent=2, default=str)

        # Encrypt using envelope encryption
        envelope = encrypt(plaintext, key_id="memory")

        # Compute integrity signature
        envelope_bytes = json.dumps(envelope, separators=(",", ":")).encode()
        signature = hmac.new(
            INTEGRITY_SECRET.encode(),
            envelope_bytes,
            hashlib.sha256
        ).hexdigest()

        # Write signature file
        signature_file = _get_signature_path()
        with open(signature_file, "w") as f:
            f.write(f"{signature}\n")
            f.write(f"timestamp:{datetime.now(timezone.utc).isoformat()}\n")

        # Write encrypted envelope file atomically
        envelope_file = _get_envelope_path()
        envelope_file.parent.mkdir(parents=True, exist_ok=True)
        temp_file = envelope_file.with_suffix(".tmp")
        with open(temp_file, "wb") as f:
            f.write(envelope_bytes)

        # Atomic replace
        temp_file.replace(envelope_file)

        logger.debug(f"Memory saved: {len(data['history'])} history entries (signed)")

    except Exception as e:
        logger.error(f"Failed to save encrypted memory: {e}")
        raise


def verify_memory_integrity() -> bool:
    """
    Verify integrity of memory file using signature.
    Returns True if signature is valid.
    """
    try:
        envelope_file = _get_envelope_path()
        signature_file = _get_signature_path()
        if envelope_file.exists() and signature_file.exists():
            with open(envelope_file, "rb") as f:
                envelope_bytes = f.read()

            with open(signature_file, "r") as f:
                lines = f.readlines()
                stored_signature = lines[0].strip()

            expected = hmac.new(
                INTEGRITY_SECRET.encode(),
                envelope_bytes,
                hashlib.sha256
            ).hexdigest()

            if expected != stored_signature:
                logger.error("Memory signature verification FAILED - possible tampering")
                return False

            envelope = json.loads(envelope_bytes)
            decrypt(envelope)

        memory = load_memory()
        required_keys = {"total_scans", "common_issues", "history"}
        if not required_keys.issubset(memory.keys()):
            logger.error("Memory missing required keys")
            return False

        return (
            isinstance(memory["total_scans"], int)
            and isinstance(memory["common_issues"], dict)
            and isinstance(memory["history"], list)
        )

    except Exception as e:
        logger.error(f"Memory integrity check failed: {e}")
        return False


def update_memory(reviewer_output: list, security_output: list, language: str, user_id: str = "anonymous") -> None:
    """
    Update memory with new analysis results.
    Tracks statistics and maintains audit trail.
    """
    memory = load_memory()

    memory["total_scans"] += 1

    # Track all issues (both reviewer and security findings)
    all_outputs = reviewer_output + security_output
    for item in all_outputs:
        issue = item.get("issue", "Unknown issue")
        memory["common_issues"][issue] = memory["common_issues"].get(issue, 0) + 1

    # Add to history with user tracking
    memory["history"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "user_id": user_id,
        "review_issues": len(reviewer_output),
        "security_issues": len(security_output),
        "issue_total": len(all_outputs),
    })

    # Keep only last 500 entries (increase from 50 for better history)
    memory["history"] = memory["history"][-500:]

    save_memory(memory)


def get_insights() -> Dict[str, Any]:
    """
    Get aggregated insights from memory.
    Returns top common issues and total scan count.
    """
    memory = load_memory()

    # Sort issues by frequency
    sorted_issues = sorted(
        memory["common_issues"].items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "total_scans": memory["total_scans"],
        "top_issues": sorted_issues[:5],
        "recent_count": len(memory["history"])
    }


def get_user_history(user_id: str, limit: int = 50) -> list:
    """Get analysis history for a specific user"""
    memory = load_memory()
    user_entries = [
        entry for entry in memory["history"]
        if entry.get("user_id") == user_id
    ]
    return sorted(
        user_entries,
        key=lambda x: x["timestamp"],
        reverse=True
    )[:limit]


def clear_history(keep_recent: int = 0) -> int:
    """
    Clear old history entries.
    Returns number of entries removed.
    """
    memory = load_memory()
    original_count = len(memory["history"])

    if keep_recent > 0:
        memory["history"] = memory["history"][-keep_recent:]
    else:
        memory["history"] = []

    save_memory(memory)
    removed = original_count - len(memory["history"])
    logger.info(f"Cleared {removed} history entries")
    return removed


def memory_store_writable() -> bool:
    """Check if memory storage is writable"""
    try:
        test_file = MEMORY_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True
    except Exception:
        return False


def backup_memory() -> Path | None:
    """Write a JSON backup of the current memory plus a SHA-256 sidecar."""
    try:
        backup_dir = MEMORY_FILE.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"history-{timestamp}.json"
        payload = json.dumps(load_memory(), indent=2, default=str)
        backup_path.write_text(payload, encoding="utf-8")

        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        checksum_path = backup_path.with_suffix(".json.sha256")
        checksum_path.write_text(f"{checksum}\n", encoding="utf-8")
        return backup_path
    except Exception as e:
        logger.error(f"Memory backup failed: {e}")
        return None


# ============== Migration Utilities ==============

def migrate_to_encrypted() -> bool:
    """
    Migrate plaintext memory to encrypted storage.
    Should be run once during deployment.
    """
    envelope_file = _get_envelope_path()
    if envelope_file.exists():
        logger.info("Encrypted memory already exists")
        return False

    if not MEMORY_FILE.exists():
        logger.info("No existing memory found")
        return False

    try:
        # Load plaintext
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)

        # Encrypt and save
        save_memory(data)

        # Backup original
        backup_file = MEMORY_FILE.with_suffix(".backup")
        MEMORY_FILE.replace(backup_file)

        logger.info(f"Migration complete: {backup_file} (backup), {envelope_file} (encrypted)")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
