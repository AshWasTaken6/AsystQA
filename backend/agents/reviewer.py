def run_reviewer(code: str, language: str) -> list[dict]:
    findings: list[dict] = []
    stripped_lines = [line.rstrip() for line in code.splitlines() if line.strip()]

    if not stripped_lines:
        return [{
            "issue": "No code provided",
            "fix": "Provide valid source code",
            "impact": "No analysis could be performed",
            "category": "Maintainability"
        }]

    if any(len(line) > 100 for line in stripped_lines):
        findings.append({
            "issue": "Lines exceed 100 characters",
            "fix": "Break long lines into smaller readable parts",
            "impact": "Harder to maintain and read",
            "category": "Maintainability"
        })

    language_normalized = language.lower().strip()

    if "TODO" in code or "FIXME" in code:
        findings.append({
            "issue": "Unfinished code (TODO/FIXME)",
            "fix": "Complete or remove unfinished sections",
            "impact": "May lead to incomplete functionality",
            "category": "Maintainability"
        })

    if language_normalized in {"python", "py"} and "print(" in code:
        findings.append({
            "issue": "Debug output found",
            "fix": "Use logging instead of print",
            "impact": "Clutters production output",
            "category": "Maintainability"
        })

    if language_normalized in {"javascript", "js", "ts"} and "console.log(" in code:
        findings.append({
            "issue": "Console logs left in code",
            "fix": "Remove debug logs before deployment",
            "impact": "Unprofessional and noisy output",
            "category": "Maintainability"
        })

    if language_normalized in {"python", "py"} and "async def" in code and "await" not in code:
        findings.append({
            "issue": "Async function without await",
            "fix": "Verify async function behavior or remove unused async",
            "impact": "May lead to unexpected concurrency issues",
            "category": "Maintainability"
        })

    return findings
