"""
Agent Factory - Centralized Creation and Lifecycle Management

Provides a single point for instantiating agents with shared dependencies
like telemetry, event bus, tool registry, and memory.

Also handles agent configuration, dependency injection, and warm pooling.
"""

import logging
import uuid
from typing import Any, Dict, Optional, Type
from core.agent_base import (
    BaseAgent,
    register_agent,
    get_agent_class,
    list_agent_classes,
)
from core.telemetry import TelemetryManager, get_telemetry_manager
from core.events import EventBus, get_event_bus
from core.tools import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)


class AgentFactory:
    """
    Factory for creating agent instances with shared infrastructure.

    Ensures all agents share the same:
    - Telemetry manager (for unified metrics)
    - Event bus (for inter-agent communication)
    - Tool registry (for tool discovery)
    """

    def __init__(
        self,
        telemetry: Optional[TelemetryManager] = None,
        event_bus: Optional[EventBus] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.telemetry = telemetry or get_telemetry_manager()
        self.event_bus = event_bus or get_event_bus()
        self.tool_registry = tool_registry or get_tool_registry()
        self._agent_instances: Dict[str, BaseAgent] = {}
        self._warm_pool: list[BaseAgent] = []

        # Ensure all agents are registered by importing modules
        self._import_agent_modules()

        logger.info("AgentFactory initialized")

    def _import_agent_modules(self) -> None:
        """Import all agent modules to trigger @register_agent decorators"""
        try:
            import agents.sentinel
            import agents.critic
            import agents.security
            import agents.planner
            import agents.tester
            import agents.reporter
        except ImportError as e:
            logger.warning(f"Could not import all agent modules: {e}")

    def create(
        self,
        agent_name: str,
        agent_id: Optional[str] = None,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            agent_name: Name of agent (must be registered via @register_agent)
            agent_id: Explicit ID (generated if None)
            **kwargs: Additional parameters for agent constructor

        Returns:
            Configured agent instance

        Raises:
            ValueError: If agent name not registered
        """
        agent_cls = get_agent_class(agent_name)
        if not agent_cls:
            raise ValueError(
                f"Agent '{agent_name}' not found. "
                f"Available: {list_agent_classes()}"
            )

        agent_id = agent_id or f"{agent_name}-{str(uuid.uuid4())[:8]}"

        # Create with shared infrastructure
        agent = agent_cls(
            agent_id=agent_id,
            telemetry=self.telemetry,
            event_bus=self.event_bus,
            tool_registry=self.tool_registry,
            **kwargs
        )

        # Initialize
        agent.initialize()

        # Store reference
        self._agent_instances[agent_id] = agent

        logger.info(f"Created agent: {agent_name} (id={agent_id})")
        return agent

    def create_all(
        self,
        agent_names: Optional[list[str]] = None,
        **kwargs
    ) -> Dict[str, BaseAgent]:
        """
        Create multiple agents at once.

        Args:
            agent_names: List of agent names (all registered if None)
            **kwargs: Passed to each agent constructor

        Returns:
            Dict mapping agent_id -> agent instance
        """
        if agent_names is None:
            agent_names = list_agent_classes()

        agents = {}
        for name in agent_names:
            try:
                agent = self.create(name, **kwargs)
                agents[agent.agent_id] = agent
            except Exception as e:
                logger.error(f"Failed to create agent '{name}': {e}")
                continue

        return agents

    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self._agent_instances.get(agent_id)

    def list_agents(self) -> Dict[str, BaseAgent]:
        """Get all active agent instances"""
        return self._agent_instances.copy()

    def destroy(self, agent_id: str) -> bool:
        """Destroy an agent instance"""
        agent = self._agent_instances.pop(agent_id, None)
        if agent:
            agent.shutdown()
            logger.info(f"Destroyed agent: {agent_id}")
            return True
        return False

    def shutdown_all(self) -> None:
        """Shutdown all agents"""
        for agent in self._agent_instances.values():
            agent.shutdown()
        self._agent_instances.clear()
        logger.info("All agents shut down")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all managed agents"""
        return {
            "managed_agents": len(self._agent_instances),
            "agents": {
                aid: agent.get_metrics()
                for aid, agent in self._agent_instances.items()
            },
        }


# Global factory instance
_global_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    """Get global agent factory"""
    global _global_factory
    if _global_factory is None:
        _global_factory = AgentFactory()
    return _global_factory


def create_agent(agent_name: str, **kwargs) -> BaseAgent:
    """Convenience: create agent using global factory"""
    factory = get_agent_factory()
    return factory.create(agent_name, **kwargs)
