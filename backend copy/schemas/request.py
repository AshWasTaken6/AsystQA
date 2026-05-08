from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to analyze.")
    language: str = Field(..., min_length=1, description="Programming language of the source.")
