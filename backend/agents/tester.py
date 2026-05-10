from typing import Any


def _issue_titles(items: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("issue", "unknown issue")) for item in items if isinstance(item, dict)]


async def run_tester(
    code: str,
    language: str,
    context: dict[str, Any] | None = None,
) -> list[str]:
    """
    Chaos Engineer profile: adversarial test strategy across property tests,
    fuzzing, stress, boundary values, and corrupted inputs.
    """
    if not code.strip():
        return [
            "Chaos Engineer: reject empty input and assert the API returns a typed validation error without side effects.",
        ]

    context = context or {}
    sentinel = context.get("sentinel", [])
    auditor = context.get("auditor", [])
    critic = context.get("critic", [])
    normalized = language.lower().strip()

    suggestions = [
        "Chaos Engineer: build boundary-value tests for empty, null, oversized, unicode, and malformed inputs.",
        "Chaos Engineer: add fuzzing that mutates identifiers, literals, delimiters, and nested structures until parsers fail closed.",
        "Chaos Engineer: add property-based tests asserting deterministic output, no uncaught exceptions, and stable score ranges.",
        "Chaos Engineer: run integration stress tests with repeated scans, concurrent submissions, timeout pressure, and corrupted payloads.",
        "Chaos Engineer: simulate partial agent failure and verify the pipeline returns warnings plus usable partial results.",
    ]

    if normalized in {"python", "py"}:
        suggestions.append("Python chaos lane: use pytest parametrization plus Hypothesis for arithmetic, indexing, and scope edge cases.")
    elif normalized in {"javascript", "typescript", "js", "ts"}:
        suggestions.append("JS/TS chaos lane: fuzz async promise rejection paths, DOM sink inputs, and browser event interleavings.")
    elif normalized in {"c", "cpp"}:
        suggestions.append("Native chaos lane: run address sanitizers, undefined-behavior sanitizers, and malformed buffer tests.")

    for title in _issue_titles(sentinel)[:3]:
        suggestions.append(f"Sentinel feedback test: reproduce '{title}' as a regression and assert idempotent recovery.")
    for title in _issue_titles(auditor)[:3]:
        suggestions.append(f"Auditor feedback test: attempt exploit reproduction for '{title}' and assert the boundary blocks it.")
    for title in _issue_titles(critic)[:2]:
        suggestions.append(f"Critic feedback test: encode '{title}' as a contract test so architectural drift fails fast.")

    return suggestions
