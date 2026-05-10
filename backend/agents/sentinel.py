import ast
import builtins
from dataclasses import dataclass, field
from typing import Any


BUILTIN_NAMES = set(dir(builtins))
UNKNOWN = object()


def _finding(
    *,
    severity: str,
    line: int,
    issue: str,
    predicted_exception: str,
    root_cause: str,
    fix: str,
    category: str,
    score_cap: int | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "severity": severity,
        "lineNumber": line,
        "issue": issue,
        "predictedException": predicted_exception,
        "rootCause": root_cause,
        "fix": fix,
        "impact": root_cause,
        "category": category,
    }
    if score_cap is not None:
        finding["scoreCap"] = score_cap
    return finding


def _target_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    if isinstance(node, ast.Name):
        names.add(node.id)
    elif isinstance(node, (ast.Tuple, ast.List)):
        for element in node.elts:
            names.update(_target_names(element))
    elif isinstance(node, ast.Starred):
        names.update(_target_names(node.value))
    return names


def _assigned_names(nodes: list[ast.stmt]) -> set[str]:
    class AssignmentCollector(ast.NodeVisitor):
        def __init__(self) -> None:
            self.names: set[str] = set()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.names.add(node.name)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.names.add(node.name)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.names.add(node.name)

        def visit_Name(self, node: ast.Name) -> None:
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                self.names.add(node.id)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                self.names.add(alias.asname or alias.name.split(".")[0])

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                self.names.add(alias.asname or alias.name.split(".")[0])

    collector = AssignmentCollector()
    for item in nodes:
        collector.visit(item)
    return collector.names


