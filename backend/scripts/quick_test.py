#!/usr/bin/env python3
"""Quick sanity checks for security services"""

import json

import pyotp
from core.auth import _user_store, authenticate_user, create_user, generate_mfa_secret, verify_totp
from services.encryption import decrypt, encrypt
from services.redaction import redact_secrets

print("=== Encryption Test ===")
plain = "super secret data"
enc = encrypt(plain)
print(f"Envelope: {json.dumps(enc, indent=2)[:120]}...")
dec = decrypt(enc)
assert dec == plain, "Decrypt failed"
print("[OK] Encryption works\n")

print("=== Redaction Test ===")
code = 'api_key = "abc123xyz"; password = "hunter2"'
redacted, mapping = redact_secrets(code)
print(f"Original: {code}")
print(f"Redacted: {redacted}")
print(f"Mapping: {mapping}")
assert "abc123xyz" not in redacted, f"API key leaked: {redacted}"
assert "hunter2" not in redacted, f"Password leaked: {redacted}"
assert len(mapping) == 2, f"Expected 2 secrets, got {len(mapping)}: {mapping}"
print("[OK] Redaction works\n")

print("=== User Auth Test ===")

# Clean up if exists
if "testuser" in _user_store:
    del _user_store["testuser"]
user = create_user("testuser", "test@example.com", "TestPass123!", ["viewer"])
print(f"Created: {user.user_id}")
auth = authenticate_user("testuser", "TestPass123!")
assert auth is not None, "Authentication failed"
print("[OK] Auth works\n")

print("=== MFA Test ===")
mfa = generate_mfa_secret("testuser")
print(f"MFA secret: {mfa.secret[:8]}...")

totp = pyotp.TOTP(mfa.secret)
code = totp.now()

assert verify_totp(mfa.secret, code)
print("[OK] MFA works\n")

print("ALL CHECKS PASSED!")
