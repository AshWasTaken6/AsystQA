"""
Architect Agent - Strategic Planning & Code Decomposition

Enhanced Architect with sophisticated planning, architectural analysis,
complexity assessment, and strategic guidance.

Specializes in:
- Codebase decomposition and modularity analysis
- Architectural pattern recognition
- Complexity profiling and hotspots
- Dependency and coupling analysis
- Strategic re-planning based on findings
- Architectural debt identification
- Design principle compliance checking

Uses episodic memory to track architectural evolution over time.
"""

import ast
import asyncio
import logging
import time
import uuid
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path

from core.agent_base import BaseAgent, Priority, register_agent
from core.memory import WorkingMemory, EpisodicMemory, ProceduralMemory, PatternType, TaskPattern
from core.telemetry import get_telemetry_manager
from core.events import EventType, emit_event
from core.tools import SimpleTool, ToolContext, ToolResult, ToolPermission
from core.strategies import (
    DecisionStrategy,
    MultiCriteriaDecisionAnalysis,
    Criterion,
)

logger = logging.getLogger(__name__)


class PlanningDepth(Enum):
    """Analysis depth levels"""
    SURFACE = "surface"         # Quick scan, high-level
    STANDARD = "standard"       # Normal analysis
    DEEP = "deep"              # Comprehensive deep analysis
    ARCHITECTURAL = "arch"     # Full system-level analysis


@dataclass
class ArchitecturalComponent:
    """Represents a logical component in the architecture"""
    name: str
    type: str  # module, class, function, microservice
    responsibilities: List[str]
    dependencies: List[str]
    complexity: float  # 0-1
    cohesion: float    # 0-1
    coupling: float    # 0-1 (lower is better)
    lines_of_code: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "responsibilities": self.responsibilities,
            "dependencies": self.dependencies,
            "complexity": self.complexity,
            "cohesion": self.cohesion,
            "coupling": self.coupling,
            "loc": self.lines_of_code,
        }


@dataclass
class ArchitecturePlan:
    """Strategic plan for code analysis and improvement"""
    primary_goal: str
    decomposition: List[Dict[str, Any]]
    complexity_profile: Dict[str, Any]
    target_modularity: float
    priority_areas: List[str]
    contingencies: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.primary_goal,
            "decomposition": self.decomposition,
            "complexity": self.complexity_profile,
            "modularity_target": self.target_modularity,
            "priorities": self.priority_areas,
            "contingencies": self.contingencies,
            "confidence": self.confidence,
        }


