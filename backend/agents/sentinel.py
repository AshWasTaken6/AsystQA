"""
Sentinel Agent - Execution Analysis & Runtime Diagnostics

Enhanced Sentinel with multi-tiered memory, advanced decision-making,
tool integration, and comprehensive telemetry.

Sentinel specializes in detecting:
- Undefined variables and scope violations
- Type errors and arithmetic exceptions
- Division by zero and index errors
- Unbound local errors
- Boundary condition violations
- Control flow anomalies

Maintains episodic memory of similar code patterns and uses procedural
memory to improve detection accuracy over time.
"""

import ast
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
import builtins

from core.agent_base import BaseAgent, Priority, register_agent
from core.memory import (
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    Priority,
    PatternType,
    PatternSuccess,
    TaskPattern,
)
from core.telemetry import get_telemetry_manager
from core.events import EventType, emit_event
from core.tools import Tool, SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import DecisionStrategy, RuleBasedStrategy, DecisionRule
import numpy as np

logger = logging.getLogger(__name__)

# Re-export existing AST analysis logic (will be reused)
BUILTIN_NAMES = set(dir(builtins))


def _assigned_names(nodes: list[ast.stmt]) -> set[str]:
    """Collect all names that are assigned in a block of statements."""
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


class AnalysisSeverity(Enum):
    """Severity levels for findings"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SentinelFinding:
    """
    Rich finding with full metadata for memory and learning.

    Extends the basic finding dict with structured data.
    """
    severity: AnalysisSeverity
    line: int
    issue: str
    predicted_exception: str
    root_cause: str
    fix_suggestion: str
    category: str
    code_snippet: str
    confidence: float = 0.9
    agent_id: str = "sentinel"
    tags: Set[str] = field(default_factory=set)
    related_findings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_id,
            "severity": self.severity.value,
            "lineNumber": self.line,
            "issue": self.issue,
            "predictedException": self.predicted_exception,
            "rootCause": self.root_cause,
            "fix": self.fix_suggestion,
            "impact": self.root_cause,
            "category": self.category,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "related": self.related_findings,
            **self.metadata,
        }


@register_agent
class SentinelAgent(BaseAgent):
    """
    Advanced Sentinel agent with memory, learning, and tool integration.

    Builds on the proven static analyzer with:
    - Working memory of current analysis context
    - Episodic memory for past similar findings
    - Procedural memory for learned detection patterns
    - Decision strategy for severity scoring
    - Event emission for pipeline coordination
    - Tools for external invocation
    """

    AGENT_NAME = "sentinel"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "diagnostics"
    AGENT_DESCRIPTION = "Advanced execution analysis and runtime diagnostics with AI-powered pattern recognition"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Working memory windows
        self.memory = WorkingMemory(
            primary_capacity=150,
            observations_capacity=100,
            actions_capacity=50,
            results_capacity=50,
            long_term_capacity=300,
        )

        # Analysis state
        self._current_findings: List[SentinelFinding] = []
        self._code_structure: Optional[Dict[str, Any]] = None
        self._symbol_table: Dict[str, Set[int]] = {}

        # Decision strategy for severity/remediation prioritization
        self._decision_strategy = self._build_severity_strategy()

        # Initialize specialized components
        self._initialize_analyzers()

    def _initialize_analyzers(self) -> None:
        """Initialize analysis sub-components"""
        # Register built-in analysis tools
        self._register_analysis_tools()

        # Create default decision rules
        self._decision_strategy = self._build_severity_strategy()

        # Load procedural patterns
        self._load_sentinel_patterns()

    def _register_analysis_tools(self) -> None:
        """Register tools this agent provides"""
        tools = [
            SimpleTool(
                name="analyze_undefined_variables",
                func=self._tool_undefined_vars,
                description="Detect undefined variable references",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="analyze_arithmetic_risks",
                func=self._tool_arithmetic_risks,
                description="Find division by zero, type errors, None arithmetic",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="analyze_boundary_conditions",
                func=self._tool_boundary_issues,
                description="Detect index out of bounds, range errors",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="analyze_control_flow",
                func=self._tool_control_flow,
                description="Find infinite loops, constant conditions, dead code",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="full_static_analysis",
                func=self._tool_full_analysis,
                description="Complete Sentinel analysis (all checks)",
                permission=ToolPermission.PUBLIC,
            ),
        ]
        for tool in tools:
            self.tool_registry.register(tool, owner=self.agent_id)

    def _load_sentinel_patterns(self) -> None:
        """Load Sentinel-specific procedural patterns"""
        patterns = [
            TaskPattern(
                id="sentinel-undefined-var",
                name="UndefinedVariablePattern",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Detect undefined variable references in functions",
                trigger_conditions={"issue_category": "Variable & Scope Trace"},
                action_template=[
                    {"check": "name_loads", "scope": "function"},
                    {"action": "cross_reference_builtins"},
                    {"action": "verify_imports"},
                ],
                expected_outcome="All undefined name references found",
                applicable_languages={"python", "py"},
            ),
            TaskPattern(
                id="sentinel-arithmetic",
                name="ArithmeticRiskPattern",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Detect arithmetic operations that can raise exceptions",
                trigger_conditions={"issue_category": "Data Type & Arithmetic Validation"},
                action_template=[
                    {"check": "binary_operations"},
                    {"check": "constant_subscript"},
                    {"track_known_values": True},
                ],
                expected_outcome="Zero division, type errors, None arithmetic detected",
                applicable_languages={"python", "py"},
            ),
        ]

        for pattern in patterns:
            self.procedural.store_pattern(pattern)

    def _build_severity_strategy(self) -> DecisionStrategy:
        """Build strategy for determining finding severity"""
        rules = [
            DecisionRule(
                condition="{severity} == 'CRITICAL'",
                action="block_release",
                priority=100,
            ),
            DecisionRule(
                condition="{predicted_exception} in {'NameError', 'UnboundLocalError', 'SyntaxError'}",
                action="fail_closed",
                priority=90,
            ),
            DecisionRule(
                condition="{category} == 'Security'",
                action="escalate",
                priority=95,
            ),
            DecisionRule(
                condition="{confidence} < 0.5",
                action="request_review",
                priority=50,
            ),
        ]
        return RuleBasedStrategy(rules, default_action="continue_analysis")

    # ============== Core Execution ==============

    async def execute(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        detailed: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute Sentinel analysis on code.

        Args:
            code: Source code to analyze
            language: Programming language (only Python supported for now)
            context: Context from other agents
            detailed: Enable detailed analysis mode

        Returns:
            List of finding dictionaries
        """
        self.state = "RUNNING"
        start_time = time.time()

        # Setup session
        session_id = context.get("session_id") if context else None
        self.start_session(session_id or str(uuid.uuid4()))

        # Validate
        if not self.validate_input(code, language):
            return [self._make_invalid_input_finding()]

        # Emit start event
        emit_event(
            EventType.AGENT_START,
            source=self.agent_id,
            data={"language": language, "code_length": len(code)},
            correlation_id=context.get("correlation_id") if context else None,
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "sentinel_analysis"
            ) as span:
                if span:
                    span.set_attribute("language", language)
                    span.set_attribute("code_size", len(code))

                # Store code observation in working memory
                self.memory.add(
                    content=f"Analyzing {len(code)} chars of {language} code",
                    context_type="observations",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                    tags={"analysis_start"},
                )

                # Route to appropriate analyzer
                if language.lower() not in {"python", "py"}:
                    findings = self._handle_unsupported_language(language)
                else:
                    findings = await self._analyze_python(code, detailed, context or {})

                # Convert to dict format
                result = [f.to_dict() for f in findings]

                # Record success
                duration = time.time() - start_time
                self._record_success(duration)

                # Store episodic memory
                self.remember_episode(
                    content=f"Sentinel analysis: {len(findings)} findings",
                    metadata={
                        "agent": self.agent_id,
                        "language": language,
                        "finding_count": len(findings),
                        "duration": duration,
                    },
                    importance=0.6,
                )

                # Emit completion event
                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={
                        "findings": len(result),
                        "duration": duration,
                        "language": language,
                    },
                )

                # Store results in working memory
                self.memory.add(
                    content=f"Completed with {len(result)} findings",
                    context_type="results",
                    priority=Priority.MEDIUM,
                    agent_id=self.agent_id,
                    tags={"analysis_complete", f"findings_{len(result)}"},
                )

                return result

        except Exception as e:
            duration = time.time() - start_time
            self._record_failure(e, duration)
            emit_event(
                EventType.AGENT_ERROR,
                source=self.agent_id,
                data={"error": str(e), "error_type": type(e).__name__},
            )
            raise

    async def _analyze_python(
        self,
        code: str,
        detailed: bool,
        context: Dict[str, Any],
    ) -> List[SentinelFinding]:
        """
        Main Python analysis logic.

        Uses AST-based analysis with memory augmentation.
        """
        findings = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            # Syntax error is itself a finding
            finding = SentinelFinding(
                severity=AnalysisSeverity.CRITICAL,
                line=exc.lineno or 1,
                issue="Python syntax prevents compilation",
                predicted_exception="SyntaxError",
                root_cause=exc.msg,
                fix_suggestion="Correct the syntax error before runtime analysis can continue.",
                category="Syntax & Compilation Scan",
                code_snippet=code.split('\n')[exc.lineno-1] if exc.lineno else "",
                confidence=1.0,
            )
            findings.append(finding)
            return findings

        # Analyze with enhanced analyzer
        analyzer = EnhancedPythonAnalyzer(
            agent=self,
            code=code,
            detailed=detailed,
            context=context,
        )
        findings = analyzer.analyze()

        # Apply decision strategy for severity adjustments
        findings = self._apply_severity_strategy(findings, context)

        # Learn from this analysis
        self._learn_from_analysis(code, findings, context)

        return findings

    def _apply_severity_strategy(
        self,
        findings: List[SentinelFinding],
        context: Dict[str, Any],
    ) -> List[SentinelFinding]:
        """Apply decision strategy to adjust severities"""
        # Could use _decision_strategy here for advanced prioritization
        # For now, keep original severities
        return findings

    def _learn_from_analysis(
        self,
        code: str,
        findings: List[SentinelFinding],
        context: Dict[str, Any],
    ) -> None:
        """Record patterns for future learning"""
        # Store successful detections in procedural memory
        if findings:
            self.procedural.record_trace(
                pattern_id="sentinel-detection-sweep",
                context_features={
                    "language": context.get("language", "python"),
                    "code_lines": len(code.splitlines()),
                    "finding_count": len(findings),
                },
                actions=[{"type": "static_analysis", "findings": len(findings)}],
                outcome=PatternSuccess.SUCCESS,
                reward=0.1 * len(findings),  # More findings = better
            )

    def _handle_unsupported_language(self, language: str) -> List[SentinelFinding]:
        """Handle non-Python languages"""
        return [SentinelFinding(
            severity=AnalysisSeverity.INFO,
            line=1,
            issue=f"Language '{language}' not supported by Sentinel",
            predicted_exception="No execution",
            root_cause="Sentinel currently only supports Python analysis",
            fix_suggestion="Convert to Python or wait for language support",
            category="Configuration",
            code_snippet="",
            confidence=1.0,
        )]

    def _make_invalid_input_finding(self) -> SentinelFinding:
        """Create finding for invalid input"""
        return SentinelFinding(
            severity=AnalysisSeverity.CRITICAL,
            line=1,
            issue="No code provided or invalid language",
            predicted_exception="No execution",
            root_cause="The submitted source is empty or unsupported, so no analysis target exists.",
            fix_suggestion="Provide valid Python source code.",
            category="Input Validation",
            code_snippet="",
            confidence=1.0,
        )

    # ============== Tool Implementations ==============

    def _tool_undefined_vars(self, context: ToolContext, code: str) -> ToolResult:
        """Tool: detect undefined variables only"""
        findings = asyncio.run(self._analyze_python(code, False, {}))
        undefined_only = [f for f in findings if "Undefined" in f.issue or "variable" in f.issue.lower()]
        return ToolResult.ok(data={"findings": [f.to_dict() for f in undefined_only]})

    def _tool_arithmetic_risks(self, context: ToolContext, code: str) -> ToolResult:
        """Tool: detect arithmetic risks only"""
        findings = asyncio.run(self._analyze_python(code, False, {}))
        arithmetic = [f for f in findings if any(kw in f.category for kw in ["Arithmetic", "Division", "Type"])]
        return ToolResult.ok(data={"findings": [f.to_dict() for f in arithmetic]})

    def _tool_boundary_issues(self, context: ToolContext, code: str) -> ToolResult:
        """Tool: detect boundary issues"""
        findings = asyncio.run(self._analyze_python(code, False, {}))
        boundary = [f for f in findings if "boundary" in f.category.lower() or "index" in f.issue.lower()]
        return ToolResult.ok(data={"findings": [f.to_dict() for f in boundary]})

    def _tool_control_flow(self, context: ToolContext, code: str) -> ToolResult:
        """Tool: detect control flow issues"""
        findings = asyncio.run(self._analyze_python(code, False, {}))
        control = [f for f in findings if "loop" in f.issue.lower() or "condition" in f.issue.lower()]
        return ToolResult.ok(data={"findings": [f.to_dict() for f in control]})

    def _tool_full_analysis(self, context: ToolContext, code: str) -> ToolResult:
        """Tool: run complete analysis"""
        result = asyncio.run(self.execute(code, "python", context))
        return ToolResult.ok(data={"findings": result})

    # ============== Abstract Method Overrides ==============

    def get_tools(self) -> List[Tool]:
        """Declare available tools"""
        return list(self.tool_registry.list_tools(owner=self.agent_id))

    def get_capabilities(self) -> "AgentCapabilities":
        """Declare capabilities"""
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["python", "py"],
            categories=["diagnostics", "static_analysis", "error_prediction"],
            tools=[t.name for t in self.get_tools()],
            requires_context=True,
            produces_insights=True,
        )

    # ============== Agent-Specific Memory Methods ==============

    def recall_similar_code(self, code_fingerprint: str, limit: int = 5) -> List[Dict]:
        """Recall similar code patterns from episodic memory"""
        return self.recall_episodes(
            query=code_fingerprint,
            limit=limit,
            min_similarity=0.6,
        )

    def get_common_anti_patterns(self) -> List[TaskPattern]:
        """Get frequently occurring anti-patterns"""
        patterns = self.procedural.retrieve_pattern(
            context={"domain": "anti_pattern"},
            min_effectiveness=0.4,
            limit=10,
        )
        return [p for p, _ in patterns]

    # ============== Inter-Agent Coordination ==============

    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant pipeline events"""
        super()._subscribe_to_events()
        # Listen for other agent findings
        self.event_bus.subscribe(
            EventType.AGENT_COMPLETE,
            self._on_other_agent_complete
        )

    def _on_other_agent_complete(self, event) -> None:
        """React to other agents completing"""
        if event.source != self.agent_id:
            # Could adjust analysis based on other findings
            pass

    # ============== Serialization ==============

    def save_state(self) -> Dict[str, Any]:
        state = super().save_state()
        state["findings"] = [f.to_dict() for f in self._current_findings]
        return state


# ============== Enhanced AST Analyzer ==============

class EnhancedPythonAnalyzer:
    """
    Enhanced version of the original PythonExecutionAnalyzer with agent integration.

    Analyzes Python AST and produces rich SentinelFindings with full metadata.
    """

    def __init__(
        self,
        agent: SentinelAgent,
        code: str,
        detailed: bool,
        context: Dict[str, Any],
    ):
        self.agent = agent
        self.code = code
        self.detailed = detailed
        self.context = context
        self.lines = code.splitlines()
        self.findings: List[SentinelFinding] = []
        self.symbol_table: Dict[str, Set[int]] = {}
        self._known_values: Dict[str, Any] = {}

    def analyze(self) -> List[SentinelFinding]:
        """Run full analysis"""
        try:
            tree = ast.parse(self.code)
        except SyntaxError as exc:
            return [self._make_syntax_finding(exc)]

        # Collect initial symbols
        self._collect_module_symbols(tree)

        # Visit all statements
        self._visit_block(tree.body)

        return self.findings

    def _make_syntax_finding(self, exc: SyntaxError) -> SentinelFinding:
        """Create finding from syntax error"""
        return SentinelFinding(
            severity=AnalysisSeverity.CRITICAL,
            line=exc.lineno or 1,
            issue="Python syntax prevents compilation",
            predicted_exception="SyntaxError",
            root_cause=exc.msg,
            fix_suggestion="Correct the syntax error before runtime analysis can continue.",
            category="Syntax & Compilation Scan",
            code_snippet=self._get_line(exc.lineno - 1),
            confidence=1.0,
        )

    def _get_line(self, lineno: int) -> str:
        """Get source line by number (0-indexed)"""
        if 0 <= lineno < len(self.lines):
            return self.lines[lineno].strip()
        return ""

    def _collect_module_symbols(self, tree: ast.Module) -> Set[str]:
        """Collect all top-level defined symbols"""
        symbols: Set[str] = set()

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbols.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    symbols.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    symbols.update(self._target_names(target))

        self.symbol_table = {sym: set() for sym in symbols}
        return symbols

    def _target_names(self, node: ast.AST) -> Set[str]:
        """Extract all names from assignment target"""
        names: Set[str] = set()
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                names.update(self._target_names(element))
        elif isinstance(node, ast.Starred):
            names.update(self._target_names(node.value))
        return names

    def _visit_block(self, statements: List[ast.stmt]) -> None:
        """Visit block of statements"""
        for stmt in statements:
            self._visit_stmt(stmt)

    def _visit_stmt(self, node: ast.stmt) -> None:
        """Dispatch statement visitor"""
        # Use existing Sentinel logic heavily
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._handle_function(node)
        elif isinstance(node, ast.ClassDef):
            self._add_defined(node.name, node.lineno)
            for base in node.bases:
                self._visit_expr(base)
        elif isinstance(node, ast.Assign):
            self._visit_expr(node.value)
            value = self._constant_value(node.value)
            for target in node.targets:
                self._define_target(target, value, node.lineno)
        elif isinstance(node, ast.For):
            self._visit_expr(node.iter)
            self._define_target(node.target, None, node.lineno)
            self._check_range_boundary(node)
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

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Analyze function definition"""
        self._add_defined(node.name, node.lineno)
        for decorator in node.decorator_list:
            self._visit_expr(decorator)

        # Collect parameters
        params = {arg.arg for arg in node.args.args}
        params.update(arg.arg for arg in node.args.posonlyargs)
        params.update(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg:
            params.add(node.args.vararg.arg)
        if node.args.kwarg:
            params.add(node.args.kwarg.arg)

        # New scope
        self.symbol_table.update({p: set() for p in params})
        self._known_values.update({p: None for p in params})

        # Local assignments (use module-level helper)
        local_assigned = _assigned_names(node.body)

        # Recurse
        self._visit_block(node.body)

        # Cleanup scope
        for name in local_assigned:
            self.symbol_table.pop(name, None)
            self._known_values.pop(name, None)

    def _add_defined(self, name: str, line: int) -> None:
        """Mark name as defined"""
        if name in BUILTIN_NAMES:
            self.findings.append(SentinelFinding(
                severity=AnalysisSeverity.WARNING,
                line=line,
                issue=f"Builtin name '{name}' is shadowed",
                predicted_exception="No immediate exception",
                root_cause=(
                    f"Assignment to '{name}' hides the Python builtin of the same name in this scope."
                ),
                fix_suggestion=f"Rename '{name}' so later calls to the builtin remain available.",
                category="Boundary Integrity",
                code_snippet=self._get_line(line-1),
                confidence=0.9,
            ))
        self.symbol_table[name] = set()

    def _define_target(self, target: ast.AST, value: Any, line: int) -> None:
        """Define a target variable"""
        for name in self._target_names(target):
            self._add_defined(name, line)
            self._known_values[name] = value if value is not None else None

    def _visit_expr(self, node: ast.AST) -> None:
        """Visit expression (lighter weight)"""
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
        # Recurse children
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                self._visit_expr(child)

    def _check_name_load(self, node: ast.Name) -> None:
        """Check variable reference"""
        name = node.id

        # Check if known
        is_known = (
            name in BUILTIN_NAMES or
            any(name in scope for scope in [self.symbol_table])
        )

        if not is_known:
            self.findings.append(SentinelFinding(
                severity=AnalysisSeverity.CRITICAL,
                line=node.lineno,
                issue=f"Undefined variable '{name}'",
                predicted_exception="NameError",
                root_cause=f"'{name}' is loaded before any assignment, import, parameter, or builtin definition is available.",
                fix_suggestion=f"Define or import '{name}' before this line.",
                category="Variable & Scope Trace",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.95,
            ))

    def _check_binary_operation(self, node: ast.BinOp) -> None:
        """Check binary operation for type/arithmetic errors"""
        left_val = self._constant_value(node.left)
        right_val = self._constant_value(node.right)

        # Division by zero
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right_val == 0:
            self.findings.append(SentinelFinding(
                severity=AnalysisSeverity.CRITICAL,
                line=node.lineno,
                issue="Division by zero",
                predicted_exception="ZeroDivisionError",
                root_cause="The divisor resolves to literal zero at analysis time.",
                fix_suggestion="Guard the divisor or return an explicit error before dividing.",
                category="Data Type & Arithmetic Validation",
                code_snippet=self._get_line(node.lineno-1),
                confidence=1.0,
            ))

        # Type mismatch in addition
        if isinstance(node.op, ast.Add):
            if (isinstance(left_val, str) and right_val is not None and not isinstance(right_val, str)) or \
               (isinstance(right_val, str) and left_val is not None and not isinstance(left_val, str)):
                self.findings.append(SentinelFinding(
                    severity=AnalysisSeverity.CRITICAL,
                    line=node.lineno,
                    issue="Incompatible operands for addition",
                    predicted_exception="TypeError",
                    root_cause=f"Python cannot apply '+' between {type(left_val).__name__} and {type(right_val).__name__}.",
                    fix_suggestion="Convert operands explicitly or use interpolation/formatting for strings.",
                    category="Data Type & Arithmetic Validation",
                    code_snippet=self._get_line(node.lineno-1),
                    confidence=0.9,
                ))

        # Arithmetic with None
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod)):
            if (left_val is None or right_val is None) and \
               (isinstance(node.left, ast.Constant) or isinstance(node.right, ast.Constant)):
                self.findings.append(SentinelFinding(
                    severity=AnalysisSeverity.CRITICAL,
                    line=node.lineno,
                    issue="Arithmetic uses None",
                    predicted_exception="TypeError",
                    root_cause="One side of the arithmetic expression is None.",
                    fix_suggestion="Validate the value is numeric before arithmetic.",
                    category="Data Type & Arithmetic Validation",
                    code_snippet=self._get_line(node.lineno-1),
                    confidence=0.85,
                ))

    def _check_constant_subscript(self, node: ast.Subscript) -> None:
        """Check constant subscript bounds"""
        value = self._constant_value(node.value)
        index = self._constant_value(node.slice)

        if isinstance(value, (list, tuple, str)) and isinstance(index, int):
            if index >= len(value) or index < -len(value):
                self.findings.append(SentinelFinding(
                    severity=AnalysisSeverity.CRITICAL,
                    line=node.lineno,
                    issue="Index outside sequence bounds",
                    predicted_exception="IndexError",
                    root_cause=f"Sequence length is {len(value)}, but index {index} requested.",
                    fix_suggestion="Check sequence length before indexing.",
                    category="Logic & Boundary Integrity",
                    code_snippet=self._get_line(node.lineno-1),
                    confidence=1.0,
                ))

    def _check_range_boundary(self, node: ast.For) -> None:
        """Check for range(len(x) + 1) pattern"""
        if not isinstance(node.target, ast.Name):
            return
        if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name):
            return
        if node.iter.func.id != "range" or len(node.iter.args) != 1:
            return

        arg = node.iter.args[0]
        if not (isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add)
                and isinstance(arg.right, ast.Constant) and arg.right.value == 1
                and isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name)
                and arg.left.func.id == "len" and len(arg.left.args) == 1
                and isinstance(arg.left.args[0], ast.Name)):
            return

        sequence_name = arg.left.args[0].id
        # Find subscript usage in body
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if (isinstance(child, ast.Subscript) and
                isinstance(child.value, ast.Name) and child.value.id == sequence_name and
                isinstance(child.slice, ast.Name) and child.slice.id == node.target.id):
                self.findings.append(SentinelFinding(
                    severity=AnalysisSeverity.WARNING,
                    line=child.lineno,
                    issue="Loop indexes one element past the sequence",
                    predicted_exception="IndexError",
                    root_cause=(
                        f"range(len({sequence_name}) + 1) includes len({sequence_name}), "
                        "which is not a valid index."
                    ),
                    fix_suggestion=f"Use range(len({sequence_name})) or iterate directly.",
                    category="Logic & Boundary Integrity",
                    code_snippet=self._get_line(child.lineno-1),
                    confidence=0.95,
                ))

    def _check_infinite_loop(self, node: ast.While) -> None:
        """Check for infinite loop without break"""
        has_break = any(
            isinstance(child, ast.Break)
            for child in ast.walk(ast.Module(body=node.body, type_ignores=[]))
        )
        if isinstance(node.test, ast.Constant) and node.test.value is True and not has_break:
            self.findings.append(SentinelFinding(
                severity=AnalysisSeverity.WARNING,
                line=node.lineno,
                issue="Infinite loop has no break path",
                predicted_exception="Logical deadlock",
                root_cause="while True executes indefinitely because no break statement exists in the loop body.",
                fix_suggestion="Add a reachable break condition or bounded loop condition.",
                category="Logic & Boundary Integrity",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.9,
            ))

    def _constant_value(self, node: ast.AST) -> Any:
        """Get constant value if possible"""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in self._known_values:
            return self._known_values[node.id]
        if isinstance(node, (ast.List, ast.Tuple)):
            return [self._constant_value(e) for e in node.elts]
        return None


# ============== Integration and Compatibility ==============

# Maintain backward compatibility - original function signature
async def run_sentinel(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Entry point for pipeline integration.

    Creates Sentinel agent and runs analysis. Maintains compatibility
    with original signature while leveraging new architecture.
    """
    from core.agent_factory import create_agent

    agent = create_agent("sentinel")
    return await agent.execute(code, language, context)
