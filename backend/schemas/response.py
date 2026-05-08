from pydantic import BaseModel
from typing import List, Dict

class Issue(BaseModel):
    issue: str
    reason: str
    fix: str

class AnalyzeResponse(BaseModel):
    score: int
    bugs: List[Dict]
    security: List[Dict]
    tests: List[str]
    summary: str
    processing_time: str
    status: List[str]