import ast
from typing import Any


def _finding(
    *,
    severity: str,
    line: int,
    issue: str,
    root_cause: str,
    fix: str,
    category: str = "Formal Review",
    score_cap: int | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "agent": "Critic",
        "severity": severity,
        "lineNumber": line,
        "issue": issue,
        "predictedException": "Semantic defect",
        "rootCause": root_cause,
        "fix": fix,
        "impact": root_cause,
        "category": category,
    }
    if score_cap is not None:
        finding["scoreCap"] = score_cap
    return finding


class FormalReviewAnalyzer(ast.NodeVisitor):
    def __init__(self, context: dict[str, Any] | None = None) -> None:
        self.context = context or {}
        self.findings: list[dict[str, Any]] = []
        self.function_stack: list[ast.FunctionDef | ast.AsyncFunctionDef] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._inspect_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._inspect_function(node)
        has_await = any(isinstance(child, ast.Await) for child in ast.walk(node))
        if not has_await:
            self.findings.append(_finding(
                severity="WARNING",
                line=node.lineno,
                issue="Async function has no await boundary",
                root_cause="The function advertises asynchronous behavior but executes synchronously.",
                fix="Remove async or introduce a real awaited operation with timeout/error handling.",
                category="SOLID & Clean Code",
            ))
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        if isinstance(node.test, ast.Constant):
            self.findings.append(_finding(
                severity="WARNING",
                line=node.lineno,
                issue="Branch condition is constant",
                root_cause="A constant condition creates dead code or an always-on branch.",
                fix="Replace the condition with a real predicate or delete the unreachable branch.",
                category="Logic & Semantic Review",
                score_cap=85,
            ))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Is, ast.IsNot)):
            comparable = [node.left, *node.comparators]
            if any(isinstance(item, ast.Constant) and item.value not in {None, True, False} for item in comparable):
                self.findings.append(_finding(
                    severity="WARNING",
                    line=node.lineno,
                    issue="Identity comparison used for a literal value",
                    root_cause="'is' checks object identity, not semantic equality, and can misclassify values.",
                    fix="Use == or != for value comparison.",
                    category="Logic & Semantic Review",
                    score_cap=85,
                ))
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        for handler in node.handlers:
            catches_broad_exception = handler.type is None
            catches_exception = (
                isinstance(handler.type, ast.Name)
                and handler.type.id in {"Exception", "BaseException"}
            )
            if catches_broad_exception or catches_exception:
                has_reraise = any(isinstance(child, ast.Raise) for child in ast.walk(ast.Module(body=handler.body, type_ignores=[])))
                if not has_reraise:
                    self.findings.append(_finding(
                        severity="WARNING",
                        line=handler.lineno,
                        issue="Broad exception handler suppresses failure semantics",
                        root_cause="A broad catch without re-raise can hide root causes and make recovery non-idempotent.",
                        fix="Catch explicit exception types and re-raise or return a typed failure result.",
                        category="Robustness & Error Handling",
                        score_cap=85,
                    ))
        self.generic_visit(node)

    def _inspect_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        statement_count = sum(isinstance(child, ast.stmt) for child in ast.walk(node))
        branch_count = sum(isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.Match)) for child in ast.walk(node))
        return_statements = [child for child in ast.walk(node) if isinstance(child, ast.Return)]

        if statement_count > 50 or branch_count > 10:
            self.findings.append(_finding(
                severity="WARNING",
                line=node.lineno,
                issue="Function carries excessive responsibility",
                root_cause=(
                    f"{node.name} has {statement_count} statements and {branch_count} control-flow branches, "
                    "which weakens single-responsibility boundaries."
                ),
                fix="Split orchestration, validation, and side effects into smaller functions.",
                category="SOLID & Clean Code",
                score_cap=85,
            ))

        returns_value = any(item.value is not None for item in return_statements)
        returns_none = any(item.value is None for item in return_statements)
        if returns_value and returns_none:
            self.findings.append(_finding(
                severity="WARNING",
                line=node.lineno,
                issue="Function has inconsistent return contract",
                root_cause="Some paths return a value while others implicitly or explicitly return None.",
                fix="Return a single typed result shape from every branch.",
                category="Design Contract",
                score_cap=85,
            ))


async def run_critic(code: str, language: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    normalized = language.lower().strip()
    if normalized not in {"python", "py"} or not code.strip():
        return []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    analyzer = FormalReviewAnalyzer(context)
    analyzer.visit(tree)
    return analyzer.findings
