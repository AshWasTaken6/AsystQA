from typing import Any


def _count_token(code: str, token: str) -> int:
    return code.count(token)


def _complexity_profile(code: str, language: str) -> dict[str, int | str]:
    normalized = language.lower().strip()
    non_empty_lines = len([line for line in code.splitlines() if line.strip()])
    branches = sum(_count_token(code, token) for token in [" if ", "elif ", "for ", "while ", "case ", "catch "])
    calls = code.count("(")
    nesting_pressure = max((len(line) - len(line.lstrip(" "))) // 4 for line in code.splitlines() or [""])
    estimated_big_o = "O(n^2) risk" if ("for " in code and code.count("for ") > 1) else "O(n) or lower expected"
    if normalized in {"javascript", "typescript", "js", "ts"} and ".map(" in code and ".filter(" in code:
        estimated_big_o = "O(k*n) chained-iteration risk"
    return {
        "lines": non_empty_lines,
        "branches": branches,
        "calls": calls,
        "nesting": nesting_pressure,
        "big_o": estimated_big_o,
    }


async def run_planner(
    code: str,
    language: str,
    context: dict[str, Any] | None = None,
) -> list[str]:
    """
    Architect profile: strategic decomposition, debt triage, complexity assessment,
    and contingency planning. When context is supplied, this becomes the re-planning
    phase of the swarm feedback loop.
    """
    context = context or {}
    normalized = language.lower().strip()
    profile = _complexity_profile(code, normalized)
    sentinel = context.get("sentinel", [])
    auditor = context.get("auditor", [])
    critic = context.get("critic", [])

    phase = "re-plan" if context else "initial plan"
    plan = [
        f"Architect {phase}: decompose the {normalized or 'source'} scan into execution, security, formal-review, and resilience lanes.",
        (
            "Complexity profile: "
            f"{profile['lines']} non-empty lines, {profile['branches']} branch tokens, "
            f"{profile['calls']} call sites, nesting depth {profile['nesting']}, {profile['big_o']}."
        ),
        "Zero-trust boundary: treat every input, file path, credential, network response, and deserialized payload as hostile.",
        "Modularity target: isolate validation, pure business logic, side effects, and recovery into independently testable units.",
        "High-availability target: prefer idempotent commands, bounded retries, circuit breakers, and typed partial-failure results.",
    ]

    if normalized in {"python", "py"}:
        plan.append("Python lane: compile with ast.parse, trace symbol lifetimes, validate exception paths, and inspect semantic contracts.")
    elif normalized in {"javascript", "typescript", "js", "ts"}:
        plan.append("JS/TS lane: inspect async promise paths, DOM sinks, authorization checks, and mutation-heavy state transitions.")

    if sentinel or auditor or critic:
        plan.extend([
            f"Feedback intake: Sentinel={len(sentinel)} finding(s), Auditor={len(auditor)} finding(s), Critic={len(critic)} finding(s).",
            "Contingency A: block release on any non-compilable, privilege-escalating, or data-loss finding.",
            "Contingency B: when runtime defects exist, prioritize boundary validation and deterministic recovery before refactors.",
            "Contingency C: when security defects exist, threat-model the affected trust boundary before accepting local fixes.",
        ])

    return plan
