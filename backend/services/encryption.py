"""
Encryption Service
Provides AES-256-GCM encryption for data at rest with envelope encryption support.
Integrates with HashiCorp Vault or uses local key derivation for key management.
"""

import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Dict, Optional

from core.config import settings
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionService:
    """
    Handles encryption/decryption of sensitive data at rest.
    Uses envelope encryption: data encrypted with DEK, DEK encrypted with KEK.
    Supports integration with external KMS (Vault, AWS KMS) for key management.
    """

    def __init__(self):
        self.kms_client = None
        self._master_key: Optional[bytes] = None
        self._initialize_keymaterial()

    def _initialize_keymaterial(self) -> None:
        """Initialize encryption keys from environment or secure storage"""
        # Try to load from Vault or KMS
        if settings.key_vault_url:
            self._load_from_vault()
        elif settings.encryption_key:
            # Use provided key (base64 encoded)
            try:
                self._master_key = base64.b64decode(settings.encryption_key)
                if len(self._master_key) != 32:
                    raise ValueError("Encryption key must be 32 bytes (256 bits)")
                logger.info("Encryption key loaded from environment")
            except Exception as e:
                logger.error(f"Failed to parse encryption key: {e}")
                raise
        else:
            # DEVELOPMENT: Derive key from hardcoded secret (DO NOT USE IN PRODUCTION)
            logger.warning("Using development encryption key - NOT SECURE FOR PRODUCTION")
            dev_secret = os.getenv("DEV_SECRET", "change-me-secret-in-production")
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b"asystqa-salt-2025",  # Fixed salt for dev
                iterations=100000,
                backend=default_backend()
            )
            self._master_key = kdf.derive(dev_secret.encode())

    def _load_from_vault(self) -> None:
        """Load master key from HashiCorp Vault"""
        try:
            import hvac
            client = hvac.Client(url=settings.key_vault_url)
            if settings.key_vault_token:
                client.token = settings.key_vault_token

            # Read key from Vault secret path
            secret = client.secrets.kv.v2.read_secret_version(
                path="asystqa/master-key"
            )
            key_b64 = secret["data"]["data"]["key"]
            self._master_key = base64.b64decode(key_b64)
            logger.info("Master key loaded from Vault")
        except Exception as e:
            logger.error(f"Failed to load key from Vault: {e}")
            raise

    def _generate_data_key(self) -> bytes:
        """Generate a random 256-bit data encryption key"""
        return secrets.token_bytes(32)

    def _encrypt_dek(self, dek: bytes) -> Dict[str, str]:
        """
        Encrypt data encryption key (DEK) with master key (KEK).
        Returns encrypted DEK + IV for storage.
        """
        if not self._master_key:
            raise ValueError("Master key not initialized")

        aesgcm = AESGCM(self._master_key)
        iv = secrets.token_bytes(12)  # 96-bit nonce for GCM

        encrypted_dek = aesgcm.encrypt(iv, dek, None)

        return {
            "encrypted_dek": base64.b64encode(encrypted_dek).decode(),
            "iv": base64.b64encode(iv).decode()
        }

    def _decrypt_dek(self, encrypted_dek_b64: str, iv_b64: str) -> bytes:
        """Decrypt data encryption key using master key"""
        if not self._master_key:
            raise ValueError("Master key not initialized")

        aesgcm = AESGCM(self._master_key)
        encrypted_dek = base64.b64decode(encrypted_dek_b64)
        iv = base64.b64decode(iv_b64)

        dek = aesgcm.decrypt(iv, encrypted_dek, None)
        return dek

    def encrypt_data(self, plaintext: str, key_id: str = "default") -> Dict[str, str]:
        """
        Encrypt data using envelope encryption.

        Args:
            plaintext: String data to encrypt
            key_id: Identifier for key version (for rotation)

        Returns:
            Dict containing encrypted payload, encrypted DEK, and IV
        """
        try:
            # Generate random data encryption key for this operation
            dek = self._generate_data_key()

            # Encrypt the data with DEK
            aesgcm = AESGCM(dek)
            nonce = secrets.token_bytes(12)
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

            # Encrypt the DEK with master key
            encrypted_dek_package = self._encrypt_dek(dek)

            # Build envelope
            envelope = {
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "encrypted_dek": encrypted_dek_package["encrypted_dek"],
                "iv": base64.b64encode(nonce).decode(),
                "dek_iv": encrypted_dek_package["iv"],
                "key_id": key_id,
                "algorithm": "AES-256-GCM",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "version": "1.0"
            }

            # Create hash for integrity verification
            data_hash = hashlib.sha256(plaintext.encode()).hexdigest()
            envelope["plaintext_hash"] = data_hash

            logger.info(f"Encrypted data: key_id={key_id}, size={len(plaintext)} bytes")
            return envelope

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, envelope: Dict[str, str]) -> str:
        """
        Decrypt data from envelope format.

        Args:
            envelope: Dict with ciphertext, encrypted_dek, iv, dek_iv

        Returns:
            Decrypted plaintext string
        """
        try:
            # Extract components
            ciphertext = base64.b64decode(envelope["ciphertext"])
            encrypted_dek = envelope["encrypted_dek"]
            dek_iv = envelope["dek_iv"]
            nonce = base64.b64decode(envelope["iv"])

            # Decrypt DEK
            dek = self._decrypt_dek(encrypted_dek, dek_iv)

            # Decrypt data
            aesgcm = AESGCM(dek)
            plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
            plaintext = plaintext_bytes.decode('utf-8')

            # Verify integrity
            if "plaintext_hash" in envelope:
                computed_hash = hashlib.sha256(plaintext_bytes).hexdigest()
                if computed_hash != envelope["plaintext_hash"]:
                    logger.error("Integrity check failed: hash mismatch")
                    raise ValueError("Data integrity verification failed")

            logger.info(f"Decrypted data: size={len(plaintext)} bytes")
            return plaintext

        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def rotate_key(self, old_key_path: str, new_key_path: str) -> None:
        """
        Rotate master key. Re-encrypt all stored data with new key.
        This is a simplified implementation - production would need batch re-encryption.
        """
        logger.info("Starting key rotation...")
        # Implementation would:
        # 1. Generate new master key
        # 2. Re-encrypt all stored envelopes with new KEK
        # 3. Update key metadata
        # 4. Keep old key for decryption of old data
        logger.warning("Key rotation not fully implemented - requires batch re-encryption")


# Global encryption service instance
encryption_service = EncryptionService()


# ============== Convenience Functions ==============

def encrypt(plaintext: str, key_id: str = "default") -> Dict[str, str]:
    """Convenience wrapper for encryption"""
    return encryption_service.encrypt_data(plaintext, key_id)


def decrypt(envelope: Dict[str, str]) -> str:
    """Convenience wrapper for decryption"""
    return encryption_service.decrypt_data(envelope)


def encrypt_file(filepath: str, output_path: Optional[str] = None) -> str:
    """
    Encrypt an entire file.
    Returns path to encrypted file.
    """
    with open(filepath, 'r') as f:
        content = f.read()

    envelope = encrypt(content)

    output = output_path or f"{filepath}.enc"
    with open(output, 'w') as f:
        json.dump(envelope, f, indent=2)

    logger.info(f"Encrypted file: {filepath} -> {output}")
    return output


def decrypt_file(filepath: str, output_path: Optional[str] = None) -> str:
    """
    Decrypt an encrypted file.
    Returns decrypted content or writes to file.
    """
    with open(filepath, 'r') as f:
        envelope = json.load(f)

    content = decrypt(envelope)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(content)
        logger.info(f"Decrypted file: {filepath} -> {output_path}")
        return output_path

    return content
