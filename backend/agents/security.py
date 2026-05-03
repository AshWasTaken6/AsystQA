import re

from utils.code_analysis import SUPPORTED_JS_LANGUAGES, normalize_language


def run(code: str, language: str) -> list[str]:
    normalized = normalize_language(language)
    findings: list[str] = []

    if re.search(r"\beval\s*\(", code):
        findings.append("Use of eval() detected. This can execute unsafe user-controlled input.")

    if normalized == "python" and re.search(r"\bexec\s*\(", code):
        findings.append("Use of exec() detected. Dynamic code execution is risky.")

    if re.search(r"(?i)\b(password|passwd|pwd)\b\s*=\s*['\"][^'\"]+['\"]", code):
        findings.append("Possible hardcoded password or secret detected.")

    if normalized == "python":
        for line_number, line in enumerate(code.splitlines(), start=1):
            if "input(" in line and not any(
                token in line for token in ["strip(", "int(", "float(", "isdigit", "isalnum"]
            ):
                findings.append(
                    f"Raw input() found on line {line_number} without obvious validation."
                )

        dangerous_imports = {
            "subprocess": "subprocess can execute shell commands.",
            "pickle": "pickle can deserialize unsafe content.",
            "marshal": "marshal is unsafe with untrusted data.",
        }
        for module, reason in dangerous_imports.items():
            if re.search(rf"^\s*(import|from)\s+{module}\b", code, flags=re.MULTILINE):
                findings.append(f"Dangerous import '{module}' detected. {reason}")

    if normalized in SUPPORTED_JS_LANGUAGES:
        dangerous_imports = {
            "child_process": "child_process can execute system commands.",
            "vm": "vm can run dynamic code.",
        }
        for module, reason in dangerous_imports.items():
            if re.search(
                rf"(import\s+.*\b{module}\b|require\(\s*['\"]{module}['\"]\s*\))",
                code,
            ):
                findings.append(f"Dangerous import '{module}' detected. {reason}")

    if not findings:
        findings.append("No obvious security risks detected.")

    return findings
