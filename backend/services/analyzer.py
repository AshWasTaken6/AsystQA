import time
from agents.planner import plan_steps
from agents.reviewer import review_code
from agents.security import security_check
from agents.tester import generate_tests
from agents.reporter import generate_report

def run_analysis(code, language):
    start = time.time()

    steps = plan_steps(language)
    status = []

    status.append("Planning complete")

    bugs = review_code(code, language)
    status.append("Review complete")

    security = security_check(code)
    status.append("Security complete")

    tests = generate_tests(code)
    status.append("Tests generated")

    report = generate_report(bugs, security)
    status.append("Report generated")

    end = time.time()

    return {
        "score": report["score"],
        "bugs": bugs,
        "security": security,
        "tests": tests,
        "summary": report["summary"],
        "processing_time": f"{round(end - start, 2)}s",
        "status": status + ["Done"]
    }