def _constant_value(node: ast.AST, known_values: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in known_values:
        return known_values[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_constant_value(element, known_values) for element in node.elts]
    return UNKNOWN


def _type_name(value: Any) -> str:
    if value is None:
        return "NoneType"
    return type(value).__name__


@dataclass
class Scope:
    defined: set[str]
    local_assigned: set[str] = field(default_factory=set)
    known_values: dict[str, Any] = field(default_factory=dict)
    module_symbols: set[str] = field(default_factory=set)
    is_function: bool = False


class PythonExecutionAnalyzer:
    def __init__(self, tree: ast.Module):
        self.tree = tree
        self.findings: list[dict[str, Any]] = []
        self.module_symbols = self._collect_module_symbols(tree)
        self.scopes: list[Scope] = [
            Scope(defined=set(), module_symbols=self.module_symbols)
        ]

    def analyze(self) -> list[dict[str, Any]]:
        self._visit_block(self.tree.body)
        return self.findings

    def _collect_module_symbols(self, tree: ast.Module) -> set[str]:
        symbols: set[str] = set()
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    symbols.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    symbols.update(_target_names(target))
        return symbols

    @property
    def scope(self) -> Scope:
        return self.scopes[-1]

    def _is_known(self, name: str) -> bool:
        if name in BUILTIN_NAMES:
            return True
        if any(name in scope.defined for scope in reversed(self.scopes)):
            return True
        return self.scope.is_function and name in self.scope.module_symbols

    def _add_defined(self, name: str, line: int) -> None:
        self.scope.defined.add(name)
        if name in BUILTIN_NAMES:
            self.findings.append(_finding(
                severity="WARNING",
                line=line,
                issue=f"Builtin name '{name}' is shadowed",
                predicted_exception="No immediate exception",
                root_cause=(
                    f"Assignment to '{name}' hides the Python builtin of the same name in this scope."
                ),
                fix=f"Rename '{name}' so later calls to the builtin remain available.",
                category="Boundary Integrity",
            ))

    def _visit_block(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            self._visit_stmt(statement)

    def _visit_stmt(self, node: ast.stmt) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._handle_function(node)
        elif isinstance(node, ast.ClassDef):
            self._add_defined(node.name, node.lineno)
            for base in node.bases:
                self._visit_expr(base)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                self._add_defined(alias.asname or alias.name.split(".")[0], node.lineno)
        elif isinstance(node, ast.Assign):
            self._visit_expr(node.value)
            value = _constant_value(node.value, self.scope.known_values)
            for target in node.targets:
                self._define_target(target, value, node.lineno)
        elif isinstance(node, ast.AnnAssign):
            if node.value is not None:
                self._visit_expr(node.value)
                value = _constant_value(node.value, self.scope.known_values)
            else:
                value = UNKNOWN
            self._define_target(node.target, value, node.lineno)
        elif isinstance(node, ast.AugAssign):
            self._visit_expr(node.target)
            self._visit_expr(node.value)
            self._define_target(node.target, UNKNOWN, node.lineno)
        elif isinstance(node, ast.For):
            self._visit_expr(node.iter)
            self._define_target(node.target, UNKNOWN, node.lineno)
            self._check_range_index_boundary(node)
            self._visit_block(node.body)
            self._visit_block(node.orelse)
        elif isinstance(node, ast.While):
            self._visit_expr(node.test)
            self._check_infinite_loop(node)
            self._visit_block(node.body)
            self._visit_block(node.orelse)
        elif isinstance(node, ast.If):
            self._visit_expr(node.test)
            self._visit_block(node.body)
            self._visit_block(node.orelse)
        elif isinstance(node, ast.Try):
            self._visit_block(node.body)
            for handler in node.handlers:
                if handler.name:
                    self._add_defined(handler.name, handler.lineno)
                self._visit_block(handler.body)
            self._visit_block(node.orelse)
            self._visit_block(node.finalbody)
        elif isinstance(node, ast.With):
            for item in node.items:
                self._visit_expr(item.context_expr)
                if item.optional_vars:
                    self._define_target(item.optional_vars, UNKNOWN, node.lineno)
            self._visit_block(node.body)
        elif isinstance(node, ast.Match):
            self._visit_expr(node.subject)
            for case in node.cases:
                if case.guard:
                    self._visit_expr(case.guard)
                self._visit_block(case.body)
        else:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.expr):
                    self._visit_expr(child)
                elif isinstance(child, ast.stmt):
                    self._visit_stmt(child)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._add_defined(node.name, node.lineno)
        for decorator in node.decorator_list:
            self._visit_expr(decorator)
        defaults = list(node.args.defaults) + list(node.args.kw_defaults)
        for default in defaults:
            if default is not None:
                self._visit_expr(default)

        params = {arg.arg for arg in node.args.args}
        params.update(arg.arg for arg in node.args.posonlyargs)
        params.update(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if node.args.kwarg:
            params.add(node.args.kwarg.arg)

        local_assigned = _assigned_names(node.body)
        self.scopes.append(Scope(
            defined=set(params),
            local_assigned=local_assigned,
            module_symbols=self.module_symbols,
            is_function=True,
        ))
        self._visit_block(node.body)
        self.scopes.pop()

    def _define_target(self, target: ast.AST, value: Any, line: int) -> None:
        for name in _target_names(target):
            self._add_defined(name, line)
            if value is UNKNOWN:
                self.scope.known_values.pop(name, None)
            else:
                self.scope.known_values[name] = value

    def _visit_expr(self, node: ast.AST) -> None:
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                self._check_name_load(node)
            return
        if isinstance(node, ast.BinOp):
            self._visit_expr(node.left)
            self._visit_expr(node.right)
            self._check_binary_operation(node)
            return
        if isinstance(node, ast.Subscript):
            self._visit_expr(node.value)
            self._visit_expr(node.slice)
            self._check_constant_subscript(node)
            return
        if isinstance(node, ast.Call):
            self._visit_expr(node.func)
            for arg in node.args:
                self._visit_expr(arg)
            for keyword in node.keywords:
                self._visit_expr(keyword.value)
            return
        if isinstance(node, ast.Lambda):
            return

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._visit_expr(child)

    def _check_name_load(self, node: ast.Name) -> None:
        name = node.id
        if self.scope.is_function and name in self.scope.local_assigned and name not in self.scope.defined:
            self.findings.append(_finding(
                severity="CRITICAL",
                line=node.lineno,
                issue=f"Local variable '{name}' is read before assignment",
                predicted_exception="UnboundLocalError",
                root_cause=(
                    f"'{name}' is assigned later in the same function, so Python treats it as local "
                    "and raises before the first value exists."
                ),
                fix=f"Initialize '{name}' before reading it, or pass it as a parameter.",
                category="Variable & Scope Trace",
                score_cap=30,
            ))
            return

        if not self._is_known(name):
            self.findings.append(_finding(
                severity="CRITICAL",
                line=node.lineno,
                issue=f"Undefined variable '{name}'",
                predicted_exception="NameError",
                root_cause=f"'{name}' is loaded before any assignment, import, parameter, or builtin definition is available.",
                fix=f"Define or import '{name}' before this line.",
                category="Variable & Scope Trace",
                score_cap=30,
            ))

    def _check_binary_operation(self, node: ast.BinOp) -> None:
        left = _constant_value(node.left, self.scope.known_values)
        right = _constant_value(node.right, self.scope.known_values)

        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            self.findings.append(_finding(
                severity="CRITICAL",
                line=node.lineno,
                issue="Division by a value that can be zero",
                predicted_exception="ZeroDivisionError",
                root_cause="The divisor resolves to literal zero at analysis time.",
                fix="Guard the divisor or return an explicit error before dividing.",
                category="Data Type & Arithmetic Validation",
                score_cap=60,
            ))

        if isinstance(node.op, ast.Add):
            if (
                (isinstance(left, str) and right is not UNKNOWN and not isinstance(right, str))
                or (isinstance(right, str) and left is not UNKNOWN and not isinstance(left, str))
            ):
                self.findings.append(_finding(
                    severity="CRITICAL",
                    line=node.lineno,
                    issue="Incompatible operands for addition",
                    predicted_exception="TypeError",
                    root_cause=(
                        f"Python cannot apply '+' between {_type_name(left)} and {_type_name(right)}."
                    ),
                    fix="Convert operands explicitly or use interpolation/formatting for strings.",
                    category="Data Type & Arithmetic Validation",
                    score_cap=60,
                ))

        if (
            isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod))
            and (left is None or right is None)
            and (isinstance(node.left, ast.Constant) or isinstance(node.right, ast.Constant))
        ):
            self.findings.append(_finding(
                severity="CRITICAL",
                line=node.lineno,
                issue="Arithmetic uses None",
                predicted_exception="TypeError",
                root_cause="One side of the arithmetic expression is None.",
                fix="Validate the value is numeric before arithmetic.",
                category="Data Type & Arithmetic Validation",
                score_cap=60,
            ))

    def _check_constant_subscript(self, node: ast.Subscript) -> None:
        value = _constant_value(node.value, self.scope.known_values)
        index = _constant_value(node.slice, self.scope.known_values)
        if isinstance(value, (list, tuple, str)) and isinstance(index, int):
            if index >= len(value) or index < -len(value):
                self.findings.append(_finding(
                    severity="CRITICAL",
                    line=node.lineno,
                    issue="Index is outside the known sequence bounds",
                    predicted_exception="IndexError",
                    root_cause=f"Sequence length is {len(value)}, but index {index} is requested.",
                    fix="Check the sequence length before indexing or use safe iteration.",
                    category="Logic & Boundary Integrity",
                    score_cap=60,
                ))

    def _check_range_index_boundary(self, node: ast.For) -> None:
        if not isinstance(node.target, ast.Name):
            return
        if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name):
            return
        if node.iter.func.id != "range" or len(node.iter.args) != 1:
            return

        arg = node.iter.args[0]
        if not (
            isinstance(arg, ast.BinOp)
            and isinstance(arg.op, ast.Add)
            and isinstance(arg.right, ast.Constant)
            and arg.right.value == 1
            and isinstance(arg.left, ast.Call)
            and isinstance(arg.left.func, ast.Name)
            and arg.left.func.id == "len"
            and len(arg.left.args) == 1
            and isinstance(arg.left.args[0], ast.Name)
        ):
            return

        sequence_name = arg.left.args[0].id
        index_name = node.target.id
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if (
                isinstance(child, ast.Subscript)
                and isinstance(child.value, ast.Name)
                and child.value.id == sequence_name
                and isinstance(child.slice, ast.Name)
                and child.slice.id == index_name
            ):
                self.findings.append(_finding(
                    severity="WARNING",
                    line=child.lineno,
                    issue="Loop indexes one element past the sequence",
                    predicted_exception="IndexError",
                    root_cause=(
                        f"range(len({sequence_name}) + 1) includes len({sequence_name}), "
                        "which is not a valid index."
                    ),
                    fix=f"Use range(len({sequence_name})) or iterate over the values directly.",
                    category="Logic & Boundary Integrity",
                    score_cap=60,
                ))

    def _check_infinite_loop(self, node: ast.While) -> None:
        has_break = any(isinstance(child, ast.Break) for child in ast.walk(ast.Module(body=node.body, type_ignores=[])))
        if isinstance(node.test, ast.Constant) and node.test.value is True and not has_break:
            self.findings.append(_finding(
                severity="WARNING",
                line=node.lineno,
                issue="Infinite loop has no break path",
                predicted_exception="Logical deadlock",
                root_cause="while True executes indefinitely because no break statement exists in the loop body.",
                fix="Add a reachable break condition or bounded loop condition.",
                category="Logic & Boundary Integrity",
                score_cap=85,
            ))


