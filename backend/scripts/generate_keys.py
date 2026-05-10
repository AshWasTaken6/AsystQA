#!/usr/bin/env python3
"""
Security Key Generation Utility
Generates cryptographic keys for AsystQA Zero Trust deployment.

Usage:
    python scripts/generate_keys.py [--output-dir ./keys]

Generated files:
    - jwt_private.pem       RSA private key for JWT signing
    - jwt_public.pem        RSA public key for JWT verification
    - encryption.key        Base64-encoded AES-256 key for data encryption
    - integrity.key         Secret for HMAC signatures
"""

import argparse
import base64
import os
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_jwt_keys(output_dir: Path) -> tuple[Path, Path]:
    """Generate RSA key pair for JWT signing (RS256)"""
    private_key = output_dir / "jwt_private.pem"
    public_key = output_dir / "jwt_public.pem"

    print("Generating JWT RSA key pair (2048-bit)...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_key.write_bytes(private_pem)
    public_key.write_bytes(public_pem)

    # Set restrictive permissions
    private_key.chmod(0o600)
    public_key.chmod(0o644)

    print(f"  OK Private key: {private_key} (600)")
    print(f"  OK Public key:  {public_key} (644)")
    return private_key, public_key


def generate_encryption_key(output_dir: Path) -> Path:
    """Generate 256-bit AES key for data encryption"""
    key_file = output_dir / "encryption.key"

    print("Generating AES-256 encryption key...")
    key = os.urandom(32)  # 256 bits
    key_b64 = base64.b64encode(key).decode()

    with open(key_file, "w") as f:
        f.write(key_b64)

    key_file.chmod(0o600)
    print(f"  OK Key: {key_file} (600)")
    return key_file


def generate_integrity_key(output_dir: Path) -> Path:
    """Generate HMAC-SHA256 secret for audit log integrity"""
    key_file = output_dir / "integrity.key"

    print("Generating HMAC-SHA256 integrity key...")
    key = os.urandom(32)
    key_hex = key.hex()

    with open(key_file, "w") as f:
        f.write(key_hex)

    key_file.chmod(0o600)
    print(f"  OK Key: {key_file} (600)")
    return key_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate cryptographic keys for AsystQA security"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("./keys"),
        help="Output directory for keys (default: ./keys)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing keys"
    )

    args = parser.parse_args()

    output_dir = args.output_dir
    if output_dir.exists() and not args.force:
        print(f"Error: {output_dir} exists. Use --force to overwrite.")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(output_dir, 0o700)

    print("\nAsystQA Key Generator v1.0")
    print(f"Output directory: {output_dir}\n")

    try:
        # Generate all keys
        generate_jwt_keys(output_dir)
        print()
        generate_encryption_key(output_dir)
        print()
        generate_integrity_key(output_dir)
        print()

        # Summary
        print("=" * 60)
        print("KEYS GENERATED SUCCESSFULLY")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Update .env with these values:")
        print("   JWT_PRIVATE_KEY=<base64 contents of keys/jwt_private.pem>")
        print("   JWT_PUBLIC_KEY=<base64 contents of keys/jwt_public.pem>")
        print("   ENCRYPTION_KEY=<contents of keys/encryption.key>")
        print("   AUDIT_INTEGRITY_SECRET=<contents of keys/integrity.key>")
        print("   MEMORY_INTEGRITY_SECRET=<generate another random value or reuse only for local dev>")
        print()
        print("2. Keep the keys directory private and out of git.")
        print()

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
