from core.auth import TokenData, get_optional_current_user
from core.authorization import Role, can_access_user_data
from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from schemas.request import AnalyzeRequest
from schemas.response import AnalyzeResponse
from services.memory import get_user_history, load_memory
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    request: Request,
    body: AnalyzeRequest,
    token_data: TokenData | None = Depends(get_optional_current_user),
) -> AnalyzeResponse:
    """
    Analyze source code. Requires authentication.
    """
    # Run pipeline with user context and redaction
    from core.pipeline import run_pipeline
    result = await run_pipeline(
        code=body.code,
        language=body.language,
        user_id=token_data.user_id if token_data else "anonymous",
        session_id=token_data.session_id if token_data else None,
    )

    return AnalyzeResponse(**result)


@router.get("/history")
def history(
    request: Request,
    token_data: TokenData | None = Depends(get_optional_current_user),
) -> dict:
    """
    Get analysis history. Non-admin users see only their own contribution.
    """
    if token_data is None:
        return load_memory()

    # Non-admin users see their own contribution count
    if Role.ADMIN.value not in token_data.roles:
        # Return only user's own history summary
        user_history = get_user_history(token_data.user_id, limit=50)
        total_scans = len(user_history)

        return {
            "total_scans": total_scans,
            "common_issues": {},
            "history": user_history
        }
    else:
        # Admin sees everything
        return load_memory()


@router.get("/agents")
def agents() -> dict:
    """List available analysis agents and their status"""
    from core.agent_registry import list_agents
    from services.resilience import circuit_status

    return {
        "agents": list_agents(),
        "circuits": circuit_status()
    }


@router.post("/scans", response_model=dict, status_code=202)
async def enqueue_scan(
    request: Request,
    body: AnalyzeRequest,
    token_data: TokenData | None = Depends(get_optional_current_user),
) -> dict:
    """
    Queue an asynchronous scan for processing.
    Returns scan ID for polling.
    """
    from services.tasks import create_scan_task

    scan_id = create_scan_task(
        code=body.code,
        language=body.language,
        user_id=token_data.user_id if token_data else "anonymous",
        session_id=token_data.session_id if token_data else None,
    )

    return {
        "scan_id": scan_id,
        "status": "queued",
        "result_url": f"/v1/results/{scan_id}"
    }


@router.get("/results/{scan_id}")
def scan_result(
    scan_id: str,
    token_data: TokenData | None = Depends(get_optional_current_user),
) -> JSONResponse:
    """
    Retrieve results of an asynchronous scan.
    Users can only access their own scans unless admin.
    """
    from services.tasks import get_scan_task

    task = get_scan_task(scan_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "type": "not_found",
                    "message": "Scan not found."
                }
            }
        )

    # Check authorization - users can only access their own scans
    task_owner = task.get("user_id")
    if token_data and not can_access_user_data(token_data, task_owner):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "type": "forbidden",
                    "message": "You cannot access this scan result."
                }
            }
        )

    if task["status"] != "completed":
        return JSONResponse(
            status_code=202,
            content=task
        )

    # Return the full result
    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(task["result"])
    )
