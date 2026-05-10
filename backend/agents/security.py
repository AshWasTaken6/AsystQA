import re
from typing import Any


def _finding(
    *,
    severity: str = "CRITICAL",
    line: int = 1,
    issue: str,
    root_cause: str,
    fix: str,
    category: str,
    owasp: str | None = None,
    score_cap: int | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "agent": "Auditor",
        "severity": severity,
        "lineNumber": line,
        "issue": issue,
        "predictedException": "Security vulnerability",
        "rootCause": root_cause,
        "fix": fix,
        "impact": root_cause,
        "category": category,
    }
    if owasp:
        finding["owasp"] = owasp
    if score_cap is not None:
        finding["scoreCap"] = score_cap
    return finding


def _line_number(code: str, needle: str) -> int:
    lowered = code.lower()
    index = lowered.find(needle.lower())
    if index < 0:
        return 1
    return code[:index].count("\n") + 1


def _has(pattern: str, code: str) -> bool:
    return re.search(pattern, code, flags=re.IGNORECASE | re.MULTILINE) is not None


async def run_security(
    code: str,
    language: str,
    context: dict[str, Any] | None = None,
) -> list[dict]:
    """
    Auditor profile: OWASP-oriented adversarial static scan with context from
    Sentinel diagnostics. This is intentionally strict and noisy in favor of
    security precision.
    """
    findings: list[dict[str, Any]] = []
    lowered = code.lower()
    normalized = language.lower().strip()

    sink_checks = [
        ("eval(", "Use of eval()", "Dynamic evaluation can execute attacker-controlled code.", "Replace eval with a typed parser or command allowlist.", "A03:2021 Injection"),
        ("exec(", "Use of exec()", "Dynamic execution allows code injection and privilege boundary bypass.", "Remove exec or isolate it in a locked-down sandbox.", "A03:2021 Injection"),
        ("subprocess", "Shell/process execution surface", "Process execution can become command injection when arguments include user-controlled data.", "Use argv arrays, disable shell=True, and allowlist commands.", "A03:2021 Injection"),
        ("innerhtml", "Unsafe HTML content injection", "innerHTML can turn untrusted strings into executable script.", "Use textContent or a vetted sanitizer.", "A03:2021 Injection"),
        ("document.write(", "Unsafe document.write sink", "document.write can inject attacker-controlled markup into the page.", "Use safe DOM construction APIs.", "A03:2021 Injection"),
    ]
    for needle, issue, root_cause, fix, owasp in sink_checks:
        if needle in lowered:
            findings.append(_finding(
                line=_line_number(code, needle),
                issue=issue,
                root_cause=root_cause,
                fix=fix,
                category="Injection",
                owasp=owasp,
                score_cap=60,
            ))

    secret_patterns = [
        (r"(api[_-]?key|secret|token|password)\s*=\s*['\"][^'\"]{6,}", "Hardcoded sensitive data"),
        (r"bearer\s+[a-z0-9._~+/=-]{12,}", "Hardcoded bearer token"),
        (r"sk-[a-z0-9_-]{8,}", "Hardcoded API token"),
    ]
    for pattern, issue in secret_patterns:
        match = re.search(pattern, code, flags=re.IGNORECASE)
        if match:
            findings.append(_finding(
                line=code[:match.start()].count("\n") + 1,
                issue=issue,
                root_cause="A credential-like value appears directly in source and can leak through code review, logs, or bundles.",
                fix="Move secrets to environment-backed secret storage and rotate exposed values.",
                category="Cryptographic & Secret Management",
                owasp="A02:2021 Cryptographic Failures",
                score_cap=60,
            ))

    sensitive_identifier = re.search(
        r"\b(api[_-]?key|secret|token|password)\b\s*=",
        code,
        flags=re.IGNORECASE,
    )
    if sensitive_identifier and not any(item.get("issue") == "Hardcoded sensitive data" for item in findings):
        findings.append(_finding(
            severity="WARNING",
            line=code[:sensitive_identifier.start()].count("\n") + 1,
            issue="Sensitive identifier assigned in source",
            root_cause="A credential-like variable is assigned directly in code, which can hide hardcoded or redacted secrets.",
            fix="Load sensitive values through a secret manager and keep only non-secret references in source.",
            category="Cryptographic & Secret Management",
            owasp="A02:2021 Cryptographic Failures",
            score_cap=85,
        ))

    crypto_checks = [
        ("md5(", "Weak hash primitive MD5", "MD5 is collision-prone and unsuitable for integrity or password storage.", "Use SHA-256 for integrity or Argon2/bcrypt/scrypt for passwords."),
        ("sha1(", "Weak hash primitive SHA-1", "SHA-1 is collision-prone and unsuitable for modern security guarantees.", "Use SHA-256+ or a password-hashing KDF as appropriate."),
        ("random.random(", "Non-cryptographic randomness", "random.random is predictable and unsafe for tokens or secrets.", "Use secrets.token_urlsafe or a CSPRNG."),
    ]
    for needle, issue, root_cause, fix in crypto_checks:
        if needle in lowered:
            findings.append(_finding(
                line=_line_number(code, needle),
                issue=issue,
                root_cause=root_cause,
                fix=fix,
                category="Cryptographic Weakness",
                owasp="A02:2021 Cryptographic Failures",
                score_cap=60,
            ))

    if _has(r"password", code) and not _has(r"(hash|bcrypt|argon2|scrypt|pbkdf2)", code):
        findings.append(_finding(
            line=_line_number(code, "password"),
            issue="Password handling lacks visible hashing",
            root_cause="Password-like data appears without a recognizable password hashing boundary.",
            fix="Hash passwords with Argon2, bcrypt, scrypt, or PBKDF2 before storage.",
            category="Authentication",
            owasp="A07:2021 Identification and Authentication Failures",
            score_cap=60,
        ))

    access_control_indicators = ["admin", "role", "permission", "owner", "user_id"]
    if any(indicator in lowered for indicator in access_control_indicators):
        has_authorization_gate = any(gate in lowered for gate in ["permission", "authorize", "forbidden", "403", "role"])
        if "user_id" in lowered and not has_authorization_gate:
            findings.append(_finding(
                line=_line_number(code, "user_id"),
                issue="User-scoped data access lacks explicit authorization gate",
                root_cause="The code references user ownership without a visible permission check at the trust boundary.",
                fix="Enforce owner/admin checks before reading or mutating user-scoped resources.",
                category="Broken Access Control",
                owasp="A01:2021 Broken Access Control",
                score_cap=60,
            ))

    if normalized in {"c", "cpp"}:
        for needle in ["strcpy(", "gets(", "sprintf("]:
            if needle in lowered:
                findings.append(_finding(
                    line=_line_number(code, needle),
                    issue=f"Memory-unsafe call {needle}",
                    root_cause="The call can write past fixed buffers or read unbounded input.",
                    fix="Use bounded APIs and validate buffer sizes before every write.",
                    category="Memory Safety",
                    owasp="A04:2021 Insecure Design",
                    score_cap=60,
                ))

    sentinel_findings = (context or {}).get("sentinel", [])
    if sentinel_findings and any(item.get("predictedException") in {"NameError", "TypeError"} for item in sentinel_findings):
        findings.append(_finding(
            severity="WARNING",
            line=1,
            issue="Runtime instability can weaken security controls",
            root_cause="Sentinel found runtime defects that may bypass logging, authorization, cleanup, or transaction finalization.",
            fix="Fix runtime blockers before relying on downstream security controls.",
            category="Security Reliability",
            owasp="A04:2021 Insecure Design",
            score_cap=85,
        ))

    return findings
