from utils.code_analysis import SUPPORTED_JS_LANGUAGES, normalize_language


def run(code: str, language: str) -> list[str]:
    normalized = normalize_language(language)

    if normalized == "python":
        return [
            "Scan Python syntax",
            "Review logic and code quality",
            "Check security patterns",
            "Generate pytest-style tests",
        ]

    if normalized in SUPPORTED_JS_LANGUAGES:
        return [
            "Scan JavaScript syntax",
            "Review DOM and client logic",
            "Check security patterns",
            "Generate unit tests",
        ]

    return [
        "Scan code structure",
        "Review logic and code quality",
        "Check security patterns",
        "Generate useful tests",
    ]
