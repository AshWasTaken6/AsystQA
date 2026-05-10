"""
Core package exports.

Exposes all base classes and utilities for agent construction.
"""

from .agent_base import (
    BaseAgent,
    AgentState,
    AgentCapabilities,
    AgentMetrics,
    register_agent,
    get_agent_class,
    list_agent_classes,
)
from .memory import (
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    ContextWindow,
    ContextItem,
    MemoryEntry,
    TaskPattern,
    ExecutionTrace,
    Priority,
    PatternType,
    PatternSuccess,
)
from .tools import (
    Tool,
    SimpleTool,
    ToolResult,
    ToolContext,
    ToolPermission,
    ToolRegistry,
    get_tool_registry,
)
from .telemetry import TelemetryManager, MetricType, Span, get_telemetry_manager
from .events import EventBus, Event, EventType, get_event_bus, emit_event
from .strategies import (
    DecisionStrategy,
    DecisionStrategyType,
    DecisionRule,
    Criterion,
    RuleBasedStrategy,
    ScoringStrategy,
    PatternMatchingStrategy,
    MultiCriteriaDecisionAnalysis,
    ScoringStrategyWrapper,
    relevance_criterion,
    confidence_criterion,
    recency_criterion,
)

__all__ = [
    # Base agent
    "BaseAgent",
    "AgentState",
    "AgentCapabilities",
    "AgentMetrics",
    "register_agent",
    "get_agent_class",
    "list_agent_classes",
    # Memory
    "WorkingMemory",
    "EpisodicMemory",
    "ProceduralMemory",
    "ContextWindow",
    "ContextItem",
    "MemoryEntry",
    "TaskPattern",
    "ExecutionTrace",
    "Priority",
    "PatternType",
    "PatternSuccess",
    # Tools
    "Tool",
    "SimpleTool",
    "ToolResult",
    "ToolContext",
    "ToolPermission",
    "ToolRegistry",
    "get_tool_registry",
    # Telemetry
    "TelemetryManager",
    "MetricType",
    "Span",
    "get_telemetry_manager",
    # Events
    "EventBus",
    "Event",
    "EventType",
    "get_event_bus",
    "emit_event",
    # Strategies
    "DecisionStrategy",
    "DecisionStrategyType",
    "DecisionRule",
    "Criterion",
    "RuleBasedStrategy",
    "ScoringStrategy",
    "PatternMatchingStrategy",
    "MultiCriteriaDecisionAnalysis",
    "ScoringStrategyWrapper",
    "relevance_criterion",
    "confidence_criterion",
    "recency_criterion",
]
