import asyncio
import time
from uuid import uuid4

from agents.critic import run_critic
from agents.planner import run_planner
from agents.reporter import run_reporter
from agents.security import run_security
from agents.sentinel import run_sentinel
from agents.tester import run_tester
from core.context import get_correlation_id
from services.audit import audit_log
from services.memory import get_insights, update_memory
from services.metrics import increment_scan, observe_agent
from services.redaction import redact_secrets
from services.resilience import with_resilience
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


def _overall_confidence(reviewer: list, security: list, warnings: list) -> float:
    """Calculate overall confidence score based on issues found."""
    total_issues = len(reviewer) + len(security)
    if total_issues == 0:
        return 0.95
    if total_issues <= 2:
        return 0.85
    if total_issues <= 5:
        return 0.70
    return 0.50


# Global timing storage for agents
_agent_timings: dict[str, float] = {}


def _with_timing(name: str, func):
    """Decorator to measure agent execution time."""
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        _agent_timings[name] = round(elapsed, 4)
        return result
    return wrapper


async def run_pipeline(
    code: str,
    language: str,
    user_id: str = "anonymous",
    session_id: str | None = None,
) -> dict:
    """
    Execute full analysis pipeline with security controls.

    Security:
    - Secrets redacted before any processing
    - Original code never stored
    - All actions audit-logged
    - Results encrypted at rest
    """
    scan_id = str(uuid4())
    correlation_id = get_correlation_id() or str(uuid4())
    start = time.time()
    language_used = detect_language(code, language)

    logger.info(
        "Pipeline start: scan_id=%s lang=%s user=%s len=%d",
        scan_id, language_used, user_id, len(code)
    )

    # Clear previous timings
    _agent_timings.clear()

    # REDACT: Remove secrets before processing
    redacted_code, secret_map = redact_secrets(code, language_used)
    if secret_map:
        logger.warning("Redacted %d secrets from scan %s", len(secret_map), scan_id)

    warnings = []
    if secret_map:
        warnings.append({
            "type": "secret_redaction",
            "message": f"Redacted {len(secret_map)} potential secret(s) before analysis.",
        })

    # RUN AUTONOMOUS SWARM (feedback order is intentional)
    architect_initial = await _run_agent(
        "architect",
        run_planner,
        redacted_code,
        language_used,
        [],
        warnings,
    )
    sentinel_output = await _run_agent(
        "sentinel",
        run_sentinel,
        redacted_code,
        language_used,
        [],
        warnings,
        {"architect": architect_initial},
    )
    auditor_output = await _run_agent(
        "auditor",
        run_security,
        redacted_code,
        language_used,
        [],
        warnings,
        {"architect": architect_initial, "sentinel": sentinel_output},
    )
    critic_output = await _run_agent(
        "critic",
        run_critic,
        redacted_code,
        language_used,
        [],
        warnings,
        {"architect": architect_initial, "sentinel": sentinel_output, "auditor": auditor_output},
    )
    chaos_output = await _run_agent(
        "chaos_engineer",
        run_tester,
        redacted_code,
        language_used,
        [],
        warnings,
        {
            "architect": architect_initial,
            "sentinel": sentinel_output,
            "auditor": auditor_output,
            "critic": critic_output,
        },
    )
    architect_replan = await _run_agent(
        "architect_replan",
        run_planner,
        redacted_code,
        language_used,
        [],
        warnings,
        {
            "sentinel": sentinel_output,
            "auditor": auditor_output,
            "critic": critic_output,
            "chaos_engineer": chaos_output,
        },
    )

    planner_output = [*architect_initial, *architect_replan]
    reviewer_output = [*sentinel_output, *critic_output]
    security_output = auditor_output
    tester_output = chaos_output

    # REPORT
    with _timed("reporter"):
        aggregated = {
            "planner": planner_output,
            "reviewer": reviewer_output,
            "security": security_output,
            "tester": tester_output,
        }
        reporter_output = run_reporter(aggregated)

    # PERSIST
    update_memory(
        reviewer_output=reviewer_output,
        security_output=security_output,
        language=language_used,
        user_id=user_id
    )

    # AUDIT
    audit_log(
        action="scan.completed",
        outcome="success",
        resource="scan",
        resource_id=scan_id,
        metadata={
            "language": language_used,
            "review_issues": len(reviewer_output),
            "security_issues": len(security_output),
            "warnings": len(warnings),
            "redacted": len(secret_map),
        },
        user_id=user_id,
    )

    insights = {
        **get_insights(),
        "swarm": {
            "framework": "Zero-Trust, Maximum-Rigidity",
            "feedback_loop": [
                "architect.initial",
                "sentinel.deep_trace",
                "auditor.threat_model",
                "critic.formal_review",
                "chaos_engineer.adversarial_tests",
                "architect.replan",
            ],
            "agents": {
                "architect": len(planner_output),
                "sentinel": len(sentinel_output),
                "auditor": len(auditor_output),
                "critic": len(critic_output),
                "chaos_engineer": len(chaos_output),
            },
        },
    }
    increment_scan(language_used, "success")

    elapsed = round(time.time() - start, 2)
    confidence = _overall_confidence(reviewer_output, security_output, warnings)

    logger.info(
        "Pipeline complete: scan_id=%s issues=%d time=%.2fs",
        scan_id, len(reviewer_output) + len(security_output), elapsed
    )

    return {
        "scan_id": scan_id,
        "correlation_id": correlation_id,
        "planner": planner_output,
        "reviewer": reviewer_output,
        "security": security_output,
        "tester": tester_output,
        "reporter": reporter_output,
        "language": language_used,
        "processing_time": elapsed,
        "agent_timings": _agent_timings.copy(),
        "confidence": confidence,
        "warnings": warnings,
        "insights": insights,
        "redacted": len(secret_map) > 0,
        "session_id": session_id,
    }


def run_pipeline_sync(
    code: str,
    language: str,
    user_id: str = "anonymous",
    session_id: str | None = None,
) -> dict:
    """Synchronous wrapper for FastAPI using asyncio.run()."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, safe to use asyncio.run()
        return asyncio.run(run_pipeline(code, language, user_id, session_id))
    else:
        # Already in async context, shouldn't call from sync context
        logger.warning("run_pipeline_sync called from async context, use await run_pipeline() instead")
        return asyncio.run(run_pipeline(code, language, user_id, session_id))


class _timed:
    """Context manager for timing code blocks."""
    def __init__(self, name: str):
        self.name = name
        self.start = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.perf_counter() - self.start
        _agent_timings[self.name] = round(elapsed, 4)
        return False


async def _run_agent(
    name: str,
    func,
    code: str,
    language: str,
    fallback: list,
    warnings: list[dict],
    context: dict | None = None,
) -> list:
    """Run an agent with timeout/retry/circuit breaker and record partial-result warnings."""
    started = time.perf_counter()
    try:
        return await with_resilience(
            name,
            lambda: func(code, language, context or {}),
        )
    except Exception as exc:
        logger.exception("Agent failed: %s", name)
        warnings.append({
            "type": "agent_partial_result",
            "agent": name,
            "message": f"{name} failed; continuing with partial results.",
            "error": type(exc).__name__,
        })
        return fallback
    finally:
        elapsed = time.perf_counter() - started
        _agent_timings[name] = round(elapsed, 4)
        observe_agent(name, elapsed)
