from pydantic import BaseModel, Field


class Report(BaseModel):
    score: int = Field(..., ge=0, le=100)
    summary: str


class AnalyzeResponse(BaseModel):
    planner: list[str]
    reviewer: list[str]
    security: list[str]
    tester: list[str]
    reporter: Report
