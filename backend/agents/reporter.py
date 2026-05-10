from schemas.response import Report


def _classify_severity(issue_text: str, source: str) -> str:
    lowered = issue_text.lower()
    if any(keyword in lowered for keyword in ["hardcoded", "unsafe", "eval", "exec", "xss", "vulnerability", "risk", "credential"]):
        return "High"
    if any(keyword in lowered for keyword in ["too many print", "log", "todo", "fixme", "lines exceed", "unfinished", "maintainability"]):
        return "Medium"
    if source == "security":
        return "High"
    return "Low"


def _build_issue(entry: dict[str, str], source: str) -> dict[str, str]:
    title = entry.get("issue", "Issue found")
    description = entry.get("fix") or entry.get("impact") or "Review this finding."
    category = entry.get("category") or ("Security" if source == "security" else "Maintainability")
    severity = _classify_severity(title, source)
    return {
        "severity": severity,
        "category": category,
        "title": title,
        "text": description,
        "source": source,
    }


def _build_risk(score: int, issues: list[dict[str, str]]) -> str:
    if not issues:
        return "Low"

    severities = {issue.get("severity", "").lower() for issue in issues}

    if "high" in severities:
        return "High"
    if "medium" in severities:
        return "Medium"

    if score >= 80:
        return "Low"
    if score >= 55:
        return "Medium"
    return "High"


def run_reporter(aggregated: dict[str, list[str]]) -> Report:
    issue_count = len(aggregated.get("reviewer", [])) + len(aggregated.get("security", []))
    score = max(0, 100 - (issue_count * 8))

    summary_parts = [
        f"Planner generated {len(aggregated.get('planner', []))} planning steps.",
        f"Reviewer found {len(aggregated.get('reviewer', []))} issue(s).",
        f"Security found {len(aggregated.get('security', []))} issue(s).",
        f"Tester suggested {len(aggregated.get('tester', []))} test idea(s).",
    ]

    issues = [_build_issue(item, "reviewer") for item in aggregated.get("reviewer", [])]
    issues.extend([_build_issue(item, "security") for item in aggregated.get("security", [])])

    tests = [
        {"title": suggestion, "type": "Suggestion"}
        for suggestion in aggregated.get("tester", [])
    ]

    return Report(
        score=score,
        summary=" ".join(summary_parts),
        risk=_build_risk(score, issues),
        issueCount=issue_count,
        issues=issues,
        tests=tests,
    )
