"""
Chaos Engineer Agent - Adversarial Testing & Stress Analysis

Advanced chaos testing agent specializing in:
- Property-based testing strategies
- Fuzzing and boundary value analysis
- Stress and load testing approaches
- Fault injection and resilience testing
- Failure mode analysis
- Chaos engineering experiments
- Regression test generation

Learns from past failures and adapts testing strategies over time.
"""

import asyncio
import logging
import time
import uuid
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from collections import defaultdict

from core.agent_base import BaseAgent, Priority, register_agent
from core.memory import WorkingMemory, EpisodicMemory, ProceduralMemory, PatternType
from core.telemetry import get_telemetry_manager
from core.events import EventType, emit_event
from core.tools import SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import DecisionStrategy, ScoringStrategy, Criterion, relevance_criterion

logger = logging.getLogger(__name__)


class TestType(Enum):
    PROPERTY = "property"          # Property-based testing
    FUZZING = "fuzzing"            # Fuzzing/mutation testing
    BOUNDARY = "boundary"          # Boundary value analysis
    STRESS = "stress"              # Load/stress testing
    CHAOS = "chaos"                # Failure injection
    REGRESSION = "regression"      # Regression test generation
    INTEGRATION = "integration"    # Integration testing


class ChaosSeverity(Enum):
    """Severity of chaos experiment"""
    LOW = "low"           # Minor perturbations
    MEDIUM = "medium"     # Resource constraints
    HIGH = "high"        # Component failures
    CRITICAL = "critical" # Systemic failures


@dataclass
class TestStrategy:
    """A test strategy recommendation"""
    test_type: TestType
    description: str
    target: str
    expected_failure_modes: List[str]
    mitigation_strategies: List[str]
    priority: int
    confidence: float = 0.8
    related_findings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.test_type.value,
            "description": self.description,
            "target": self.target,
            "expected_failures": self.expected_failure_modes,
            "mitigations": self.mitigation_strategies,
            "priority": self.priority,
            "confidence": self.confidence,
        }


@dataclass
class ChaosExperiment:
    """A specific chaos experiment"""
    name: str
    severity: ChaosSeverity
    target_component: str
    fault_type: str
    duration_seconds: int
    success_criteria: List[str]
    rollback_plan: str
    risk_score: float


