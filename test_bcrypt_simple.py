#!/usr/bin/env python3
"""Simple auth test without patching"""
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

pw = "TestPass123!"
try:
    h = pwd_context.hash(pw)
    print(f"Hash: {h[:30]}")
    verified = pwd_context.verify(pw, h)
    print(f"Verify: {verified}")
except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
