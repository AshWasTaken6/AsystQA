from fastapi import APIRouter

from core.pipeline import run_pipeline
from schemas.request import AnalyzeRequest
from schemas.response import AnalyzeResponse
from services.memory import load_memory

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = run_pipeline(request.code, request.language)
    return AnalyzeResponse(**result)


@router.get("/history")
def history() -> dict:
    return load_memory()
