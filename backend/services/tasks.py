import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from core.pipeline import run_pipeline
from fastapi.encoders import jsonable_encoder

_TASKS: dict[str, dict] = {}


def create_scan_task(code: str, language: str, user_id: str = "anonymous", session_id: str | None = None) -> str:
    scan_id = str(uuid4())
    _TASKS[scan_id] = {
        "scan_id": scan_id,
        "status": "queued",
        "created_at": datetime.now(UTC).isoformat(),
        "user_id": user_id,
        "result": None,
        "error": None,
    }
    asyncio.create_task(_execute_scan(scan_id, code, language, user_id, session_id))
    return scan_id


async def _execute_scan(scan_id: str, code: str, language: str, user_id: str, session_id: str | None) -> None:
    _TASKS[scan_id]["status"] = "running"
    try:
        result = await run_pipeline(code, language, user_id=user_id, session_id=session_id)
        result["scan_id"] = scan_id
        _TASKS[scan_id]["result"] = jsonable_encoder(result)
        _TASKS[scan_id]["status"] = "completed"
    except Exception as exc:
        _TASKS[scan_id]["status"] = "failed"
        _TASKS[scan_id]["error"] = {"type": type(exc).__name__, "message": str(exc)}


def get_scan_task(scan_id: str) -> dict | None:
    return _TASKS.get(scan_id)
