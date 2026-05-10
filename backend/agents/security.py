def run_security(code: str, language: str) -> list[dict]:
    findings: list[dict] = []
    lowered = code.lower()

    if "eval(" in lowered:
        findings.append({
            "issue": "Use of eval()",
            "fix": "Avoid eval and use safer parsing methods",
            "impact": "Can execute malicious code",
            "category": "Security"
        })

    if "exec(" in lowered:
        findings.append({
            "issue": "Use of exec()",
            "fix": "Avoid dynamic execution",
            "impact": "Severe security risk",
            "category": "Security"
        })

    if any(secret in lowered for secret in ["password", "secret", "api_key", "apikey", "token"]):
        findings.append({
            "issue": "Hardcoded sensitive data",
            "fix": "Use environment variables or secret management",
            "impact": "Risk of credential leaks",
            "category": "Security"
        })

    if "innerhtml" in lowered or "document.write(" in lowered:
        findings.append({
            "issue": "Unsafe HTML content injection",
            "fix": "Use safe DOM APIs such as textContent",
            "impact": "XSS vulnerability risk",
            "category": "Security"
        })

    if "password" in lowered and "hash" not in lowered:
        findings.append({
            "issue": "Password handling may be insecure",
            "fix": "Hash passwords before storing or transmitting",
            "impact": "Risk of credential exposure",
            "category": "Security"
        })

    return findings
