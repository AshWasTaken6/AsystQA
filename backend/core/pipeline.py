import time

from agents.planner import run_planner
from agents.reporter import run_reporter
from agents.reviewer import run_reviewer
from agents.security import run_security
from agents.tester import run_tester
from services.memory import update_memory, get_insights
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_language(code: str, requested_language: str) -> str:
    normalized = (requested_language or "").strip().lower()
    if normalized and normalized not in {"auto", "auto detect", "detect", "unknown"}:
        return normalized

    lowered = code.lower()
    if "<?php" in lowered or "echo " in lowered:
        return "php"
    if "console.log(" in lowered or "function " in lowered or "=>" in lowered:
        return "javascript"
    if "def " in lowered or "import " in lowered or "print(" in lowered:
        return "python"
    if "public static void main" in lowered or "system.out.println" in lowered:
        return "java"
    if "<html" in lowered or "</html>" in lowered:
        return "html"
    return "unknown"


def run_pipeline(code: str, language: str) -> dict:
    start = time.time()
    language_used = detect_language(code, language)

    logger.info("Starting analysis pipeline for language=%s", language_used)

    planner_output = run_planner(code, language_used)
    reviewer_output = run_reviewer(code, language_used)
    security_output = run_security(code, language_used)
    tester_output = run_tester(code, language_used)

    aggregated = {
        "planner": planner_output,
        "reviewer": reviewer_output,
        "security": security_output,
        "tester": tester_output,
    }

    reporter_output = run_reporter(aggregated)

    # 👇 ADD MEMORY HERE (AFTER AGENTS RUN)
    update_memory(reviewer_output, security_output, language_used)
    insights = get_insights()

    end = time.time()

    logger.info("Completed analysis pipeline for language=%s", language_used)

    return {
        **aggregated,
        "reporter": reporter_output,
        "language": language_used,
        "processing_time": round(end - start, 2),
        "insights": insights,
    }