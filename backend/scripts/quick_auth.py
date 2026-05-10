#!/usr/bin/env python3
import sys

sys.path.insert(0, '.')

# Patch bcrypt version attribute
import bcrypt

if not hasattr(bcrypt, '__about__'):
    class About:
        __version__ = getattr(bcrypt, "__version__", "unknown")


    bcrypt.__about__ = About()  # type: ignore[attr-defined]

# Clean
from core.auth import _user_store, authenticate_user, create_user

_user_store.clear()

user = create_user("testuser", "test@example.com", "TestPass123!", ["viewer"])
print(f"Created user ID: {user.user_id}")

auth = authenticate_user("testuser", "TestPass123!")
print(f"Authenticated: {auth is not None}")

print("OK!")
