import re

SUPPORTED_JS_LANGUAGES = ["javascript", "js", "typescript", "ts"]


# -------------------------
# Normalize Language
# -------------------------
def normalize_language(language: str) -> str:
    return language.strip().lower()


# -------------------------
# Count pattern occurrences
# -------------------------
def count_pattern(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code))


# -------------------------
# Extract functions (basic)
# -------------------------
def extract_functions(code: str, language: str):
    functions = []

    if language == "python":
        matches = re.finditer(r"def\s+(\w+)\s*\(", code)
        for match in matches:
            functions.append({
                "name": match.group(1)
            })

    elif language in SUPPORTED_JS_LANGUAGES:
        matches = re.finditer(r"function\s+(\w+)\s*\(", code)
        for match in matches:
            functions.append({
                "name": match.group(1)
            })

    return functions


# -------------------------
# Find duplicate lines
# -------------------------
def find_duplicate_non_empty_lines(code: str):
    lines = [line.strip() for line in code.split("\n") if line.strip()]
    seen = set()
    duplicates = set()

    for line in lines:
        if line in seen:
            duplicates.add(line)
        else:
            seen.add(line)

    return [
        f"Duplicate line detected: '{line[:50]}'"
        for line in duplicates
    ]


# -------------------------
# Find long functions
# -------------------------
def find_long_functions(code: str, language: str, threshold: int = 20):
    findings = []

    if language == "python":
        functions = re.split(r"\ndef\s+", code)

        for func in functions[1:]:
            lines = func.split("\n")
            if len(lines) > threshold:
                name = lines[0].split("(")[0].strip()
                findings.append(
                    f"Function '{name}' is too long ({len(lines)} lines)"
                )

    elif language in SUPPORTED_JS_LANGUAGES:
        functions = re.split(r"\nfunction\s+", code)

        for func in functions[1:]:
            lines = func.split("\n")
            if len(lines) > threshold:
                name = lines[0].split("(")[0].strip()
                findings.append(
                    f"Function '{name}' is too long ({len(lines)} lines)"
                )

    return findings


# -------------------------
# Find unused Python variables (basic heuristic)
# -------------------------
def find_unused_python_variables(code: str):
    findings = []

    assignments = re.findall(r"(\w+)\s*=", code)

    for var in set(assignments):
        occurrences = len(re.findall(rf"\b{var}\b", code))

        if occurrences <= 1:
            findings.append(
                f"Variable '{var}' assigned but never used"
            )

    return findings