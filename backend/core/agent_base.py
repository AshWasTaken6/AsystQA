"""
Base Agent - Abstract Foundation for All AsystQA Agents

This module defines the core abstract agent class that all specialized
agents inherit from. It provides:

- Multi-tiered memory integration (working, episodic, procedural)
- Sophisticated decision-making via Strategy pattern
- Tool-calling interface for external capabilities
- Comprehensive telemetry and monitoring
- Event emission for inter-agent coordination
- Graceful error handling and recovery
- State persistence and restoration
"""

import abc
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Type
import logging

from core.memory import (
    WorkingMemory,
    EpisodicMemory,
    ProceduralMemory,
    Priority,
    PatternType,
    PatternSuccess,
)
from core.telemetry import TelemetryManager, Span, MetricType
from core.events import Event, EventBus, EventType
from core.tools import Tool, ToolRegistry, ToolResult
from core.strategies import DecisionStrategy, ScoringStrategy

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Agent lifecycle states"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class AgentCapabilities:
    """Declared capabilities of an agent"""
    languages: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    requires_context: bool = False
    produces_insights: bool = False
    supports_streaming: bool = False


@dataclass
class AgentMetrics:
    """Performance metrics for an agent"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    last_execution: Optional[float] = None
    last_error: Optional[str] = None
    error_count_by_type: Dict[str, int] = field(default_factory=dict)


class BaseAgent(abc.ABC):
    """
    Abstract base class for all AsystQA agents.

    Provides a comprehensive framework for building intelligent,
    self-aware agents with memory, learning, and coordination capabilities.

    Subclasses must implement:
    - initialize(): Setup agent resources
    - execute(): Core agent logic
    - get_tools(): Declare available tools
    - get_capabilities(): Declare capabilities
    """

    # Agent metadata (override in subclass)
    AGENT_NAME: str = "base_agent"
    AGENT_VERSION: str = "1.0.0"
    AGENT_CATEGORY: str = "core"
    AGENT_DESCRIPTION: str = "Base agent - not for direct use"

    def __init__(
        self,
        agent_id: Optional[str] = None,
        telemetry: Optional[TelemetryManager] = None,
        event_bus: Optional[EventBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        """
        Initialize base agent.

        Args:
            agent_id: Unique identifier (default: generated)
            telemetry: Shared telemetry manager
            event_bus: Shared event bus for inter-agent communication
            tool_registry: Shared tool registry
        """
        # Identity
        self.agent_id = agent_id or f"{self.AGENT_NAME}-{str(uuid.uuid4())[:8]}"
        self.name = self.AGENT_NAME
        self.version = self.AGENT_VERSION
        self.category = self.AGENT_CATEGORY

        # Lifecycle
        self.state = AgentState.INITIALIZING
        self.initialized = False

        # Shared infrastructure
        self.telemetry = telemetry or TelemetryManager()
        self.event_bus = event_bus or EventBus()
        self.tool_registry = tool_registry or ToolRegistry()

        # Agent-specific memory spaces (namespaced)
        self.memory = WorkingMemory(
            primary_capacity=100,
            observations_capacity=50,
            actions_capacity=30,
            results_capacity=30,
            long_term_capacity=200,
        )
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()

        # Metrics
        self.metrics = AgentMetrics()
        self._session_id: Optional[str] = None
        self._current_span: Optional[Span] = None

        # Context
        self.context: Dict[str, Any] = {}

    def initialize(self) -> None:
        """
        Initialize agent resources. Override in subclass.
        Called once during agent startup.
        """
        try:
            # Register tools
            self._register_tools()

            # Subscribe to relevant events
            self._subscribe_to_events()

            # Initial state
            self.state = AgentState.READY
            self.initialized = True

            logger.info(f"Agent {self.agent_id} initialized successfully")

        except Exception as e:
            self.state = AgentState.ERROR
            logger.error(f"Agent {self.agent_id} initialization failed: {e}")
            raise

    def _register_tools(self) -> None:
        """Register agent's tools with the registry"""
        for tool in self.get_tools():
            self.tool_registry.register(tool, owner=self.agent_id)

    def _subscribe_to_events(self) -> None:
        """Subscribe to relevant events on the bus.
        Override in subclass to listen to events."""
        pass

    def _handle_pipeline_event(self, event: Event) -> None:
        """Handle pipeline-related events"""
        # Override in subclass for custom event handling
        pass

    @abc.abstractmethod
    def execute(
        self,
        code: str,
        language: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Execute agent's primary analysis logic.

        Args:
            code: Source code to analyze
            language: Programming language
            context: Additional context from other agents
            **kwargs: Agent-specific parameters

        Returns:
            List of findings/recommendations (dict format)
        """
        pass

    @abc.abstractmethod
    def get_tools(self) -> List[Tool]:
        """Declare tools this agent can use"""
        pass

    @abc.abstractmethod
    def get_capabilities(self) -> AgentCapabilities:
        """Declare agent capabilities"""
        pass

    def start_session(self, session_id: str) -> None:
        """Start a new agent session"""
        self._session_id = session_id
        self.context = {"session_id": session_id}
        self.telemetry.start_session(self.agent_id, session_id)

    def end_session(self) -> Dict[str, Any]:
        """End current session and return metrics"""
        metrics = self.get_metrics()
        self.telemetry.end_session(self.agent_id)
        self._session_id = None
        return metrics

    def _run_with_tracing(
        self,
        func: Callable,
        *args,
        operation_name: Optional[str] = None,
        **kwargs
    ):
        """Execute function with telemetry tracing"""
        span_name = operation_name or f"{self.name}.execute"
        with self.telemetry.trace_span(self.agent_id, span_name) as span:
            try:
                self.state = AgentState.RUNNING
                start_time = time.perf_counter()

                result = func(*args, **kwargs)

                duration = time.perf_counter() - start_time
                self._record_success(duration)

                if span:
                    span.set_attribute("success", True)
                    span.set_attribute("duration", duration)

                return result

            except Exception as e:
                duration = time.perf_counter() - start_time if 'start_time' in locals() else 0
                self._record_failure(e, duration)

                if span:
                    span.set_attribute("success", False)
                    span.set_attribute("error", str(e))
                    span.set_attribute("error_type", type(e).__name__)

                logger.error(f"Agent {self.agent_id} execution failed: {e}", exc_info=True)
                raise

    def _record_success(self, duration: float) -> None:
        """Record successful execution"""
        self.metrics.total_executions += 1
        self.metrics.successful_executions += 1
        self.metrics.total_execution_time += duration
        self.metrics.avg_execution_time = (
            self.metrics.total_execution_time / self.metrics.total_executions
        )
        self.metrics.last_execution = time.time()
        self.state = AgentState.READY

        # Record in episodic memory
        self.episodic.remember(
            content=f"Successful execution of {self.name}",
            metadata={
                "agent": self.agent_id,
                "duration": duration,
                "timestamp": time.time(),
            },
            importance=0.6,
            source_agent=self.agent_id,
        )

    def _record_failure(self, error: Exception, duration: float) -> None:
        """Record failed execution"""
        self.metrics.total_executions += 1
        self.metrics.failed_executions += 1
        self.metrics.last_execution = time.time()
        self.metrics.last_error = str(error)
        error_type = type(error).__name__
        self.metrics.error_count_by_type[error_type] = (
            self.metrics.error_count_by_type.get(error_type, 0) + 1
        )
        self.state = AgentState.ERROR

        # Record failure in episodic memory
        self.episodic.remember(
            content=f"Failed execution of {self.name}: {error}",
            metadata={
                "agent": self.agent_id,
                "error": str(error),
                "error_type": error_type,
                "duration": duration,
                "timestamp": time.time(),
            },
            importance=0.3,  # Failures less important but still useful
            source_agent=self.agent_id,
        )

        # Emit error event
        self.event_bus.emit(Event(
            type=EventType.AGENT_ERROR,
            source=self.agent_id,
            data={"error": str(error), "error_type": error_type}
        ))

    def use_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Call a tool by name.

        Args:
            tool_name: Name of registered tool
            **kwargs: Tool parameters

        Returns:
            ToolResult with result or error
        """
        tool = self.tool_registry.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Tool {tool_name} not found")

        if not tool.can_execute(self.context):
            return ToolResult(success=False, error="Tool not available in current context")

        # Record tool use in working memory
        self.memory.add(
            content=f"Used tool {tool_name} with args {kwargs}",
            context_type="actions",
            priority=Priority.LOW,
            agent_id=self.agent_id,
            tags={"tool_use", tool_name},
        )

        # Execute with telemetry
        with self.telemetry.trace_span(self.agent_id, f"tool.{tool_name}") as span:
            try:
                result = tool.execute(self.context, **kwargs)
                if span:
                    span.set_attribute("tool_success", result.success)
                return result
            except Exception as e:
                if span:
                    span.set_attribute("tool_error", str(e))
                return ToolResult(success=False, error=str(e))

    def remember_episode(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5,
    ) -> str:
        """
        Store an episodic memory.

        Args:
            content: Memory text
            metadata: Structured data
            importance: 0-1 importance score

        Returns:
            Memory ID
        """
        return self.episodic.remember(
            content=content,
            metadata=metadata,
            importance=importance,
            source_agent=self.agent_id,
        )

    def recall_episodes(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Recall relevant past episodes.

        Args:
            query: Natural language query
            limit: Max results
            min_similarity: Min similarity threshold

        Returns:
            List of memory entries with scores
        """
        results = self.episodic.recall(
            query=query,
            limit=limit,
            min_similarity=min_similarity,
        )
        return [
            {
                "id": r.entry.id,
                "content": r.entry.content,
                "score": r.score,
                "metadata": r.entry.metadata,
            }
            for r in results
        ]

    def apply_pattern(self, pattern_type: PatternType, context: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        Apply a learned procedural pattern to current context.

        Args:
            pattern_type: Type of pattern to apply
            context: Current context

        Returns:
            Suggested actions if pattern matches, else None
        """
        patterns = self.procedural.retrieve_pattern(
            context=context,
            pattern_type=pattern_type,
            min_effectiveness=0.4,
            limit=3,
        )

        if not patterns:
            return None

        # Use best matching pattern
        best_pattern, confidence = patterns[0]

        # Generate actions from pattern
        actions = best_pattern.generate_actions(context)

        # Record pattern application
        self.procedural.record_trace(
            pattern_id=best_pattern.id,
            context_features=context,
            actions=actions,
            outcome=PatternSuccess.UNKNOWN,  # Outcome will be recorded later
        )

        return actions

    def think(self, thought: str, priority: Priority = Priority.MEDIUM) -> None:
        """
        Record an internal thought in working memory.

        Args:
            thought: Thought text
            priority: Memory priority
        """
        self.memory.add(
            content=thought,
            context_type="primary",
            priority=priority,
            agent_id=self.agent_id,
            tags={"thought"},
        )

    def observe(self, observation: Any, tags: Optional[set[str]] = None) -> str:
        """
        Record an observation.

        Args:
            observation: Observed fact
            tags: Optional categorization tags

        Returns:
            Observation ID
        """
        return self.memory.add(
            content=observation,
            context_type="observations",
            priority=Priority.MEDIUM,
            agent_id=self.agent_id,
            tags=tags or set(),
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive agent metrics"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "executions": self.metrics.total_executions,
            "success_rate": (
                self.metrics.successful_executions / max(1, self.metrics.total_executions)
            ),
            "avg_duration": self.metrics.avg_execution_time,
            "last_execution": self.metrics.last_execution,
            "memory": self.memory.stats(),
            "episodic": self.episodic.stats(),
            "procedural": self.procedural.analyze_pattern_performance(),
        }

    def save_state(self) -> Dict[str, Any]:
        """Save agent state for persistence"""
        return {
            "agent_id": self.agent_id,
            "state": self.state.value,
            "context": self.context,
            "metrics": {
                "total_executions": self.metrics.total_executions,
                "successful_executions": self.metrics.successful_executions,
                "failed_executions": self.metrics.failed_executions,
                "total_execution_time": self.metrics.total_execution_time,
            },
            "memory": self.memory.to_dict(),
            "episodic_count": self.episodic.backend.count(),
            "procedural": self.procedural.export(),
        }

    def load_state(self, state_data: Dict[str, Any]) -> None:
        """Restore agent state from saved data"""
        self.state = AgentState(state_data["state"])
        self.context = state_data.get("context", {})
        # Restore memory (simplified - full restoration would be more complex)
        if "memory" in state_data:
            # Would need proper deserialization
            pass

    def is_healthy(self) -> bool:
        """Check if agent is in healthy state"""
        return self.state in (AgentState.READY, AgentState.RUNNING)

    def shutdown(self) -> None:
        """Gracefully shutdown agent"""
        self.state = AgentState.SHUTDOWN
        logger.info(f"Agent {self.agent_id} shutdown complete")

    # --- Abstract methods that subclasses should override ---

    def validate_input(self, code: str, language: str) -> bool:
        """Validate input before execution"""
        return bool(code.strip()) and bool(language.strip())

    def pre_process(self, code: str, language: str, context: Dict[str, Any]) -> Any:
        """Pre-process input before main execution"""
        return {"code": code, "language": language, "context": context}

    def post_process(self, raw_result: Any) -> List[Dict[str, Any]]:
        """Post-process raw results into standard finding format"""
        return raw_result if isinstance(raw_result, list) else [raw_result]


# ============== Agent Factory Registration Helpers ==============

_AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {}


def register_agent(cls: Type[BaseAgent]) -> Type[BaseAgent]:
    """
    Decorator to register agent class in global registry.

    Usage:
        @register_agent
        class MyAgent(BaseAgent):
            ...
    """
    _AGENT_REGISTRY[cls.AGENT_NAME] = cls
    return cls


def get_agent_class(name: str) -> Optional[Type[BaseAgent]]:
    """Get agent class by name"""
    return _AGENT_REGISTRY.get(name)


def list_agent_classes() -> List[str]:
    """List all registered agent names"""
    return list(_AGENT_REGISTRY.keys())
