"""
Critic Agent - Formal Review & Semantic Defect Detection

Advanced Critic with multi-tiered memory for detecting:
- Design contract violations
- SOLID principle violations
- Semantic defects
- Async/await misuse
- Exception handling anti-patterns
- Function complexity issues
- Return contract inconsistencies

Learns from past code reviews and improves detection accuracy over time.
"""

import ast
import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set
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
from core.tools import SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import DecisionStrategy, ScoringStrategy, Criterion, recency_criterion

logger = logging.getLogger(__name__)


class ReviewSeverity(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class CriticFinding:
    """Structured finding from Critic"""
    severity: ReviewSeverity
    line: int
    issue: str
    root_cause: str
    fix_suggestion: str
    category: str
    code_snippet: str
    confidence: float
    agent_id: str = "critic"
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_id,
            "severity": self.severity.value,
            "lineNumber": self.line,
            "issue": self.issue,
            "predictedException": "Semantic defect",
            "rootCause": self.root_cause,
            "fix": self.fix_suggestion,
            "impact": self.root_cause,
            "category": self.category,
            "confidence": self.confidence,
            "tags": list(self.tags),
            **self.metadata,
        }


@register_agent
class CriticAgent(BaseAgent):
    """
    Enhanced Critic agent for formal review and semantic analysis.

    Specializes in:
    - Semantic correctness beyond syntax
    - Design principle violations (SOLID, DRY, etc.)
    - Code maintainability and clarity
    - Async/await proper usage
    - Exception handling adequacy
    - Function complexity management
    - Return value consistency
    """

    AGENT_NAME = "critic"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "formal-review"
    AGENT_DESCRIPTION = "Advanced semantic code review with design principle enforcement"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.memory = WorkingMemory(
            primary_capacity=150,
            observations_capacity=100,
            actions_capacity=50,
            long_term_capacity=300,
        )

        # Analysis state
        self._findings: List[CriticFinding] = []
        self._function_complexity: Dict[str, Dict[str, int]] = {}
        self._async_functions: Set[str] = set()
        self._exception_handlers: List[str] = []

        # Load patterns
        self._load_critic_patterns()
        self._decision_strategy = self._build_review_strategy()

    def _load_critic_patterns(self) -> None:
        """Load procedural patterns for code review"""
        patterns = [
            TaskPattern(
                id="critic-single-responsibility",
                name="Single Responsibility Violation",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Function does too much (excessive statements/branches)",
                trigger_conditions={"category": "SOLID & Clean Code"},
                action_template=[
                    {"check": "statement_count", "threshold": 50},
                    {"check": "branch_count", "threshold": 10},
                    {"action": "suggest_split"},
                ],
                expected_outcome="Functions with manageable complexity",
                applicable_languages={"python", "javascript", "typescript", "java"},
            ),
            TaskPattern(
                id="critic-inconsistent-return",
                name="Inconsistent Return Contract",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Function returns values and None inconsistently",
                trigger_conditions={"issue": "inconsistent return contract"},
                action_template=[
                    {"inspect": "return_statements"},
                    {"check": "value_vs_none"},
                    {"action": "unify_return_type"},
                ],
                expected_outcome="Consistent return types across all paths",
                applicable_languages={"python", "javascript", "typescript", "java"},
            ),
            TaskPattern(
                id="critic-broad-exception",
                name="Broad Exception Handler",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Catch-all except without re-raise or typed handling",
                trigger_conditions={"category": "Robustness & Error Handling"},
                action_template=[
                    {"detect": "bare_except"},
                    {"check": "has_reraise"},
                    {"action": "specify_exception_types"},
                ],
                expected_outcome="Typed error handling with proper recovery",
                applicable_languages={"python", "java", "javascript"},
            ),
            TaskPattern(
                id="critic-async-without-await",
                name="Async Function Without Await",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Async function declared but contains no await",
                trigger_conditions={"issue": "Async function has no await boundary"},
                action_template=[
                    {"detect": "async_def"},
                    {"check": "contains_await"},
                    {"action": "remove_async_or_add_await"},
                ],
                expected_outcome="Proper async boundary usage",
                applicable_languages={"python", "javascript"},
            ),
        ]

        for pattern in patterns:
            self.procedural.store_pattern(pattern)

    def _build_review_strategy(self) -> DecisionStrategy:
        """Build strategy for review severity and recommendation"""
        # Use weighted scoring to determine which issues need escalation
        criteria = [
            Criterion(
                name="severity_weight",
                weight=0.4,
                scorer=self._score_severity,
            ),
            Criterion(
                name="complexity_impact",
                weight=0.2,
                scorer=self._score_complexity,
            ),
            Criterion(
                name="pattern_frequency",
                weight=0.2,
                scorer=self._score_frequency,
            ),
            Criterion(
                name="confidence",
                weight=0.2,
                scorer=self._score_confidence,
            ),
        ]
        return ScoringStrategy(criteria)

    def _score_severity(self, context: Dict, options: List[str]) -> Dict[str, float]:
        """Score based on severity of potential issue"""
        return {
            "review": 0.9 if context.get("severity") in ["CRITICAL", "HIGH"] else 0.6,
            "note": 0.3,
        }

    def _score_complexity(self, context: Dict, options: List[str]) -> Dict[str, float]:
        """Score based on code complexity"""
        lines = context.get("lines_of_code", 0)
        complex_score = min(1.0, lines / 100)
        return {"review": complex_score, "note": 0.2}

    def _score_frequency(self, context: Dict, options: List[str]) -> Dict[str, float]:
        """Score based on pattern frequency"""
        freq = context.get("pattern_frequency", 0)
        return {"review": min(1.0, freq / 5), "note": 0.1}

    def _score_confidence(self, context: Dict, options: List[str]) -> Dict[str, float]:
        """Score based on confidence"""
        conf = context.get("confidence", 0.5)
        return {"review": conf, "note": conf}

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
        Execute formal review on code.

        Args:
            code: Source code
            language: Programming language
            context: Previous agent findings (e.g., Sentinel)
            detailed: Enable deep semantic analysis

        Returns:
            List of review findings
        """
        self.state = "RUNNING"
        start_time = time.time()

        session_id = context.get("session_id") if context else None
        self.start_session(session_id or str(uuid.uuid4()))

        emit_event(
            EventType.AGENT_START,
            source=self.agent_id,
            data={"language": language, "detailed": detailed},
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "critic_analysis"
            ) as span:
                if span:
                    span.set_attribute("language", language)
                    span.set_attribute("detailed", detailed)

                self.memory.add(
                    content=f"Starting formal review of {language} code",
                    context_type="observations",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                    tags={"review_start"},
                )

                # Only Python supported for now
                if language.lower() not in {"python", "py"}:
                    findings = [self._unsupported_language_finding(language)]
                else:
                    findings = await self._review_python(code, detailed, context or {})

                result = [f.to_dict() for f in findings]

                duration = time.time() - start_time
                self._record_success(duration)

                self.remember_episode(
                    content=f"Critic review: {len(result)} semantic findings",
                    metadata={
                        "agent": self.agent_id,
                        "language": language,
                        "duration": duration,
                        "findings": len(result),
                    },
                    importance=0.6,
                )

                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={"findings": len(result), "duration": duration},
                )

                self.memory.add(
                    content=f"Review complete: {len(result)} findings",
                    context_type="results",
                    priority=Priority.MEDIUM,
                    agent_id=self.agent_id,
                )

                return result

        except Exception as e:
            duration = time.time() - start_time
            self._record_failure(e, duration)
            emit_event(EventType.AGENT_ERROR, source=self.agent_id, data={"error": str(e)})
            raise

    async def _review_python(
        self,
        code: str,
        detailed: bool,
        context: Dict[str, Any],
    ) -> List[CriticFinding]:
        """Perform detailed Python code review"""
        findings = []

        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Sentinel already caught syntax errors
            return []

        # Initialize analysis state
        self._function_complexity.clear()
        self._async_functions.clear()

        # Use sophisticated visitor
        visitor = EnhancedReviewVisitor(
            agent=self,
            code=code,
            detailed=detailed,
            sentinel_context=context.get("sentinel", []),
        )
        findings = visitor.analyze()

        # Apply decision strategy to find escalation candidates
        findings = self._apply_review_strategy(findings, context)

        # Learn
        self._learn_from_review(code, findings, context)

        return findings

    def _apply_review_strategy(
        self,
        findings: List[CriticFinding],
        context: Dict[str, Any],
    ) -> List[CriticFinding]:
        """Apply scoring strategy to prioritize findings"""
        for finding in findings:
            context_for_scoring = {
                "severity": finding.severity.value,
                "lines_of_code": len(self.code) if hasattr(self, 'code') else 0,
                "confidence": finding.confidence,
                "pattern_frequency": 0,
            }
            result = self._decision_strategy.decide(
                context_for_scoring,
                ["review", "note"]
            )
            # Adjust severity based on score
            if result[1] < 0.4:
                finding.severity = ReviewSeverity.LOW
            elif result[1] < 0.7:
                finding.severity = ReviewSeverity.MEDIUM

        return findings

    def _learn_from_review(
        self,
        code: str,
        findings: List[CriticFinding],
        context: Dict[str, Any],
    ) -> None:
        """Store review patterns"""
        if findings:
            self.procedural.record_trace(
                pattern_id="critic-review-sweep",
                context_features={
                    "language": "python",
                    "code_lines": len(code.splitlines()),
                    "findings": len(findings),
                },
                actions=[{"type": "formal_review", "issues_found": len(findings)}],
                outcome=PatternSuccess.SUCCESS,
                reward=0.1 * len(findings),
            )

    def _unsupported_language_finding(self, language: str) -> CriticFinding:
        return CriticFinding(
            severity=ReviewSeverity.INFO,
            line=1,
            issue=f"Language '{language}' not supported by Critic",
            predicted_exception="No analysis",
            root_cause="Critic currently only supports Python formal review",
            fix_suggestion="Convert to Python or wait for language support",
            category="Configuration",
            code_snippet="",
            confidence=1.0,
        )

    # ============== Tools ==============

    def get_tools(self) -> List[SimpleTool]:
        """Tools provided by Critic"""
        return [
            SimpleTool(
                name="check_solid_principles",
                func=self._tool_check_solid,
                description="Evaluate SOLID principle violations",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="check_async_patterns",
                func=self._tool_check_async,
                description="Detect async/await misuse patterns",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="check_exception_handling",
                func=self._tool_check_exceptions,
                description="Evaluate exception handling quality",
                permission=ToolPermission.PUBLIC,
            ),
        ]

    def _tool_check_solid(self, context: ToolContext, code: str) -> ToolResult:
        result = asyncio.run(self.execute(code, "python", {}))
        solid_issues = [f for f in result if "SOLID" in f.get("category", "")]
        return ToolResult.ok(data={"findings": solid_issues})

    def _tool_check_async(self, context: ToolContext, code: str) -> ToolResult:
        result = asyncio.run(self.execute(code, "python", {}))
        async_issues = [f for f in result if "async" in f.get("issue", "").lower()]
        return ToolResult.ok(data={"findings": async_issues})

    def _tool_check_exceptions(self, context: ToolContext, code: str) -> ToolResult:
        result = asyncio.run(self.execute(code, "python", {}))
        exc_issues = [f for f in result if "exception" in f.get("category", "").lower()]
        return ToolResult.ok(data={"findings": exc_issues})

    def get_capabilities(self):
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["python", "py"],
            categories=["formal-review", "semantic-analysis", "design-review"],
            tools=[t.name for t in self.get_tools()],
            requires_context=True,
            produces_insights=True,
        )

    # ============== Event Handlers ==============

    def _subscribe_to_events(self) -> None:
        super()._subscribe_to_events()
        self.event_bus.subscribe(
            EventType.FINDING_DETECTED,
            self._on_finding_detected
        )

    def _on_finding_detected(self, event) -> None:
        """Learn from other agent findings"""
        # Record cross-agent patterns
        pass


# ============== Enhanced AST Visitor ==============

class EnhancedReviewVisitor(ast.NodeVisitor):
    """
    Advanced AST visitor for formal review.

    Extends original Critic with richer context, cross-agent correlation,
    and pattern learning capabilities.
    """

    def __init__(
        self,
        agent: CriticAgent,
        code: str,
        detailed: bool,
        sentinel_context: List[Dict],
    ):
        self.agent = agent
        self.code = code
        self.lines = code.splitlines()
        self.detailed = detailed
        self.sentinel_findings = sentinel_context
        self.findings: List[CriticFinding] = []
        self.function_stack: List[ast.FunctionDef] = []
        self._current_function: Optional[str] = None

    def analyze(self) -> List[CriticFinding]:
        """Run analysis"""
        self.visit(self.tree)
        return self.findings

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function definition"""
        self._current_function = node.name
        self._inspect_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function"""
        self._current_function = node.name
        self.agent._async_functions.add(node.name)

        # Check for await
        has_await = any(isinstance(child, ast.Await) for child in ast.walk(node))
        if not has_await:
            self.findings.append(CriticFinding(
                severity=ReviewSeverity.WARNING,
                line=node.lineno,
                issue="Async function has no await boundary",
                root_cause="The function advertises asynchronous behavior but executes synchronously.",
                fix_suggestion="Remove async or introduce a real awaited operation with timeout/error handling.",
                category="SOLID & Clean Code",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.9,
            ))

        self._inspect_function(node)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Check if statement"""
        if isinstance(node.test, ast.Constant):
            self.findings.append(CriticFinding(
                severity=ReviewSeverity.WARNING,
                line=node.lineno,
                issue="Branch condition is constant",
                root_cause="A constant condition creates dead code or an always-on branch.",
                fix_suggestion="Replace the condition with a real predicate or delete unreachable branch.",
                category="Logic & Semantic Review",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.95,
            ))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        """Check identity comparisons with literals"""
        if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Is, ast.IsNot)):
            comparable = [node.left, *node.comparators]
            if any(isinstance(item, ast.Constant) and item.value not in {None, True, False}
                   for item in comparable):
                self.findings.append(CriticFinding(
                    severity=ReviewSeverity.WARNING,
                    line=node.lineno,
                    issue="Identity comparison used for a literal value",
                    root_cause="'is' checks object identity, not semantic equality.",
                    fix_suggestion="Use == or != for value comparison.",
                    category="Logic & Semantic Review",
                    code_snippet=self._get_line(node.lineno-1),
                    confidence=0.9,
                ))
        self.generic_visit(node)

    def visit_Try(self, node: ast.Try) -> None:
        """Analyze exception handlers"""
        for handler in node.handlers:
            catches_broad = handler.type is None
            catches_exception = (
                isinstance(handler.type, ast.Name) and
                handler.type.id in {"Exception", "BaseException"}
            )
            if catches_broad or catches_exception:
                has_reraise = any(
                    isinstance(child, ast.Raise)
                    for child in ast.walk(ast.Module(body=handler.body, type_ignores=[]))
                )
                if not has_reraise:
                    self.findings.append(CriticFinding(
                        severity=ReviewSeverity.WARNING,
                        line=handler.lineno,
                        issue="Broad exception handler suppresses failure semantics",
                        root_cause="A broad catch without re-raise can hide root causes.",
                        fix_suggestion="Catch explicit exception types and re-raise or return typed failure.",
                        category="Robustness & Error Handling",
                        code_snippet=self._get_line(handler.lineno-1),
                        confidence=0.85,
                    ))
        self.generic_visit(node)

    def _inspect_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Perform deep inspection on function"""
        # Count statements and branches
        statement_count = sum(
            isinstance(child, ast.stmt) for child in ast.walk(node)
        )
        branch_count = sum(
            isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.Match))
            for child in ast.walk(node)
        )
        returns = [c for c in ast.walk(node) if isinstance(c, ast.Return)]

        # Complexity finding
        if statement_count > 50 or branch_count > 10:
            self.findings.append(CriticFinding(
                severity=ReviewSeverity.WARNING,
                line=node.lineno,
                issue="Function carries excessive responsibility",
                root_cause=(
                    f"{node.name} has {statement_count} statements and {branch_count} branches, "
                    "violating Single Responsibility."
                ),
                fix_suggestion="Split orchestration, validation, and side effects into smaller functions.",
                category="SOLID & Clean Code",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.9,
            ))

        # Store metrics
        self.agent._function_complexity[node.name] = {
            "statements": statement_count,
            "branches": branch_count,
            "returns": len(returns),
        }

        # Check return consistency
        returns_value = any(r.value is not None for r in returns)
        returns_none = any(r.value is None for r in returns)
        if returns and returns_value and returns_none:
            self.findings.append(CriticFinding(
                severity=ReviewSeverity.WARNING,
                line=node.lineno,
                issue="Function has inconsistent return contract",
                root_cause="Some paths return a value while others implicitly or explicitly return None.",
                fix_suggestion="Return a single typed result shape from every branch.",
                category="Design Contract",
                code_snippet=self._get_line(node.lineno-1),
                confidence=0.85,
            ))

    def _get_line(self, lineno: int) -> str:
        if 0 <= lineno < len(self.lines):
            return self.lines[lineno].strip()
        return ""


# ============== Compatibility ==============

async def run_critic(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Entry point - creates Critic agent and runs"""
    from core.agent_factory import create_agent
    agent = create_agent("critic")
    return await agent.execute(code, language, context)
