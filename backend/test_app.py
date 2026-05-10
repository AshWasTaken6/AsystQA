#!/usr/bin/env python3
"""Test script to verify app creation"""

try:
    print("Attempting to import main...")
    from main import app
    print("SUCCESS: App imported successfully")
    print(f"App type: {type(app)}")
    print(f"App title: {app.title}")
except Exception as e:
    print(f"ERROR: Failed to import app: {e}")
    import traceback
    traceback.print_exc()