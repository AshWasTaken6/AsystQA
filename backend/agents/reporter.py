from typing import Any

from schemas.response import Report


def _classify_severity(issue_text: str, source: str) -> str:
    lowered = issue_text.lower()
    critical_keywords = ["syntax", "nameerror", "unboundlocalerror", "typeerror", "zerodivisionerror", "indexerror"]
    high_keywords = ["hardcoded", "unsafe", "eval", "exec", "xss", "vulnerability", "risk", "credential"]
    medium_keywords = ["too many print", "log", "todo", "fixme", "lines exceed", "unfinished", "maintainability"]
    if any(keyword in lowered for keyword in critical_keywords):
        return "CRITICAL"
    if any(keyword in lowered for keyword in high_keywords):
        return "CRITICAL"
    if any(keyword in lowered for keyword in medium_keywords):
        return "WARNING"
    if source == "security":
        return "CRITICAL"
    return "WARNING"


def _build_issue(entry: dict[str, Any], source: str) -> dict[str, Any]:
    title = entry.get("issue", "Issue found")
    description = entry.get("fix") or entry.get("impact") or "Review this finding."
    category = entry.get("category") or ("Security" if source == "security" else "Maintainability")
    severity = entry.get("severity") or _classify_severity(
        f"{title} {entry.get('predictedException', '')}",
        source,
    )
    issue = {
        "severity": severity,
        "category": category,
        "title": title,
        "text": description,
        "source": source,
    }
    if "lineNumber" in entry:
        issue["lineNumber"] = entry["lineNumber"]
    if "predictedException" in entry:
        issue["predictedException"] = entry["predictedException"]
    if "rootCause" in entry:
        issue["rootCause"] = entry["rootCause"]
    if "agent" in entry:
        issue["agent"] = entry["agent"]
    if "recovery" in entry:
        issue["recovery"] = entry["recovery"]
    if "owasp" in entry:
        issue["owasp"] = entry["owasp"]
    return issue


def _build_risk(score: int, issues: list[dict[str, Any]]) -> str:
    if not issues:
        return "Low"

    severities = {issue.get("severity", "").lower() for issue in issues}

    if "critical" in severities or "high" in severities:
        return "High"
    if "warning" in severities or "medium" in severities:
        return "Medium"

    if score >= 80:
        return "Low"
    if score >= 55:
        return "Medium"
    return "High"


def _score_from_findings(reviewer: list[Any], security: list[Any]) -> int:
    findings = [
        item for item in reviewer + security
        if isinstance(item, dict)
    ]
    if not findings:
        return 95

    score = max(0, 100 - (len(findings) * 8))
    caps = [
        item["scoreCap"]
        for item in findings
        if isinstance(item.get("scoreCap"), int)
    ]
    if caps:
        score = min(score, min(caps))
    return score


def _classification(score: int) -> str:
    if score <= 30:
        return "Non-Functional"
    if score <= 60:
        return "Flawed"
    if score <= 85:
        return "Functional"
    return "Production Ready"


def run_reporter(aggregated: dict[str, list[Any]]) -> Report:
    reviewer = aggregated.get("reviewer", [])
    security = aggregated.get("security", [])
    tester = aggregated.get("tester", [])
    issue_count = len(reviewer) + len(security)
    score = _score_from_findings(reviewer, security)
    classification = _classification(score)

    summary_parts = [
        f"Classification: {classification}.",
        f"Architect generated {len(aggregated.get('planner', []))} planning and re-planning steps.",
        f"Sentinel/Critic found {len(reviewer)} execution and formal-review issue(s).",
        f"Auditor found {len(security)} security issue(s).",
        f"Chaos Engineer suggested {len(tester)} adversarial test(s).",
    ]

    issues = [_build_issue(item, "reviewer") for item in reviewer]
    issues.extend([_build_issue(item, "security") for item in security])

    tests = [
        {"title": suggestion, "type": "Suggestion"}
        for suggestion in tester
    ]

    return Report(
        score=score,
        summary=" ".join(summary_parts),
        risk=_build_risk(score, issues),
        issueCount=issue_count,
        issues=issues,
        tests=tests,
    )
