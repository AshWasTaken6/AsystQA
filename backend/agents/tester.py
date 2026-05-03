from utils.code_analysis import extract_functions, normalize_language


def run(code: str, language: str) -> list[str]:
    functions = extract_functions(code, normalize_language(language))

    if not functions:
        return ["Create a basic smoke test for the main execution path."]

    test_suggestions = [f"Create test_{function['name']}()" for function in functions[:5]]
    return test_suggestions
