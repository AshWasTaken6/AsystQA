"""
Procedural Memory - Learned Task Patterns and Execution Strategies

Stores patterns of how tasks were successfully completed,
including:
- Code analysis techniques that found bugs
- Security detection patterns that were effective
- Decision pathways that led to correct conclusions
- Action sequences that produced good outcomes

Uses reinforcement learning-inspired storage where successful
patterns get reinforced over time.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, TypedDict
from collections import defaultdict
import numpy as np


class PatternType(Enum):
    """Types of procedural patterns"""
    CODE_ANALYSIS = "code_analysis"          # How to analyze code
    ISSUE_DETECTION = "issue_detection"       # How to find specific issues
    DECISION_MAKING = "decision_making"       # Decision strategies
    ACTION_SEQUENCE = "action_sequence"       # Ordered action steps
    CONTEXT_RECOGNITION = "context_recog"     # Situation identification
    RECOVERY_STRATEGY = "recovery"            # How to recover from failures


class PatternSuccess(Enum):
    """Outcome of pattern execution"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    UNKNOWN = "unknown"


@dataclass
class ExecutionTrace:
    """
    A single execution of a pattern with outcome.

    Used for learning which patterns work well in which contexts.
    """
    trace_id: str
    pattern_id: str
    context_features: dict[str, Any]      # Context when pattern was used
    actions_taken: list[dict[str, Any]]   # Specific actions performed
    outcome: PatternSuccess               # Result
    outcome_details: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    reward: float = 0.0                   # RL-style reward signal


