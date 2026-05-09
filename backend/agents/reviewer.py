def run_reviewer(code: str, language: str) -> list[dict]:
    findings = []
    stripped_lines = [line.rstrip() for line in code.splitlines()]

    if not stripped_lines:
        return [{
            "issue": "No code provided",
            "fix": "Provide valid source code",
            "impact": "No analysis could be performed"
        }]

    if any(len(line) > 100 for line in stripped_lines):
        findings.append({
            "issue": "Lines exceed 100 characters",
            "fix": "Break long lines into smaller readable parts",
            "impact": "Harder to maintain and read"
        })

    if "TODO" in code or "FIXME" in code:
        findings.append({
            "issue": "Unfinished code (TODO/FIXME)",
            "fix": "Complete or remove unfinished sections",
            "impact": "May lead to incomplete functionality"
        })

    if language.lower() in {"python", "py"} and "print(" in code:
        findings.append({
            "issue": "Too many print statements",
            "fix": "Use logging instead of print",
            "impact": "Clutters production output"
        })

    if language.lower() in {"javascript", "js", "ts"} and "console.log(" in code:
        findings.append({
            "issue": "Console logs left in code",
            "fix": "Remove debug logs before deployment",
            "impact": "Unprofessional and noisy output"
        })

    if not findings:
        findings.append({
            "issue": "No major issues found",
            "fix": "Code looks clean",
            "impact": "Good maintainability"
        })

    return findings