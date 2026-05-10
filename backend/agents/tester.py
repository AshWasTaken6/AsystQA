async def run_tester(code: str, language: str) -> list[str]:
    suggestions: list[str] = []

    if not code.strip():
        return ["No code was provided, so no test suggestions could be generated."]

    suggestions.append("Add a happy-path test that validates the expected primary behavior.")
    suggestions.append("Add at least one failure-path test for invalid or empty input.")

    normalized = language.lower().strip()
    if normalized in {"python", "py"}:
        suggestions.append("Use pytest parametrization to cover multiple input variants quickly.")
    elif normalized in {"javascript", "typescript", "js", "ts"}:
        suggestions.append("Add unit tests for edge cases and integration tests for exposed APIs.")
    else:
        suggestions.append("Add regression tests around the most business-critical logic branch.")

    return suggestions