@dataclass
class TaskPattern:
    """
    A learned procedural pattern for accomplishing a task.

    Patterns are generalized from successful executions and
    can be matched against current context to suggest actions.
    """
    id: str
    name: str
    pattern_type: PatternType
    description: str

    # Pattern definition
    trigger_conditions: dict[str, Any]     # When to apply this pattern
    action_template: dict[str, Any]        # What actions to take
    expected_outcome: str                  # What should happen

    # Learning statistics
    execution_count: int = 0
    success_count: int = 0
    last_used: float = field(default_factory=time.time)
    effectiveness_score: float = 0.5       # 0-1 success rate

    # Context features
    applicable_languages: set[str] = field(default_factory=set)
    applicable_domains: set[str] = field(default_factory=set)  # security, performance, etc.

    # Pattern refinement
    variant_of: Optional[str] = None       # Parent pattern ID
    refinements: list[str] = field(default_factory=list)  # Child pattern IDs

    def record_execution(self, outcome: PatternSuccess, reward: float = 0.0) -> None:
        """Record result of executing this pattern"""
        self.execution_count += 1
        if outcome == PatternSuccess.SUCCESS:
            self.success_count += 1
        self.last_used = time.time()

        # Update effectiveness using exponential moving average
        success_rate = self.success_count / max(1, self.execution_count)
        alpha = 0.1  # Learning rate
        self.effectiveness_score = (1 - alpha) * self.effectiveness_score + alpha * success_rate

    def matches_context(self, context: dict[str, Any]) -> float:
        """
        Determine how well this pattern matches current context.

        Returns:
            Match confidence between 0 and 1
        """
        if not self.trigger_conditions:
            return 0.5  # Neutral if no conditions

        matches = 0
        total = 0

        for key, expected_value in self.trigger_conditions.items():
            if key not in context:
                continue
            actual_value = context[key]

            # Different matching strategies based on value type
            if isinstance(expected_value, str) and isinstance(actual_value, str):
                # Substring or exact match
                if expected_value.lower() in actual_value.lower():
                    matches += 1
            elif isinstance(expected_value, (list, set, tuple)):
                # Membership check
                if actual_value in expected_value:
                    matches += 1
            elif isinstance(expected_value, dict):
                # Recursive nested check
                sub_score = 0
                sub_total = 0
                for k, v in expected_value.items():
                    if k in actual_value and actual_value[k] == v:
                        sub_score += 1
                    sub_total += 1
                if sub_total > 0:
                    matches += sub_score / sub_total
                    total += 1
            else:
                # Direct equality
                if actual_value == expected_value:
                    matches += 1

            total += 1

        return matches / max(1, total)

    def generate_actions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate concrete actions from this pattern's template given context.

        Allows pattern customization based on current situation.
        """
        # Basic template substitution
        actions = []
        template = self.action_template

        if isinstance(template, list):
            for action_def in template:
                # Substitute variables from context
                action = self._substitute_variables(action_def, context)
                actions.append(action)
        elif isinstance(template, dict):
            actions.append(self._substitute_variables(template, context))

        return actions

    def _substitute_variables(self, template: Any, context: dict[str, Any]) -> Any:
        """Recursively substitute {{variable}} placeholders with context values"""
        if isinstance(template, str):
            import re
            def replace_var(match):
                var_name = match.group(1)
                return str(context.get(var_name, match.group(0)))
            return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
        elif isinstance(template, dict):
            return {
                k: self._substitute_variables(v, context)
                for k, v in template.items()
            }
        elif isinstance(template, list):
            return [self._substitute_variables(item, context) for item in template]
        else:
            return template

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "trigger_conditions": self.trigger_conditions,
            "action_template": self.action_template,
            "expected_outcome": self.expected_outcome,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "last_used": self.last_used,
            "effectiveness_score": self.effectiveness_score,
            "applicable_languages": list(self.applicable_languages),
            "applicable_domains": list(self.applicable_domains),
            "variant_of": self.variant_of,
            "refinements": self.refinements,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskPattern":
        """Deserialize from dictionary"""
        data["pattern_type"] = PatternType(data["pattern_type"])
        data["applicable_languages"] = set(data.get("applicable_languages", []))
        data["applicable_domains"] = set(data.get("applicable_domains", []))
        return cls(**data)


class ProceduralMemory:
    """
    Storage and retrieval of learned task patterns.

    Supports:
    - Pattern storage by type and applicability
    - Context-based pattern matching
    - Learning from execution outcomes
    - Pattern generalization and specialization
    - Reinforcement-based scoring
    """

    def __init__(self):
        self._patterns: dict[str, TaskPattern] = {}  # id -> pattern
        self._by_type: dict[PatternType, set[str]] = defaultdict(set)
        self._by_language: dict[str, set[str]] = defaultdict(set)
        self._by_domain: dict[str, set[str]] = defaultdict(set)
        self._execution_traces: dict[str, ExecutionTrace] = {}  # trace_id -> trace

        # Pre-load base patterns for QA agents
        self._initialize_base_patterns()

    def _initialize_base_patterns(self) -> None:
        """Initialize with foundational QA patterns"""
        patterns = [
            TaskPattern(
                id="pat-basic-scan",
                name="Basic Code Scan",
                pattern_type=PatternType.CODE_ANALYSIS,
                description="Standard comprehensive code analysis",
                trigger_conditions={"task_type": "code_review"},
                action_template=[
                    {"agent": "sentinel", "action": "analyze_execution"},
                    {"agent": "critic", "action": "formal_review"},
                    {"agent": "auditor", "action": "security_scan"},
                ],
                expected_outcome="Complete set of findings across all lanes",
                applicable_languages={"python", "javascript", "typescript", "java"},
                applicable_domains={"general", "security", "quality"},
            ),
            TaskPattern(
                id="pat-security-focus",
                name="Security-First Analysis",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Prioritize security vulnerability detection",
                trigger_conditions={"priority": "security", "domain": "security"},
                action_template=[
                    {"agent": "auditor", "focus": "owasp_top_10"},
                    {"agent": "sentinel", "check": "injection_risks"},
                    {"agent": "critic", "review": "access_control"},
                ],
                expected_outcome="Security issues identified and prioritized",
                applicable_domains={"security", "compliance"},
            ),
            TaskPattern(
                id="pat-performance",
                name="Performance Analysis",
                pattern_type=PatternType.ISSUE_DETECTION,
                description="Detect performance and scalability issues",
                trigger_conditions={"domain": "performance"},
                action_template=[
                    {"agent": "sentinel", "analyze": "complexity"},
                    {"agent": "critic", "check": "algorithm_efficiency"},
                    {"agent": "chaos", "stress": True},
                ],
                expected_outcome="Performance bottlenecks identified",
                applicable_domains={"performance", "scalability"},
            ),
        ]

        for pattern in patterns:
            self.store_pattern(pattern)

    def store_pattern(self, pattern: TaskPattern) -> str:
        """Store a new pattern"""
        self._patterns[pattern.id] = pattern
        self._by_type[pattern.pattern_type].add(pattern.id)
        for lang in pattern.applicable_languages:
            self._by_language[lang].add(pattern.id)
        for domain in pattern.applicable_domains:
            self._by_domain[domain].add(pattern.id)
        return pattern.id

    def retrieve_pattern(
        self,
        context: dict[str, Any],
        pattern_type: Optional[PatternType] = None,
        min_effectiveness: float = 0.3,
        limit: int = 5,
    ) -> list[tuple[TaskPattern, float]]:
        """
        Retrieve patterns matching current context.

        Args:
            context: Current situation context
            pattern_type: Optional filter by type
            min_effectiveness: Minimum effectiveness score
            limit: Max results

        Returns:
            List of (pattern, confidence) tuples, sorted by relevance
        """
        candidates = set()

        if pattern_type:
            candidates = self._by_type.get(pattern_type, set()).copy()
        else:
            # Union of all patterns
            candidates = set(self._patterns.keys())

        # Filter by language if specified
        if "language" in context:
            lang_patterns = self._by_language.get(context["language"], set())
            candidates = candidates & lang_patterns if candidates else lang_patterns

        # Filter by domain if specified
        if "domain" in context:
            domain_patterns = self._by_domain.get(context["domain"], set())
            candidates = candidates & domain_patterns if candidates else domain_patterns

        # Score and filter
        scored = []
        for pid in candidates:
            pattern = self._patterns[pid]

            # Check effectiveness threshold
            if pattern.effectiveness_score < min_effectiveness:
                continue

            # Calculate context match
            match_score = pattern.matches_context(context)

            # Combined score: 0.6 * match + 0.4 * effectiveness
            combined_score = 0.6 * match_score + 0.4 * pattern.effectiveness_score

            if combined_score >= min_effectiveness:
                scored.append((pattern, combined_score))

        # Sort by combined score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:limit]

    def record_trace(
        self,
        pattern_id: str,
        context_features: dict[str, Any],
        actions: list[dict[str, Any]],
        outcome: PatternSuccess,
        outcome_details: Optional[str] = None,
        reward: float = 0.0,
    ) -> str:
        """
        Record execution of a pattern for learning.

        Args:
            pattern_id: Which pattern was executed
            context_features: Context at time of execution
            actions: Actual actions taken
            outcome: Result of execution
            outcome_details: Optional descriptive text
            reward: Numeric reward for RL-style learning

        Returns:
            Trace ID
        """
        trace_id = str(uuid.uuid4())
        trace = ExecutionTrace(
            trace_id=trace_id,
            pattern_id=pattern_id,
            context_features=context_features,
            actions_taken=actions,
            outcome=outcome,
            outcome_details=outcome_details,
            reward=reward,
        )
        self._execution_traces[trace_id] = trace

        # Update pattern statistics
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            pattern.record_execution(outcome, reward)

        return trace_id

    def create_variant(
        self,
        parent_pattern_id: str,
        modifications: dict[str, Any],
        name_suffix: str = "variant"
    ) -> Optional[str]:
        """
        Create a new pattern as a variant of an existing one.

        Used for pattern specialization.
        """
        parent = self._patterns.get(parent_pattern_id)
        if not parent:
            return None

        variant_id = f"{parent_pattern_id}-{name_suffix}"
        variant_data = parent.to_dict()
        variant_data.update(modifications)
        variant_data["id"] = variant_id
        variant_data["variant_of"] = parent_pattern_id

        variant = TaskPattern.from_dict(variant_data)
        variant.refinements = []  # Will be set below

        # Link to parent
        parent.refinements.append(variant_id)

        return self.store_pattern(variant)

    def get_traces_for_pattern(
        self,
        pattern_id: str,
        outcome: Optional[PatternSuccess] = None,
        limit: int = 50
    ) -> list[ExecutionTrace]:
        """Get execution traces for a specific pattern"""
        traces = [
            t for t in self._execution_traces.values()
            if t.pattern_id == pattern_id
        ]
        if outcome:
            traces = [t for t in traces if t.outcome == outcome]
        traces.sort(key=lambda t: t.timestamp, reverse=True)
        return traces[:limit]

    def analyze_pattern_performance(self) -> dict[str, Any]:
        """Analyze all patterns for performance metrics"""
        stats = {
            "total_patterns": len(self._patterns),
            "by_type": {},
            "top_performers": [],
            "needs_improvement": [],
            "recently_used": [],
        }

        # By type
        for ptype in PatternType:
            ptype_patterns = self._by_type.get(ptype, set())
            count = len(ptype_patterns)
            if count > 0:
                avg_eff = np.mean([
                    self._patterns[pid].effectiveness_score
                    for pid in ptype_patterns
                ])
                stats["by_type"][ptype.value] = {
                    "count": count,
                    "avg_effectiveness": float(avg_eff)
                }

        # Top performers and needs improvement
        all_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p.effectiveness_score,
            reverse=True
        )

        stats["top_performers"] = [
            {
                "id": p.id,
                "name": p.name,
                "effectiveness": p.effectiveness_score,
                "executions": p.execution_count,
            }
            for p in all_patterns[:10]
        ]

        stats["needs_improvement"] = [
            {
                "id": p.id,
                "name": p.name,
                "effectiveness": p.effectiveness_score,
                "executions": p.execution_count,
            }
            for p in all_patterns
            if p.execution_count >= 5 and p.effectiveness_score < 0.5
        ]

        # Recently used
        recent = sorted(
            self._patterns.values(),
            key=lambda p: p.last_used,
            reverse=True
        )[:10]
        stats["recently_used"] = [
            {"id": p.id, "name": p.name, "last_used": p.last_used}
            for p in recent
        ]

        return stats

    def export(self) -> dict:
        """Export all patterns and traces"""
        return {
            "patterns": [p.to_dict() for p in self._patterns.values()],
            "traces": [
                {
                    "trace_id": t.trace_id,
                    "pattern_id": t.pattern_id,
                    "outcome": t.outcome.value,
                    "reward": t.reward,
                    "timestamp": t.timestamp,
                }
                for t in self._execution_traces.values()
            ],
        }

    def import_from(self, data: dict) -> tuple[int, int]:
        """Import patterns and traces from export"""
        pattern_count = 0
        trace_count = 0

        # Patterns
        for pdata in data.get("patterns", []):
            try:
                pattern = TaskPattern.from_dict(pdata)
                self.store_pattern(pattern)
                pattern_count += 1
            except Exception as e:
                print(f"Failed to import pattern: {e}")

        # Traces (basic, without full context/actions to avoid bloat)
        for tdata in data.get("traces", []):
            try:
                trace = ExecutionTrace(
                    trace_id=tdata["trace_id"],
                    pattern_id=tdata["pattern_id"],
                    context_features={},
                    actions=[],
                    outcome=PatternSuccess(tdata["outcome"]),
                    reward=tdata.get("reward", 0.0),
                    timestamp=tdata.get("timestamp", time.time()),
                )
                self._execution_traces[trace.trace_id] = trace
                trace_count += 1
            except Exception as e:
                print(f"Failed to import trace: {e}")

        return pattern_count, trace_count

    def clear(self) -> None:
        """Clear all patterns and traces"""
        self._patterns.clear()
        self._by_type.clear()
        self._by_language.clear()
        self._by_domain.clear()
        self._execution_traces.clear()
        self._initialize_base_patterns()
