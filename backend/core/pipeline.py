import time  # 👈 ADD THIS

from agents.planner import run_planner
from agents.reporter import run_reporter
from agents.reviewer import run_reviewer
from agents.security import run_security
from agents.tester import run_tester
from utils.logger import get_logger

# 👇 ADD THIS
from services.memory import update_memory, get_insights

logger = get_logger(__name__)


def run_pipeline(code: str, language: str) -> dict:
    start = time.time()  # 👈 START TIMER

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

    # 👇 ADD MEMORY HERE (AFTER AGENTS RUN)
    update_memory(reviewer_output, security_output)
    insights = get_insights()

    end = time.time()  # 👈 END TIMER

    logger.info("Completed analysis pipeline for language=%s", language)

    return {
        **aggregated,
        "reporter": reporter_output,
        "processing_time": round(end - start, 2),  # 👈 ADD THIS
        "insights": insights,  # 👈 ADD THIS
    }