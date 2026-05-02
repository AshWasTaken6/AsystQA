from fastapi import APIRouter

from backend.core.pipeline import run_pipeline
from backend.schemas.request import AnalyzeRequest
from backend.schemas.response import AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = run_pipeline(request.code, request.language)
    return AnalyzeResponse(**result)
