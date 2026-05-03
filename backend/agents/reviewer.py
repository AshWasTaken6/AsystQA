from utils.code_analysis import (
    SUPPORTED_JS_LANGUAGES,
    count_pattern,
    extract_functions,
    find_duplicate_non_empty_lines,
    find_long_functions,
    find_unused_python_variables,
    normalize_language,
)


def run(code: str, language: str) -> list[str]:
    normalized = normalize_language(language)
    findings: list[str] = []

    if normalized == "python":
        findings.extend(find_unused_python_variables(code))
        print_count = count_pattern(code, r"\bprint\s*\(")
        if print_count > 2:
            findings.append(
                f"Too many print statements found ({print_count}). Consider logging or cleanup."
            )
    elif normalized in SUPPORTED_JS_LANGUAGES:
        log_count = count_pattern(code, r"\bconsole\.log\s*\(")
        if log_count > 2:
            findings.append(
                f"Too many console.log statements found ({log_count}). Consider cleanup before shipping."
            )

    functions = extract_functions(code, normalized)
    if not functions:
        findings.append("No functions detected. Consider splitting logic into reusable functions.")

    findings.extend(find_duplicate_non_empty_lines(code))
    findings.extend(find_long_functions(code, normalized))

    if not findings:
        findings.append("No major review issues detected.")

    return findings
