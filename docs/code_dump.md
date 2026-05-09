# AsystQA Backend Code Dump

This document contains the complete source code from all backend files in the `backend copy` package.

---

## backend copy/README.md

> No README file exists in backend copy.

---

## backend copy/requirements.txt

```text
fastapi>=0.115.0,<1.0.0
uvicorn[standard]>=0.30.0,<1.0.0
```

---

## backend copy/__init__.py

```python
"""AsystQA backend package."""
```

---

## backend copy/main.py

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from core.config import settings

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": f"{settings.app_name} running"}
```

---

## backend copy/api/__init__.py

```python
"""API package for AsystQA."""
```

---

## backend copy/api/routes.py

```python
from fastapi import APIRouter

from core.pipeline import run_pipeline
from schemas.request import AnalyzeRequest
from schemas.response import AnalyzeResponse

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    result = run_pipeline(request.code, request.language)
    return AnalyzeResponse(**result)
```

---

## backend copy/core/config.py

```python
from dataclasses import dataclass, field
import os


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AsystQA Backend")
    api_prefix: str = os.getenv("API_PREFIX", "")
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if origin.strip()
        ]
    )


settings = Settings()
```

---

## backend copy/core/pipeline.py

```python
from agents.planner import run_planner
from agents.reporter import run_reporter
from agents.reviewer import run_reviewer
from agents.security import run_security
from agents.tester import run_tester
from utils.logger import get_logger

logger = get_logger(__name__)


def run_pipeline(code: str, language: str) -> dict:
    logger.info("Starting analysis pipeline for language=%s", language)

    planner_output = run_planner(code, language)
    reviewer_output = run_reviewer(code, language)
    security_output = run_security(code, language)
    tester_output = run_tester(code, language)

    aggregated = {
        "planner": planner_output,
        "reviewer": reviewer_output,
        "security": security_output,
        "tester": tester_output,
    }

    reporter_output = run_reporter(aggregated)
    logger.info("Completed analysis pipeline for language=%s", language)

    return {
        **aggregated,
        "reporter": reporter_output,
    }
```

---

## backend copy/agents/__init__.py

```python
"""Agent modules for AsystQA."""
```

---

## backend copy/agents/planner.py

```python
def run_planner(code: str, language: str) -> list[str]:
    normalized = language.lower().strip()
    line_count = len([line for line in code.splitlines() if line.strip()])

    plan = [
        f"Analyze the submitted {normalized or 'source'} code for quality, safety, and test coverage.",
        f"Inspect {line_count} non-empty lines to identify the main execution path and dependencies.",
        "Prepare consolidated findings for reviewer, security, and tester agents.",
    ]

    if normalized in {"python", "py"}:
        plan.append("Check imports, function boundaries, and exception handling patterns.")
    elif normalized in {"javascript", "typescript", "js", "ts"}:
        plan.append("Check async flows, component logic, and input handling paths.")

    return plan
```

---

## backend copy/agents/reviewer.py

```python
def run_reviewer(code: str, language: str) -> list[str]:
    findings: list[str] = []
    stripped_lines = [line.rstrip() for line in code.splitlines()]

    if not stripped_lines:
        return ["No code was provided for review."]

    if any(len(line) > 100 for line in stripped_lines):
        findings.append("Some lines exceed 100 characters and may be harder to maintain.")

    if "TODO" in code or "FIXME" in code:
        findings.append("Found unfinished work markers like TODO or FIXME.")

    if language.lower() in {"python", "py"} and "print(" in code:
        findings.append("Consider replacing ad-hoc print statements with structured logging.")

    if language.lower() in {"javascript", "typescript", "js", "ts"} and "console.log(" in code:
        findings.append("Consider removing debug console logging before production use.")

    if not findings:
        findings.append("No obvious maintainability issues were detected by the reviewer stub.")

    return findings
```

---

## backend copy/agents/security.py

```python
def run_security(code: str, language: str) -> list[str]:
    findings: list[str] = []
    lowered = code.lower()

    if "eval(" in lowered:
        findings.append("Potential unsafe dynamic execution detected via eval().")

    if "exec(" in lowered:
        findings.append("Potential unsafe dynamic execution detected via exec().")

    if "password" in lowered or "secret" in lowered or "api_key" in lowered:
        findings.append("Possible hardcoded sensitive data markers were detected.")

    if "innerhtml" in lowered:
        findings.append("Direct HTML injection patterns may introduce XSS risk.")

    if not findings:
        findings.append("No obvious high-risk patterns were detected by the security stub.")

    return findings
```

---

## backend copy/agents/tester.py

```python
def run_tester(code: str, language: str) -> list[str]:
    suggestions: list[str] = []

    if not code.strip():
        return ["No code was provided, so no test suggestions could be generated."]

    suggestions.append("Add a happy-path test that validates the expected primary behavior.")
    suggestions.append("Add at least one failure-path test for invalid or empty input.")

    normalized = language.lower().strip()
    if normalized in {"python", "py"}:
        suggestions.append("Use pytest parametrization to cover multiple input variants quickly.")
    elif normalized in {"javascript", "typescript", "js", "ts"}:
        suggestions.append("Add unit tests for edge cases and integration tests for exposed APIs.")
    else:
        suggestions.append("Add regression tests around the most business-critical logic branch.")

    return suggestions
```

---

## backend copy/agents/reporter.py

```python
from schemas.response import Report


def run_reporter(aggregated: dict[str, list[str]]) -> Report:
    issue_count = sum(len(items) for items in aggregated.values())
    score = max(0, 100 - (issue_count * 5))

    summary_parts = [
        f"Planner produced {len(aggregated['planner'])} steps.",
        f"Reviewer found {len(aggregated['reviewer'])} item(s).",
        f"Security found {len(aggregated['security'])} item(s).",
        f"Tester suggested {len(aggregated['tester'])} test improvement(s).",
    ]

    return Report(
        score=score,
        summary=" ".join(summary_parts),
    )
```

---

## backend copy/schemas/__init__.py

```python
"""Schemas package for AsystQA."""
```

---

## backend copy/schemas/request.py

```python
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to analyze.")
    language: str = Field(..., min_length=1, description="Programming language of the source.")
```

---

## backend copy/schemas/response.py

```python
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
```

---

## backend copy/utils/__init__.py

```python
"""Utility helpers for AsystQA."""
```

---

## backend copy/utils/logger.py

```python
import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
```
