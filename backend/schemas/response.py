from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Report(BaseModel):
    score: int = Field(..., ge=0, le=100)
    summary: str
    risk: str
    issueCount: int
    issues: List[Dict[str, str]]
    tests: List[Dict[str, str]]


class AnalyzeResponse(BaseModel):
    scan_id: str
    correlation_id: str | None = None
    planner: List[str]
    reviewer: List[Dict[str, Any]]   # 👈 CHANGED
    security: List[Dict[str, Any]]   # 👈 CHANGED
    tester: List[str]
    reporter: Report
    language: str
    session_id: str | None = None    # 👈 NEW
    processing_time: float           # 👈 NEW
    agent_timings: Dict[str, float]
    confidence: float = Field(..., ge=0, le=1)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    insights: Dict[str, Any]         # 👈 NEW
    redacted: bool = False           # 👈 NEW


class AcceptedScanResponse(BaseModel):
    scan_id: str
    status: str
    result_url: str
