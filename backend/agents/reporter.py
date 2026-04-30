from backend.schemas.response import Report


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