@register_agent
class ArchitectAgent(BaseAgent):
    """
    Enhanced Architect agent with strategic planning capabilities.

    Provides high-level strategic analysis including:
    - Architectural decomposition
    - Complexity hotspot identification
    - Modularity assessment
    - Strategic re-planning based on downstream findings
    - Architectural debt tracking
    - Design pattern recognition
    - Technical risk assessment
    """

    AGENT_NAME = "architect"
    AGENT_VERSION = "3.0.0"
    AGENT_CATEGORY = "planning"
    AGENT_DESCRIPTION = "Strategic code analysis, architectural planning, and re-planning"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.memory = WorkingMemory(
            primary_capacity=100,
            observations_capacity=150,
            long_term_capacity=300,
        )

        self._plans: List[ArchitecturePlan] = []
        self._components: Dict[str, ArchitecturalComponent] = {}
        self._complexity_metrics: Dict[str, float] = {}
        self._decision_strategy = self._build_planning_strategy()

        self._load_architectural_patterns()

    def _load_architectural_patterns(self) -> None:
        """Load architectural patterns into procedural memory"""
        patterns = [
            TaskPattern(
                id="arch-layered",
                name="Layered Architecture",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="Separate concerns into layers (presentation, business, data)",
                trigger_conditions={"architecture_style": "layered"},
                action_template=[
                    {"identify": "presentation_layer"},
                    {"identify": "business_logic_layer"},
                    {"identify": "data_access_layer"},
                    {"enforce": "layer_dependencies_downward"},
                ],
                expected_outcome="Clean layer separation with no circular dependencies",
                applicable_domains={"architecture", "modularity"},
            ),
            TaskPattern(
                id="arch-modular",
                name="Modular Design",
                pattern_type=PatternType.ACTION_SEQUENCE,
                description="High module independence and low coupling",
                trigger_conditions={"goal": "modularity"},
                action_template=[
                    {"measure": "coupling"},
                    {"identify": "high_coupling_pairs"},
                    {"suggest": "interface_separation"},
                ],
                expected_outcome="Modules with high cohesion and low coupling",
                applicable_domains={"architecture", "refactoring"},
            ),
        ]

        for pattern in patterns:
            self.procedural.store_pattern(pattern)

    def _build_planning_strategy(self) -> DecisionStrategy:
        """Build strategy for planning depth selection"""
        criteria = [
            Criterion(
                name="code_size",
                weight=0.3,
                scorer=lambda ctx, opts: {
                    "surface": 0.9 if ctx.get("code_length", 0) < 500 else 0.3,
                    "standard": 0.5,
                    "deep": 0.3 if ctx.get("code_length", 0) < 2000 else 0.6,
                }
            ),
            Criterion(
                name="finding_severity",
                weight=0.4,
                scorer=lambda ctx, opts: {
                    "surface": 0.2,
                    "standard": 0.5,
                    "deep": 0.9 if ctx.get("has_critical", False) else 0.6,
                }
            ),
            Criterion(
                name="user_context",
                weight=0.3,
                scorer=lambda ctx, opts: {
                    "surface": 0.3,
                    "standard": 0.7,
                    "deep": 0.9 if ctx.get("detailed", False) else 0.4,
                }
            ),
        ]
        return MultiCriteriaDecisionAnalysis(criteria, method="weighted_sum")

    # ============== Core Execution ==============

    async def execute(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        depth: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute architectural analysis and planning.

        Args:
            code: Source code to analyze
            language: Programming language
            context: Previous agent context
            depth: Explicit depth override

        Returns:
            List of planning steps (strategic recommendations)
        """
        self.state = "RUNNING"
        start_time = time.time()
        context = context or {}

        session_id = context.get("session_id")
        self.start_session(session_id or str(uuid.uuid4()))

        emit_event(
            EventType.PIPELINE_START if not context else EventType.AGENT_START,
            source=self.agent_id,
            data={"language": language, "depth": depth, "replan": bool(context)},
        )

        try:
            with get_telemetry_manager().trace_span(
                self.agent_id, "architect_analysis"
            ) as span:
                if span:
                    span.set_attribute("language", language)
                    span.set_attribute("is_replan", bool(context))

                # Determine planning depth
                if not depth:
                    depth = self._determine_depth(code, language, context)

                # Build plan
                plan = await self._create_plan(code, language, context, depth)

                # Store plan
                self._plans.append(plan)
                self.memory.add(
                    content=f"Plan created: {plan.primary_goal}",
                    context_type="long_term",
                    priority=Priority.HIGH,
                    agent_id=self.agent_id,
                )

                duration = time.time() - start_time
                self._record_success(duration)

                self.remember_episode(
                    content=f"Architecture plan: {plan.primary_goal}",
                    metadata={
                        "agent": self.agent_id,
                        "depth": depth,
                        "loc": len(code.splitlines()),
                        "complexity": plan.complexity_profile.get("big_o", "unknown"),
                        "duration": duration,
                    },
                    importance=0.8,
                )

                emit_event(
                    EventType.AGENT_COMPLETE,
                    source=self.agent_id,
                    data={"plan_steps": len(plan.decomposition)},
                )

                # Return as list of plan items
                return self._plan_to_steps(plan)

        except Exception as e:
            duration = time.time() - start_time
            self._record_failure(e, duration)
            emit_event(EventType.AGENT_ERROR, source=self.agent_id, data={"error": str(e)})
            raise

    async def _create_plan(
        self,
        code: str,
        language: str,
        context: Dict[str, Any],
        depth: str,
    ) -> ArchitecturePlan:
        """Create comprehensive architecture plan"""

        # Profile code
        profile = self._complexity_profile(code, language)
        self._complexity_metrics = profile

        # Decompose structure
        components = self._decompose_code(code, language)
        self._components = {c.name: c for c in components}

        # Identify priority areas based on context
        priority_areas = self._identify_priority_areas(components, context)

        # Build contingencies
        contingencies = self._build_contingencies(profile, context, depth)

        # Set modularity target based on depth
        modularity_targets = {
            "surface": 0.3,
            "standard": 0.5,
            "deep": 0.7,
            "arch": 0.85,
        }
        target_mod = modularity_targets.get(depth, 0.5)

        # Calculate confidence
        base_confidence = 0.8 if components else 0.5
        if context and context.get("sentinel"):
            # Existing findings reduce confidence slightly
            base_confidence -= 0.1

        plan = ArchitecturePlan(
            primary_goal=self._determine_goal(profile, context, depth),
            decomposition=[
                {
                    "component": c.name,
                    "type": c.type,
                    "loc": c.loc,
                    "complexity": round(c.complexity, 2),
                    "coupling": round(c.coupling, 2),
                }
                for c in components[:20]  # Limit for size
            ],
            complexity_profile=profile,
            target_modularity=target_mod,
            priority_areas=priority_areas,
            contingencies=contingencies,
            confidence=base_confidence,
        )

        return plan

    def _determine_depth(
        self,
        code: str,
        language: str,
        context: Dict[str, Any],
    ) -> str:
        """Determine appropriate planning depth"""
        code_len = len(code)
        loc = len(code.splitlines())

        # Check for critical issues
        sentinel = context.get("sentinel", [])
        auditor = context.get("auditor", [])
        has_critical = any(
            f.get("severity") == "CRITICAL"
            for f in sentinel + auditor
        )

        # Use decision strategy
        ctx = {
            "code_length": loc,
            "has_critical": has_critical,
            "detailed": context.get("detailed", False),
        }
        depth, score = self._decision_strategy.decide(
            ctx,
            ["surface", "standard", "deep"]
        )
        return depth

    def _determine_goal(
        self,
        profile: Dict[str, Any],
        context: Dict[str, Any],
        depth: str,
    ) -> str:
        """Determine primary planning goal"""
        if not context:
            return "Initial comprehensive analysis and decomposition"

        # Re-planning goal
        sentinel = context.get("sentinel", [])
        auditor = context.get("auditor", [])
        critic = context.get("critic", [])

        issues = []
        issues.extend([f.get("category", "") for f in sentinel])
        issues.extend([f.get("category", "") for f in auditor])
        issues.extend([f.get("category", "") for f in critic])

        if any("Security" in i for i in issues):
            return "Address security vulnerabilities and harden code"
        if any("Runtime" in i or "Execution" in i for i in issues):
            return "Fix runtime defects and improve error handling"
        if any("Design" in i or "Maintainability" in i for i in issues):
            return "Improve design and reduce complexity"

        return "Optimize based on feedback"

    def _complexity_profile(self, code: str, language: str) -> Dict[str, Any]:
        """Generate detailed complexity profile"""
        lines = code.splitlines()
        non_empty = len([l for l in lines if l.strip()])

        # Cyclomatic approximation
        branches = sum(
            code.count(token) for token in [" if ", "elif ", "for ", "while ", "except ", " and ", " or "]
        )

        # Nesting depth
        max_indent = max((len(line) - len(line.lstrip())) // 4 for line in lines if line.strip()) if lines else 0

        # Big-O estimation
        if language in {"python", "py"}:
            nested_loops = code.count("for ") * code.count("for ")
            big_o = "O(n^2)" if nested_loops > 1 else "O(n log n)" if "sort(" in code else "O(n) or lower"
        else:
            big_o = "O(n) estimated"

        return {
            "lines": non_empty,
            "branches": branches,
            "max_nesting": max_indent,
            "big_o": big_o,
            "total_chars": len(code),
        }

    def _decompose_code(self, code: str, language: str) -> List[ArchitecturalComponent]:
        """Decompose code into architectural components"""
        components = []

        if language.lower() in {"python", "py"}:
            try:
                tree = ast.parse(code)
            except SyntaxError:
                return [ArchitecturalComponent(
                    name="broken_module",
                    type="module",
                    responsibilities=["Invalid syntax"],
                    dependencies=[],
                    complexity=1.0,
                    cohesion=0.0,
                    coupling=0.0,
                    lines_of_code=len(code.splitlines()),
                )]

            # Analyze functions
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    num_statements = sum(1 for _ in ast.walk(node) if isinstance(_, ast.stmt))
                    num_branches = sum(1 for _ in ast.walk(node) if isinstance(_, (ast.If, ast.For, ast.While)))
                    num_args = len(node.args.args)

                    # Estimate complexity (simplified)
                    complexity = min(1.0, (num_statements / 50) + (num_branches / 10) + (num_args / 10))

                    # Find dependencies (calls)
                    calls = set()
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name):
                                calls.add(child.func.id)

                    # Cohesion estimate (how many local variables vs parameters)
                    local_vars = sum(1 for _ in ast.walk(node) if isinstance(_, ast.Name) and isinstance(_.ctx, ast.Store))
                    cohesion = min(1.0, local_vars / max(1, num_args + num_statements))

                    coupling = min(1.0, len(calls) / max(1, num_statements / 5))

                    component = ArchitecturalComponent(
                        name=func_name,
                        type="function",
                        responsibilities=[f"Function: {func_name}"],
                        dependencies=list(calls)[:10],  # Cap
                        complexity=complexity,
                        cohesion=cohesion,
                        coupling=coupling,
                        lines_of_code=num_statements,
                    )
                    components.append(component)

            # Analyze classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    bases = [b.id if isinstance(b, ast.Name) else "complex" for b in node.bases]

                    complexity = min(1.0, len(methods) / 20)

                    component = ArchitecturalComponent(
                        name=class_name,
                        type="class",
                        responsibilities=[f"Class with {len(methods)} methods"],
                        dependencies=bases,
                        complexity=complexity,
                        cohesion=0.7 if methods else 0.5,  # placeholder
                        coupling=0.3 if bases else 0.1,
                        lines_of_code=len(node.body),
                    )
                    components.append(component)

        return components

    def _identify_priority_areas(
        self,
        components: List[ArchitecturalComponent],
        context: Dict[str, Any],
    ) -> List[str]:
        """Identify high-priority areas for attention"""
        priorities = []

        # High complexity functions
        complex_funcs = [c for c in components if c.type == "function" and c.complexity > 0.7]
        if complex_funcs:
            priorities.append(f"Reduce complexity in {len(complex_funcs)} complex functions")

        # High coupling
        high_coupling = [c for c in components if c.coupling > 0.7]
        if high_coupling:
            priorities.append(f"Loosen tight coupling in {len(high_coupling)} components")

        # Context-based priorities
        sentinel = context.get("sentinel", [])
        categories = [f.get("category", "") for f in sentinel]
        if any("Boundary" in c for c in categories):
            priorities.append("Add input validation at trust boundaries")
        if any("Exception" in c for c in categories):
            priorities.append("Improve error handling and recovery")

        return priorities

    def _build_contingencies(
        self,
        profile: Dict[str, Any],
        context: Dict[str, Any],
        depth: str,
    ) -> List[str]:
        """Build contingency plans for various scenarios"""
        contingencies = [
            "Contingency A: block release on any non-compilable, privilege-escalating, or data-loss finding.",
            "Contingency B: when runtime defects exist, prioritize boundary validation before refactors.",
            "Contingency C: when security defects exist, threat-model the affected boundary before local fixes.",
        ]

        if profile.get("branches", 0) > 20:
            contingencies.append("Consider splitting complex functions before adding new features.")

        if depth == "deep":
            contingencies.append("Deep analysis mode: prepare for complete architectural review.")

        return contingencies

    def _plan_to_steps(self, plan: ArchitecturePlan) -> List[Dict[str, Any]]:
        """Convert plan to step format for output"""
        steps = [
            {
                "agent": "Architect",
                "phase": "initial" if not self._plans else "replan",
                "step": f"Goal: {plan.primary_goal}",
            },
            {
                "agent": "Architect",
                "phase": "initial" if not self._plans else "replan",
                "step": f"Complexity: {plan.complexity_profile['lines']} LOC, {plan.complexity_profile['branches']} branches",
            },
            {
                "agent": "Architect",
                "phase": "initial" if not self._plans else "replan",
                "step": f"Modularity target: {plan.target_modularity:.0%}",
            },
        ]

        # Add decomposition
        for comp in plan.decomposition[:5]:
            steps.append({
                "agent": "Architect",
                "phase": "decompose",
                "step": f"Component {comp['name']}: complexity {comp['complexity']}, coupling {comp['coupling']}",
            })

        # Add contingencies
        steps.append({
            "agent": "Architect",
            "phase": "contingency",
            "step": "; ".join(plan.contingencies[:2]),
        })

        return steps

    # ============== Tools ==============

    def get_tools(self) -> List[SimpleTool]:
        return [
            SimpleTool(
                name="assess_modularity",
                func=self._tool_modularity,
                description="Assess code modularity and coupling",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="complexity_hotspots",
                func=self._tool_hotspots,
                description="Identify complexity hotspots",
                permission=ToolPermission.PUBLIC,
            ),
            SimpleTool(
                name="dependency_graph",
                func=self._tool_dependencies,
                description="Generate dependency graph",
                permission=ToolPermission.INTERNAL,
            ),
        ]

    def _tool_modularity(self, context: ToolContext, code: str, language: str) -> ToolResult:
        components = self._decompose_code(code, language)
        avg_coupling = sum(c.coupling for c in components) / len(components) if components else 0
        avg_cohesion = sum(c.cohesion for c in components) / len(components) if components else 0
        return ToolResult.ok(data={
            "modularity_score": 1.0 - avg_coupling,
            "coupling_avg": avg_coupling,
            "cohesion_avg": avg_cohesion,
            "component_count": len(components),
        })

    def _tool_hotspots(self, context: ToolContext, code: str) -> ToolResult:
        components = self._decompose_code(code, "python")
        hotspots = [{"name": c.name, "complexity": c.complexity} for c in components if c.complexity > 0.7]
        return ToolResult.ok(data={"hotspots": hotspots})

    def _tool_dependencies(self, context: ToolContext, code: str, language: str) -> ToolResult:
        # Build dependency graph
        deps = {}
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    calls = set()
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                            calls.add(child.func.id)
                    deps[node.name] = list(calls)
        except Exception:
            pass
        return ToolResult.ok(data={"dependencies": deps})

    def get_capabilities(self):
        from core.agent_base import AgentCapabilities
        return AgentCapabilities(
            languages=["python", "py", "javascript", "js", "typescript", "ts", "java"],
            categories=["planning", "architecture", "complexity", "refactoring"],
            tools=[t.name for t in self.get_tools()],
            requires_context=True,
            produces_insights=True,
        )

    def get_plan_history(self) -> List[Dict[str, Any]]:
        """Get history of all plans created"""
        return [p.to_dict() for p in self._plans]


# ============== Compatibility ==============

async def run_planner(
    code: str,
    language: str,
    context: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    from core.agent_factory import create_agent
    agent = create_agent("architect")
    return await agent.execute(code, language, context)
