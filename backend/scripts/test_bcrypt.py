#!/usr/bin/env python3
"""Simple auth test without patching"""
import os
import sys
import traceback

from passlib.context import CryptContext

sys.path.insert(0, ".")
os.chdir("backend")


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

pw = "TestPass123!"
try:
    h = pwd_context.hash(pw)
    print(f"Hash: {h[:30]}")
    verified = pwd_context.verify(pw, h)
    print(f"Verify: {verified}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
