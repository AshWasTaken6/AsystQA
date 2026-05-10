import asyncio

import pytest
from core.config import settings
from httpx import ASGITransport, AsyncClient
from main import app
from services import audit, memory, tasks


def _isolate_memory(monkeypatch, tmp_path):
    memory_file = tmp_path / "history.json"
    checksum_file = tmp_path / "history.json.sha256"
    monkeypatch.setattr(memory, "MEMORY_FILE", memory_file)
    monkeypatch.setattr(memory, "CHECKSUM_FILE", checksum_file)
    monkeypatch.setattr(audit, "AUDIT_FILE", tmp_path / "audit.jsonl")
    monkeypatch.setattr(tasks, "_TASKS", {})


@pytest.mark.anyio
async def test_health_endpoints(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        healthz = await client.get("/healthz")
        readyz = await client.get("/readyz")
        livez_response = await client.get("/livez")

    assert healthz.json() == {"status": "ok"}
    assert readyz.json() == {"status": "ready"}
    livez = livez_response.json()
    assert livez["status"] == "alive"
    assert livez["memory_integrity"] is True
    assert livez["memory_writable"] is True


@pytest.mark.anyio
async def test_analyze_returns_trace_metadata_and_redacts_secrets(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/analyze",
            json={
                "code": "const api_key = 'abc123'; console.log(api_key);",
                "language": "JavaScript",
                "filename": "../token-demo.js",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]

    payload = response.json()
    assert payload["scan_id"]
    assert payload["correlation_id"] == response.headers["X-Correlation-ID"]
    assert payload["language"] == "javascript"
    assert set(payload["agent_timings"]) == {"planner", "reviewer", "security", "tester", "reporter"}
    assert 0 <= payload["confidence"] <= 1
    assert any(warning["type"] == "secret_redaction" for warning in payload["warnings"])
    assert payload["insights"]["total_scans"] == 1


@pytest.mark.anyio
async def test_unsupported_language_returns_structured_validation_error(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/analyze",
            json={"code": "hello", "language": "brainfreeze"},
        )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["type"] == "validation_error"
    assert payload["error"]["correlation_id"] == response.headers["X-Correlation-ID"]


@pytest.mark.anyio
async def test_metrics_endpoint_exposes_prometheus_payload(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "asystqa_request_duration_seconds" in response.text or "prometheus_client is not installed" in response.text


@pytest.mark.anyio
async def test_v1_analyze_and_agent_registry(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        analyze_response = await client.post(
            "/v1/analyze",
            json={"code": "print('hello')", "language": "python"},
        )
        agents_response = await client.get("/v1/agents")

    assert analyze_response.status_code == 200
    assert analyze_response.json()["language"] == "python"
    assert agents_response.status_code == 200
    assert {agent["name"] for agent in agents_response.json()["agents"]} == {
        "planner",
        "reviewer",
        "security",
        "tester",
    }


@pytest.mark.anyio
async def test_auth_can_be_required_and_token_allows_history(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "auth_required", True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        blocked = await client.get("/v1/history")
        token_response = await client.post(
            "/v1/auth/token",
            json={"username": "admin@asystqa.com", "password": "admin123"},
        )
        token = token_response.json()["access_token"]
        allowed = await client.get("/v1/history", headers={"Authorization": f"Bearer {token}"})

    assert blocked.status_code == 401
    assert token_response.status_code == 200
    assert allowed.status_code == 200


@pytest.mark.anyio
async def test_async_scan_lifecycle(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        queued = await client.post(
            "/v1/scans",
            json={"code": "const token = 'abc'; console.log(token);", "language": "javascript"},
        )
        assert queued.status_code == 202
        scan_id = queued.json()["scan_id"]

        result = None
        for _ in range(20):
            poll = await client.get(f"/v1/results/{scan_id}")
            if poll.status_code == 200:
                result = poll.json()
                break
            await asyncio.sleep(0.05)

    assert result is not None
    assert result["scan_id"] == scan_id
    assert result["reporter"]["issueCount"] >= 1


def test_memory_backup(monkeypatch, tmp_path):
    _isolate_memory(monkeypatch, tmp_path)
    memory.save_memory({"total_scans": 0, "common_issues": {}, "history": []})

    backup_path = memory.backup_memory()

    assert backup_path is not None
    assert backup_path.exists()
    assert backup_path.with_suffix(".json.sha256").exists()