@register_agent
class ChaosEngineerAgent(BaseAgent):
    """
    Enhanced Chaos Engineer agent for adversarial testing.

    Specializes in:
    - Generating property-based test suites
    - Fuzzing strategies (mutation, grammar-based, coverage-guided)
    - Boundary and edge case identification
    - Stress testing plans
    - Chaos engineering experiments
    - Failure mode detection
    - Anti-pattern testing
    """

    AGENT_NAME = "chaos_engineer"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "testing"
    AGENT_DESCRIPTION = "Adversarial testing, fuzzing, stress testing, and chaos engineering"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.memory = WorkingMemory(
            primary_capacity=150,
            observations_capacity=100,
            long_term_capacity=400,
        )

        self._strategies: List[TestStrategy] = []
        self._known_failure_modes: Dict[str, List[str]] = defaultdict(list)
        self._chaos_history: List[Dict[str, Any]] = []
        self._decision_strategy = self._build_test_selection_strategy()

        # Load patterns
        self._load_chaos_patterns()
        self._initialize_fuzzing_grammar()

    def _load_chaos_patterns(self) -> None:
        """Load test pattern templates"""
        patterns = [
            TaskPattern(
                id="chaos-property-testing",
                name="Property-Based Testing",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="Generate property tests using Hypothesis or QuickCheck",
                trigger_conditions={"test_type": TestType.PROPERTY.value},
                action_template=[
                    {"property": "roundtrip"},
                    {"property": "invariant"},
                    {"property": "idempotent"},
                ],
                expected_outcome="Properties hold across wide input ranges",
                applicable_languages={"python", "javascript", "java"},
            ),
            TaskPattern(
                id="chaos-fuzzing",
                name="Coverage-Guided Fuzzing",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="Generate diverse inputs to uncover edge cases",
                trigger_conditions={"test_type": TestType.FUZZING.value},
                action_template=[
                    {"mutate": "structure"},
                    {"mutate": "values"},
                    {"track": "coverage"},
                ],
                expected_outcome="Crash or unexpected behavior found",
                applicable_languages={"python", "javascript", "c", "cpp"},
            ),
            TaskPattern(
                id="chaos-boundary",
                name="Boundary Value Analysis",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="Test edge cases: min, max, empty, null, special values",
                trigger_conditions={"test_type": TestType.BOUNDARY.value},
                action_template=[
                    {"generate": "min_values"},
                    {"generate": "max_values"},
                    {"generate": "negative"},
                    {"generate": "empty"},
                ],
                expected_outcome="All boundaries handled correctly",
                applicable_languages={"python", "javascript", "java"},
            ),
            TaskPattern(
                id="chaos-stress",
                name="Stress Testing",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="High-load and concurrent access testing",
                trigger_conditions={"test_type": TestType.STRESS.value},
                action_template=[
                    {"ramp_up": "concurrent_users"},
                    {"hold": "peak_load"},
                    {"ramp_down": "gracefully"},
                ],
                expected_outcome="System remains stable under load",
                applicable_languages={"python", "javascript", "go"},
            ),
        ]

        for pattern in patterns:
            self.procedural.store_pattern(pattern)

    def _initialize_fuzzing_grammar(self) -> None:
        """Initialize basic fuzzing grammar"""
        self._fuzz_grammar = {
            "int": lambda: random.randint(-2**31, 2**31 - 1),
            "float": lambda: random.uniform(-1e10, 1e10),
            "str": lambda: "".join(random.choices("abcdefghijklmnopqrstuvwxyz" + "0123456789" * 3, k=random.randint(0, 100))),
            "bool": lambda: random.choice([True, False]),
            "none": lambda: None,
            "empty": lambda: "",
            "huge": lambda: "A" * 10000,
            "unicode": lambda: "🔥" * 100,
        }

    def _build_test_selection_strategy(self) -> DecisionStrategy:
        """Build strategy for selecting test types"""
        return ScoringStrategy(
            criteria=[
                Criterion(
                    name="issue_severity",
                    weight=0.3,
                    scorer=self._score_by_severity,
                ),
                Criterion(
                    name="code_complexity",
                    weight=0.25,
                    scorer=self._score_by_complexity,
                ),
                Criterion(
                    name="finding_category",
                    weight=0.25,
                    scorer=self._score_by_category,
                ),
                Criterion(
                    name="language_support",
                    weight=0.2,
                    scorer=self._score_language_support,
                ),
            ]
        )

    def _score_by_severity(self, ctx, opts):
        severities = ctx.get("severities", [])
        score = 1.0 if any(s in ["CRITICAL", "HIGH"] for s in severities) else 0.6
        return {t: score for t in opts}

    def _score_by_complexity(self, ctx, opts):
        complexity = ctx.get("complexity", 0)
        score = min(1.0, complexity / 10)
        return {t: score for t in opts}

    def _score_by_category(self, ctx, opts):
        cats = ctx.get("categories", [])
        weights = {
            "logic": 0.9,
            "security": 0.9,
            "runtime": 0.8,
            "performance": 0.7,
        }
        max_weight = max([weights.get(c, 0) for c in cats], default=0.5)
        return {t: max_weight for t in opts}

    def _score_language_support(self, ctx, opts):
        lang = ctx.get("language", "")
        supported = {
            "python": {"property", "boundary", "fuzzing", "stress"},
            "javascript": {"property", "fuzzing", "stress"},
            "java": {"property", "boundary", "stress"},
        }
        available = supported.get(lang, {"property", "boundary"})
        return {t: 1.0 if t in available else 0.3 for t in opts}

    # ============== Core Execution ==============

    async def execute(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Generate chaos testing strategies.

        Args:
            code: Source code
            language: Programming language
            context: Findings from other agents

        Returns:
            List of test strategy recommendations
        """
        self.state = "RUNNING"
        start_time = time.time()
        context = context or {}

        session_id = context.get("session_id")
        self.start_session(session_id or str(uuid.uuid4()))

        emit_event(
            EventType.AGENT_START,
            source=self.agent_id,
            data={"language": language},
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "chaos_analysis"
            ) as span:
                if span:
                    span.set_attribute("language", language)

                self.memory.add(
                    content="Starting chaos analysis",
                    context_type="observations",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                    tags={"chaos_start"},
                )

                strategies = await self._generate_strategies(code, language, context)

                # Convert to dicts
                result = [s.to_dict() for s in strategies]

                # Record
                duration = time.time() - start_time
                self._record_success(duration)

                self.remember_episode(
                    content=f"Chaos: {len(result)} strategies generated",
                    metadata={
                        "agent": self.agent_id,
                        "strategies": len(result),
                        "language": language,
                        "duration": duration,
                    },
                    importance=0.7,
                )

                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={"strategies": len(result)},
                )

                self.memory.add(
                    content=f"Generated {len(result)} test strategies",
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

    async def _generate_strategies(
        self,
        code: str,
        language: str,
        context: Dict[str, Any],
    ) -> List[TestStrategy]:
        """Generate tailored test strategies"""
        strategies = []

        # Analyze code structure & issues
        analysis = self._analyze_code_for_testing(code, language, context)

        # Select test types
        test_type_scores = self._decision_strategy.decide(
            analysis,
            [t.value for t in TestType]
        )
        selected_types = [test_type_scores[0]]  # Best match

        # For each test type, generate specific strategy
        for test_type in selected_types:
            strategies.extend(self._create_strategies_for_type(test_type, analysis, context))

        # Always add baseline strategies
        strategies.extend(self._create_baseline_strategies(language))

        # Deduplicate and sort by priority
        seen = set()
        unique = []
        for s in sorted(strategies, key=lambda x: x.priority, reverse=True):
            key = f"{s.test_type}:{s.target}"
            if key not in seen:
                seen.add(key)
                unique.append(s)

        return unique[:10]  # Top 10

    def _analyze_code_for_testing(
        self,
        code: str,
        language: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze code to inform test strategy selection"""
        analysis = {
            "language": language,
            "lines_of_code": len(code.splitlines()),
            "complexity": 0.0,
            "has_io": False,
            "has_state": False,
            "has_concurrency": False,
            "categories": [],
            "severities": [],
        }

        # Analyze structure
        if language.lower() in {"python", "py"}:
            try:
                tree = ast.parse(code)
                # Count functions, classes, branches
                func_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef))
                class_count = sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                analysis["complexity"] = func_count * 0.5 + class_count * 2

                # Look for I/O
                analysis["has_io"] = any(
                    isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in {"open", "read", "write", "fetch", "request"}
                    for n in ast.walk(tree)
                )

                # Look for global state
                analysis["has_state"] = any(
                    isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                    and n.targets[0].id.isupper()  # Convention
                    for n in ast.walk(tree)
                )

            except Exception:
                pass

        # Extract from other agents
        sentinel = context.get("sentinel", [])
        findings_categories = [f.get("category", "") for f in sentinel]
        findings_severities = [f.get("severity", "") for f in sentinel]

        analysis["categories"] = findings_categories
        analysis["severities"] = findings_severities

        # Memory patterns
        recalled = self.recall_episodes(
            query=f"{language} testing strategies",
            limit=5,
            min_similarity=0.5,
        )
        analysis["memory_hits"] = len(recalled)

        return analysis

    def _create_strategies_for_type(
        self,
        test_type_str: str,
        analysis: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[TestStrategy]:
        """Create specific strategies for a test type"""
        test_type = TestType(test_type_str)
        strategies = []
        lang = analysis["language"]

        if test_type == TestType.PROPERTY:
            strategies.append(TestStrategy(
                test_type=TestType.PROPERTY,
                description=f"Define property-based tests for {lang} code",
                target="Core functions and pure algorithms",
                expected_failure_modes=[
                    "Type mismatches",
                    "Invariant violations",
                    "Idempotency failures",
                ],
                mitigation_strategies=[
                    "Use Hypothesis (py) or fast-check (js)",
                    "Define invariants for critical functions",
                    "Run with wide input ranges (1000+ examples)",
                ],
                priority=8,
                confidence=0.9,
            ))

        elif test_type == TestType.FUZZING:
            strategies.append(TestStrategy(
                test_type=TestType.FUZZING,
                description="Structure-aware fuzzing for parser boundaries",
                target="Input parsing, deserialization, API endpoints",
                expected_failure_modes=[
                    "Parser crashes",
                    "Memory corruption",
                    "Unexpected exceptions",
                ],
                mitigation_strategies=[
                    "Use AFL or libFuzzer style mutation",
                    "Track code coverage to guide mutations",
                    "Target parser entry points",
                ],
                priority=7,
                confidence=0.85,
            ))

        elif test_type == TestType.BOUNDARY:
            boundaries = [
                ("empty input", "Empty strings, arrays, objects"),
                ("null/None", "Explicit null handling"),
                ("min/max", "Integer boundaries, length limits"),
                ("unicode", "Emoji, special chars, RTL"),
                ("oversized", "Data > expected size"),
            ]
            for name, target in boundaries[:3]:
                strategies.append(TestStrategy(
                    test_type=TestType.BOUNDARY,
                    description=f"Test {name} conditions",
                    target=target,
                    expected_failure_modes=["IndexError", "TypeError", "ValidationError"],
                    mitigation_strategies=["Add boundary checks", "Use safe APIs"],
                    priority=6,
                    confidence=0.8,
                ))

        elif test_type == TestType.STRESS:
            strategies.append(TestStrategy(
                test_type=TestType.STRESS,
                description="Concurrent load and memory pressure",
                target="Shared resources, database, external APIs",
                expected_failure_modes=[
                    "Race conditions",
                    "Resource exhaustion",
                    "Deadlocks",
                ],
                mitigation_strategies=[
                    "Use thread-safe primitives",
                    "Implement connection pooling",
                    "Add circuit breakers",
                ],
                priority=7,
                confidence=0.75,
            ))

        elif test_type == TestType.CHAOS:
            # Based on sentinel findings if available
            sentinel = context.get("sentinel", [])
            if sentinel:
                strategies.append(TestStrategy(
                    test_type=TestType.CHAOS,
                    description="Inject faults to test resilience",
                    target="System based on runtime defects found",
                    expected_failure_modes=["Degraded service", "Partial failures"],
                    mitigation_strategies=["Add retry logic", "Implement fallbacks"],
                    priority=8,
                    confidence=0.85,
                ))

        return strategies

    def _create_baseline_strategies(self, language: str) -> List[TestStrategy]:
        """Always-included baseline strategies"""
        baselines = [
            TestStrategy(
                test_type=TestType.REGRESSION,
                description="Regression test suite for all fixed bugs",
                target="All historically fixed issues",
                expected_failure_modes=[],
                mitigation_strategies=["Tag each test with bug ID", "Run on every build"],
                priority=9,
                confidence=1.0,
            ),
            TestStrategy(
                test_type=TestType.INTEGRATION,
                description="Integration tests verifying module interfaces",
                target="Public APIs and module boundaries",
                expected_failure_modes=["Contract violations", "Interface changes"],
                mitigation_strategies=["Contract testing", "API versioning"],
                priority=7,
                confidence=0.9,
            ),
        ]
        return baselines

    # ============== Tools ==============

    def get_tools(self) -> List[SimpleTool]:
        return [
            SimpleTool(
                name="generate_property_tests",
                func=self._tool_gen_property,
                description="Generate property test skeletons",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="analyze_failure_modes",
                func=self._tool_analyze_failures,
                description="Analyze potential failure modes",
                permission=ToolPermission.INTERNAL,
            ),
            SimpleTool(
                name="create_chaos_experiment",
                func=self._tool_create_chaos,
                description="Design a chaos experiment",
                permission=ToolPermission.RESTRICTED,
            ),
        ]

    def _tool_gen_property(self, context: ToolContext, code: str, language: str) -> ToolResult:
        strategies = asyncio.run(self.execute(code, language, context.to_dict() if hasattr(context, 'to_dict') else {}))
        property_strats = [s for s in strategies if s["type"] == "property"]
        return ToolResult.ok(data={"strategies": property_strats})

    def _tool_analyze_failures(self, context: ToolContext, code: str, findings: List[Dict]) -> ToolResult:
        # Suggest failures based on findings
        suggestions = []
        for finding in findings:
            if "critical" in finding.get("severity", "").lower():
                suggestions.append(f"Chaos test for: {finding.get('issue', 'unknown')}")
        return ToolResult.ok(data={"failure_modes": suggestions})

    def _tool_create_chaos(self, context: ToolContext, component: str, severity: str) -> ToolResult:
        exp = ChaosExperiment(
            name=f"Chaos-{component}",
            severity=ChaosSeverity(severity),
            target_component=component,
            fault_type="kill_instance",
            duration_seconds=300,
            success_criteria=["availability > 99%"],
            rollback_plan="Auto-restart failed instances",
            risk_score=0.5,
        )
        return ToolResult.ok(data={"experiment": exp.to_dict() if hasattr(exp, 'to_dict') else vars(exp)})

    def get_capabilities(self):
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["python", "py", "javascript", "js", "java", "go", "c", "cpp"],
            categories=["testing", "fuzzing", "chaos", "stress", "property"],
            tools=[t.name for t in self.get_tools()],
            requires_context=True,
            produces_insights=True,
        )

    # ============== Fuzzing Helpers ==============

    def fuzz_input(self, input_schema: Dict[str, Any], count: int = 10) -> List[Dict[str, Any]]:
        """Generate fuzzed inputs based on schema"""
        fuzzed = []
        for _ in range(count):
            inp = {}
            for field, ftype in input_schema.items():
                if ftype == "int":
                    inp[field] = random.choice([0, -1, 2**31-1, -2**31])
                elif ftype == "str":
                    inp[field] = random.choice(["", "a"*1000, "🔥🔥🔥", "\x00"])
                else:
                    inp[field] = None
            fuzzed.append(inp)
        return fuzzed


# ============== Compatibility ==============

async def run_tester(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[str]:
    from core.agent_factory import create_agent
    agent = create_agent("chaos_engineer")
    strategies = await agent.execute(code, language, context)
    # Return list of descriptions (original format expects strings)
    return [s["description"] for s in strategies]