async def run_sentinel(code: str, language: str, context: dict[str, Any] | None = None) -> list[dict]:
    stripped = code.strip()
    if not stripped:
        finding = _finding(
            severity="CRITICAL",
            line=1,
            issue="No code provided",
            predicted_exception="No execution",
            root_cause="The submitted source is empty, so no analysis target exists.",
            fix="Provide valid source code.",
            category="Syntax & Compilation Scan",
            score_cap=30,
        )
        finding["agent"] = "Sentinel"
        finding["recovery"] = _recovery_strategy(finding)
        return [finding]

    language_normalized = language.lower().strip()
    if language_normalized not in {"python", "py"}:
        return []

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        finding = _finding(
            severity="CRITICAL",
            line=exc.lineno or 1,
            issue="Python syntax prevents compilation",
            predicted_exception="SyntaxError",
            root_cause=exc.msg,
            fix="Correct the syntax error before runtime analysis can continue.",
            category="Syntax & Compilation Scan",
            score_cap=30,
        )
        finding["agent"] = "Sentinel"
        finding["recovery"] = _recovery_strategy(finding)
        return [finding]

    findings = PythonExecutionAnalyzer(tree).analyze()
    for finding in findings:
        finding["agent"] = "Sentinel"
        finding.setdefault("recovery", _recovery_strategy(finding))
    return findings


def _recovery_strategy(finding: dict[str, Any]) -> str:
    predicted = finding.get("predictedException")
    if predicted in {"SyntaxError", "NameError", "UnboundLocalError"}:
        return "Fail closed, reject execution, and require a corrected build artifact before retry."
    if predicted in {"TypeError", "ZeroDivisionError", "IndexError"}:
        return "Validate inputs at the boundary, return an explicit typed error, and make retries idempotent."
    if predicted == "Logical deadlock":
        return "Apply a bounded timeout, persist progress checkpoints, and make retry operations safe to replay."
    return "Capture diagnostic context, avoid partial writes, and retry only after preconditions are restored."
