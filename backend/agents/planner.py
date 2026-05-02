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
