from __future__ import annotations

import ast
import re
from collections import Counter


SUPPORTED_JS_LANGUAGES = {"javascript", "js", "typescript", "ts"}


def normalize_language(language: str) -> str:
    return language.strip().lower()


def get_non_empty_lines(code: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for line_number, line in enumerate(code.splitlines(), start=1):
        stripped = line.strip()
        if stripped:
            lines.append((line_number, stripped))
    return lines


def find_duplicate_non_empty_lines(code: str) -> list[str]:
    seen: dict[str, int] = {}
    duplicates: list[str] = []

    for line_number, line in get_non_empty_lines(code):
        if line in seen:
            duplicates.append(
                f"Duplicate line repeated at lines {seen[line]} and {line_number}: {line}"
            )
        else:
            seen[line] = line_number

    return duplicates


def count_pattern(code: str, pattern: str) -> int:
    return len(re.findall(pattern, code))


def extract_functions(code: str, language: str) -> list[dict[str, int | str]]:
    normalized = normalize_language(language)
    if normalized == "python":
        return extract_python_functions(code)
    if normalized in SUPPORTED_JS_LANGUAGES:
        return extract_js_functions(code)
    return []


def extract_python_functions(code: str) -> list[dict[str, int | str]]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    functions: list[dict[str, int | str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end_lineno = getattr(node, "end_lineno", node.lineno)
            functions.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": end_lineno,
                    "length": end_lineno - node.lineno + 1,
                }
            )
    return sorted(functions, key=lambda item: int(item["start_line"]))


def extract_js_functions(code: str) -> list[dict[str, int | str]]:
    functions: list[dict[str, int | str]] = []
    patterns = [
        re.compile(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("),
        re.compile(r"(?:const|let|var)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\([^)]*\)\s*=>"),
    ]

    lines = code.splitlines()
    for line_number, line in enumerate(lines, start=1):
        for pattern in patterns:
            match = pattern.search(line)
            if match:
                functions.append(
                    {
                        "name": match.group(1),
                        "start_line": line_number,
                        "end_line": line_number,
                        "length": 1,
                    }
                )
                break

    return functions


def find_long_functions(
    code: str,
    language: str,
    threshold: int = 20,
) -> list[str]:
    long_functions: list[str] = []

    for function in extract_functions(code, language):
        if int(function["length"]) > threshold:
            long_functions.append(
                f"Function '{function['name']}' is long at {function['length']} lines."
            )

    return long_functions


def find_unused_python_variables(code: str) -> list[str]:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    assignments: dict[str, list[int]] = {}
    usages: Counter[str] = Counter()

    class VariableVisitor(ast.NodeVisitor):
        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, ast.Store):
                assignments.setdefault(node.id, []).append(node.lineno)
            elif isinstance(node.ctx, ast.Load):
                usages[node.id] += 1
            self.generic_visit(node)

    VariableVisitor().visit(tree)

    ignored_names = {"_", "__name__"}
    unused: list[str] = []

    for name, line_numbers in assignments.items():
        if name in ignored_names:
            continue
        if usages[name] == 0:
            unused.append(
                f"Unused variable '{name}' assigned on line {line_numbers[0]}."
            )

    return unused

