from pydantic import BaseModel, Field
from typing import List, Dict, Any


class Report(BaseModel):
    score: int = Field(..., ge=0, le=100)
    summary: str
    risk: str
    issueCount: int
    issues: List[Dict[str, str]]
    tests: List[Dict[str, str]]


class AnalyzeResponse(BaseModel):
    planner: List[str]
    reviewer: List[Dict[str, Any]]   # 👈 CHANGED
    security: List[Dict[str, Any]]   # 👈 CHANGED
    tester: List[str]
    reporter: Report
    language: str

    processing_time: float           # 👈 NEW
    insights: Dict[str, Any]         # 👈 NEW