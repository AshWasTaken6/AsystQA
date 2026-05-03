def run(
    planner_output: list[str],
    reviewer_output: list[str],
    security_output: list[str],
    tester_output: list[str],
) -> dict[str, object]:
    review_issue_count = _count_real_issues(reviewer_output)
    security_issue_count = _count_real_issues(security_output)

    score = 100
    score -= review_issue_count * 7
    score -= security_issue_count * 12
    score = max(score, 0)

    if score >= 90:
        level = "Excellent"
    elif score >= 75:
        level = "Good"
    elif score >= 60:
        level = "Fair"
    else:
        level = "Needs Work"

    return {
        "score": score,
        "level": level,
        "summary": (
            f"Found {review_issue_count} review issue(s) and "
            f"{security_issue_count} security risk(s)."
        ),
        "counts": {
            "planner_steps": len(planner_output),
            "review_issues": review_issue_count,
            "security_risks": security_issue_count,
            "test_suggestions": len(tester_output),
        },
    }


def _count_real_issues(items: list[str]) -> int:
    non_issue_prefixes = (
        "No major",
        "No obvious",
    )
    return sum(1 for item in items if not item.startswith(non_issue_prefixes))
