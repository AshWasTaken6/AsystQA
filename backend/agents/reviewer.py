def run_reviewer(code: str, language: str) -> list[str]:
    findings: list[str] = []
    stripped_lines = [line.rstrip() for line in code.splitlines()]

    if not stripped_lines:
        return ["No code was provided for review."]

    if any(len(line) > 100 for line in stripped_lines):
        findings.append("Some lines exceed 100 characters and may be harder to maintain.")

    if "TODO" in code or "FIXME" in code:
        findings.append("Found unfinished work markers like TODO or FIXME.")

    if language.lower() in {"python", "py"} and "print(" in code:
        findings.append("Consider replacing ad-hoc print statements with structured logging.")

    if language.lower() in {"javascript", "typescript", "js", "ts"} and "console.log(" in code:
        findings.append("Consider removing debug console logging before production use.")

    if not findings:
        findings.append("No obvious maintainability issues were detected by the reviewer stub.")

    return findings
