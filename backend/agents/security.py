def run_security(code: str, language: str) -> list[dict]:
    findings = []
    lowered = code.lower()

    if "eval(" in lowered:
        findings.append({
            "issue": "Use of eval()",
            "fix": "Avoid eval and use safer parsing methods",
            "impact": "Can execute malicious code"
        })

    if "exec(" in lowered:
        findings.append({
            "issue": "Use of exec()",
            "fix": "Avoid dynamic execution",
            "impact": "Severe security risk"
        })

    if "password" in lowered or "secret" in lowered:
        findings.append({
            "issue": "Hardcoded sensitive data",
            "fix": "Use environment variables",
            "impact": "Risk of credential leaks"
        })

    if "innerhtml" in lowered:
        findings.append({
            "issue": "Unsafe HTML injection",
            "fix": "Use safe DOM methods like textContent",
            "impact": "XSS vulnerability risk"
        })

    if not findings:
        findings.append({
            "issue": "No security risks detected",
            "fix": "No action needed",
            "impact": "Code appears safe"
        })

    return findings