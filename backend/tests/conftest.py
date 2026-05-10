"""
Pytest configuration and shared fixtures for security testing.
"""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configure test environment before any tests run"""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DEBUG"] = "true"
    os.environ["JWT_PRIVATE_KEY"] = "test_private_key_for_jwt_signing_1234567890"
    os.environ["JWT_PUBLIC_KEY"] = "test_public_key_for_verification"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_jwt_signing_32bytes_long"
    # 32 random bytes base64 encoded
    os.environ["ENCRYPTION_KEY"] = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    os.environ["AUDIT_INTEGRITY_SECRET"] = "test_secret_key_for_hmac_32bytes_long"
    os.environ["DATA_DIR"] = "./test_data"
    os.environ["AUDIT_LOG_DIR"] = "./logs/test_audit"


@pytest.fixture
def client():
    """Create FastAPI test client"""
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for test user"""
    # Register user
    client.post("/api/v1/auth/register", json={
        "username": "testadmin",
        "email": "test@example.com",
        "password": "TestPass123!",
        "roles": ["admin"]
    })

    # Login
    response = client.post("/api/v1/auth/login", json={
        "username": "testadmin",
        "password": "TestPass123!"
    })

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def cleanup_test_data():
    """Clean up test data after tests"""
    yield
    # Cleanup logic here if needed
    test_dirs = [
        Path("./test_data"),
        Path("./logs/test_audit"),
    ]
    for d in test_dirs:
        if d.exists():
            import shutil
            shutil.rmtree(d)
