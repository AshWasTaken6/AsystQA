from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import planner, reporter, reviewer, security, tester


class AnalyzeRequest(BaseModel):
    code: str
    language: str


app = FastAPI(title="AsystQA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5173/"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AsystQA Backend Running"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    planner_output = planner.run(request.code, request.language)
    reviewer_output = reviewer.run(request.code, request.language)
    security_output = security.run(request.code, request.language)
    tester_output = tester.run(request.code, request.language)
    reporter_output = reporter.run(
        planner_output,
        reviewer_output,
        security_output,
        tester_output,
    )

    return {
        "planner": planner_output,
        "reviewer": reviewer_output,
        "security": security_output,
        "tester": tester_output,
        "reporter": reporter_output,
    }
