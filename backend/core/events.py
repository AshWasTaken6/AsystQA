"""
Event Bus - Observer Pattern for Inter-Agent Communication

Provides asynchronous event-based communication between agents.
Agents can subscribe to events and react to changes in the system.

Features:
- Event types and filtering
- Async subscription handling
- Event history for debugging
- Correlation across agents
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """System event types"""
    # Pipeline events
    PIPELINE_START = "pipeline.start"
    PIPELINE_COMPLETE = "pipeline.complete"
    PIPELINE_ERROR = "pipeline.error"

    # Agent lifecycle
    AGENT_START = "agent.start"
    AGENT_COMPLETE = "agent.complete"
    AGENT_ERROR = "agent.error"
    AGENT_TIMEOUT = "agent.timeout"

    # Finding events
    FINDING_DETECTED = "finding.detected"
    FINDING_AGGREGATED = "finding.aggregated"
    FINDING_ESCALATED = "finding.escalated"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_RECALLED = "memory.recalled"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # Learning events
    PATTERN_LEARNED = "pattern.learned"
    PATTERN_APPLIED = "pattern.applied"
    PATTERN_REINFORCED = "pattern.reinforced"

    # System
    CONFIG_CHANGED = "config.changed"
    HEALTH_CHECK = "health.check"


@dataclass
class Event:
    """
    An event in the system.

    Attributes:
        id: Unique event ID
        type: Event type string
        source: Agent or component that emitted
        timestamp: When event occurred
        correlation_id: Link to related events
        data: Event payload
        tags: Categorization tags
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    type: EventType = EventType.PIPELINE_START
    source: str = "system"
    timestamp: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "timestamp": self.timestamp,
            "correlation_id": self.correlation_id,
            "data": self.data,
            "tags": list(self.tags),
        }


HandlerCallback = Callable[[Event], None]
AsyncHandlerCallback = Callable[[Event], Any]  # Any = coroutine when called


class EventBus:
    """
    Central event bus for inter-agent communication.

    Implements the Observer pattern with support for:
    - Synchronous and asynchronous handlers
    - Event filtering by type
    - Priority-based delivery
    - Event history for debugging
    """

    def __init__(self, max_history: int = 1000):
        """
        Initialize event bus.

        Args:
            max_history: Maximum events to retain in history
        """
        self._subscribers: Dict[EventType, List[HandlerCallback]] = defaultdict(list)
        self._async_subscribers: Dict[EventType, List[AsyncHandlerCallback]] = defaultdict(list)
        self._wildcard_subscribers: List[HandlerCallback] = []
        self._history: List[Event] = []
        self._max_history = max_history
        self._lock = asyncio.Lock()

    def subscribe(
        self,
        event_type: EventType,
        handler: HandlerCallback,
        priority: int = 0,
    ) -> str:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Event type to listen for
            handler: Callback function (sync)
            priority: Handler priority (higher runs first)

        Returns:
            Subscription ID for unsubscribing
        """
        # Insert based on priority (higher first)
        subscription_id = str(uuid.uuid4())[:8]
        handler_entry = (priority, handler, subscription_id)
        self._subscribers[event_type].append(handler_entry)
        self._subscribers[event_type].sort(key=lambda x: x[0], reverse=True)
        logger.debug(f"Subscribed to {event_type.value}: {subscription_id}")
        return subscription_id

    def subscribe_async(
        self,
        event_type: EventType,
        handler: AsyncHandlerCallback,
        priority: int = 0,
    ) -> str:
        """Subscribe to events with async handler"""
        subscription_id = str(uuid.uuid4())[:8]
        handler_entry = (priority, handler, subscription_id)
        self._async_subscribers[event_type].append(handler_entry)
        self._async_subscribers[event_type].sort(key=lambda x: x[0], reverse=True)
        return subscription_id

    def subscribe_all(
        self,
        handler: HandlerCallback,
        exclude_types: Optional[Set[EventType]] = None,
    ) -> str:
        """
        Subscribe to all events (wildcard).

        Args:
            handler: Callback for any event
            exclude_types: Event types to exclude
        """
        subscription_id = str(uuid.uuid4())[:8]
        self._wildcard_subscribers.append((0, handler, subscription_id, exclude_types or set()))
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove subscription by ID"""
        removed = False
        for handlers in [*self._subscribers.values(), *self._async_subscribers.values()]:
            for i, (_, _, sub_id) in enumerate(handlers):
                if sub_id == subscription_id:
                    handlers.pop(i)
                    removed = True
                    break
        # Check wildcards
        for i, (_, _, sub_id, _) in enumerate(self._wildcard_subscribers):
            if sub_id == subscription_id:
                self._wildcard_subscribers.pop(i)
                removed = True
                break
        return removed

    def emit(self, event: Event) -> None:
        """
        Emit an event to all subscribers.

        Synchronous dispatch - handlers execute immediately.
        For async operations, use emit_async.
        """
        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        event_type = event.type

        # Call subscribers for this type
        for priority, handler, sub_id in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error ({sub_id}): {e}", exc_info=True)

        # Call wildcard subscribers
        for priority, handler, sub_id, exclude in self._wildcard_subscribers:
            if event_type not in exclude:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Wildcard handler error ({sub_id}): {e}", exc_info=True)

    async def emit_async(self, event: Event) -> None:
        """
        Emit an event to all subscribers, including async handlers.
        """
        # Store history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        event_type = event.type

        # Sync handlers
        for priority, handler, sub_id in self._subscribers.get(event_type, []):
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error ({sub_id}): {e}")

        # Async handlers
        async_tasks = []
        for priority, handler, sub_id in self._async_subscribers.get(event_type, []):
            async_tasks.append(handler(event))

        if async_tasks:
            await asyncio.gather(*async_tasks, return_exceptions=True)

        # Wildcards
        for priority, handler, sub_id, exclude in self._wildcard_subscribers:
            if event_type not in exclude:
                if asyncio.iscoroutinefunction(handler):
                    async_tasks.append(handler(event))
                else:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(f"Wildcard handler error: {e}")

        # Execute async tasks
        if async_tasks:
            await asyncio.gather(*async_tasks, return_exceptions=True)

    def get_history(
        self,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """
        Get event history, optionally filtered.

        Args:
            event_type: Filter by type
            source: Filter by source agent/component
            limit: Max events to return

        Returns:
            List of events, most recent first
        """
        results = list(reversed(self._history))

        if event_type:
            results = [e for e in results if e.type == event_type]
        if source:
            results = [e for e in results if e.source == source]

        return results[:limit]

    def clear_history(self) -> None:
        """Clear event history"""
        self._history.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        type_counts = defaultdict(int)
        for event in self._history:
            type_counts[event.type.value] += 1

        return {
            "total_events": len(self._history),
            "by_type": dict(type_counts),
            "active_sync_subscribers": sum(len(h) for h in self._subscribers.values()),
            "active_async_subscribers": sum(len(h) for h in self._async_subscribers.values()),
            "wildcard_subscribers": len(self._wildcard_subscribers),
        }


# Global event bus
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get global event bus instance"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def emit_event(
    event_type: EventType,
    source: str,
    data: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
) -> Event:
    """
    Convenience function to emit an event.

    Usage:
        emit_event(EventType.AGENT_START, "sentinel", {"code_length": 100})
    """
    event = Event(
        type=event_type,
        source=source,
        data=data or {},
        correlation_id=correlation_id,
    )
    bus = get_event_bus()
    bus.emit(event)
    return event
