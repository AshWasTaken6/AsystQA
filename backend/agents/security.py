def run_security(code: str, language: str) -> list[str]:
    findings: list[str] = []
    lowered = code.lower()

    if "eval(" in lowered:
        findings.append("Potential unsafe dynamic execution detected via eval().")

    if "exec(" in lowered:
        findings.append("Potential unsafe dynamic execution detected via exec().")

    if "password" in lowered or "secret" in lowered or "api_key" in lowered:
        findings.append("Possible hardcoded sensitive data markers were detected.")

    if "innerhtml" in lowered:
        findings.append("Direct HTML injection patterns may introduce XSS risk.")

    if not findings:
        findings.append("No obvious high-risk patterns were detected by the security stub.")

    return findings
