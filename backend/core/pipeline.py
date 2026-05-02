from backend.agents.planner import run_planner
from backend.agents.reporter import run_reporter
from backend.agents.reviewer import run_reviewer
from backend.agents.security import run_security
from backend.agents.tester import run_tester
from backend.utils.logger import get_logger

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
