"""
Working Memory - Short-Term Contextual Buffers

Implements a sliding window of recent context with priority-based eviction,
attention-weighted retention, and cross-agent context sharing capabilities.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from collections import deque
from heapq import heappush, heappop


class Priority(Enum):
    """Memory priority levels for retention decisions"""
    CRITICAL = 0  # Highest priority - never evict unless absolutely necessary
    HIGH = 1      # Important context, evict last
    MEDIUM = 2    # Normal priority
    LOW = 3       # Can be evicted first
    TEMPORARY = 4 # One-time use, evict immediately after use


@dataclass
class ContextItem:
    """
    A single item in working memory with metadata for management.

    Attributes:
        id: Unique identifier
        content: The actual memory content (any serializable)
        timestamp: Creation time
        priority: Eviction priority
        attention_score: Relevance score (0-1) for attention mechanisms
        access_count: Number of times accessed
        last_accessed: Last access timestamp
        ttl: Time-to-live in seconds (None = unlimited)
        tags: Categorical tags for grouping
        agent_id: Which agent created this item
        linked_items: IDs of related context items
    """
    id: str
    content: Any
    timestamp: float = field(default_factory=time.time)
    priority: Priority = Priority.MEDIUM
    attention_score: float = 0.5
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    tags: set[str] = field(default_factory=set)
    agent_id: Optional[str] = None
    linked_items: list[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if item has exceeded its TTL"""
        if self.ttl is None:
            return False
        return time.time() - self.timestamp > self.ttl

    def touch(self) -> None:
        """Update access metadata"""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp,
            "priority": self.priority.name,
            "attention_score": self.attention_score,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "ttl": self.ttl,
            "tags": list(self.tags),
            "agent_id": self.agent_id,
            "linked_items": self.linked_items,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContextItem":
        """Deserialize from dictionary"""
        data["priority"] = Priority[data["priority"]]
        data["tags"] = set(data.get("tags", []))
        return cls(**data)


class ContextWindow:
    """
    A sliding window of context items with LRU + priority eviction.

    Uses a hybrid eviction strategy:
    1. Expired items (TTL) always evicted first
    2. Lowest priority items evicted next
    3. Within same priority, least recently used (LRU)
    4. Within same LRU, lowest attention score
    """

    def __init__(self, max_size: int = 100):
        """
        Initialize context window.

        Args:
            max_size: Maximum number of items to retain
        """
        self.max_size = max_size
        self._items: dict[str, ContextItem] = {}
        self._eviction_queue: list[tuple] = []  # (priority, timestamp, attention, id)
        self._access_order: deque[str] = deque(maxlen=max_size * 2)

    def add(
        self,
        content: Any,
        priority: Priority = Priority.MEDIUM,
        attention_score: float = 0.5,
        ttl: Optional[float] = None,
        tags: Optional[set[str]] = None,
        agent_id: Optional[str] = None,
        linked_items: Optional[list[str]] = None,
    ) -> str:
        """
        Add item to context window.

        Returns:
            Unique ID of the added item
        """
        item_id = str(uuid.uuid4())
        item = ContextItem(
            id=item_id,
            content=content,
            priority=priority,
            attention_score=attention_score,
            ttl=ttl,
            tags=tags or set(),
            agent_id=agent_id,
            linked_items=linked_items or [],
        )
        self._items[item_id] = item
        self._update_eviction_queue(item)
        self._evict_if_needed()
        return item_id

    def get(self, item_id: str) -> Optional[Any]:
        """Retrieve item content by ID"""
        item = self._items.get(item_id)
        if item:
            item.touch()
            self._access_order.append(item_id)
        return item.content if item else None

    def get_item(self, item_id: str) -> Optional[ContextItem]:
        """Get full ContextItem by ID"""
        item = self._items.get(item_id)
        if item:
            item.touch()
        return item

    def remove(self, item_id: str) -> bool:
        """Remove item from window"""
        if item_id in self._items:
            del self._items[item_id]
            # Rebuild eviction queue (inefficient but safe)
            self._rebuild_eviction_queue()
            return True
        return False

    def clear(self) -> None:
        """Clear all items"""
        self._items.clear()
        self._eviction_queue.clear()
        self._access_order.clear()

    def _update_eviction_queue(self, item: ContextItem) -> None:
        """Update the eviction priority queue"""
        heappush(
            self._eviction_queue,
            (item.priority.value, item.timestamp, -item.attention_score, item.id)
        )

    def _evict_if_needed(self) -> None:
        """Evict items if over capacity"""
        while len(self._items) > self.max_size and self._eviction_queue:
            # Remove invalid entries first
            while self._eviction_queue:
                priority, timestamp, neg_attention, item_id = self._eviction_queue[0]
                if item_id in self._items:
                    break
                heappop(self._eviction_queue)

            if not self._eviction_queue:
                break

            # Check if we need to evict
            if len(self._items) <= self.max_size:
                break

            # Evict the lowest priority item
            priority, timestamp, neg_attention, item_id = heappop(self._eviction_queue)
            if item_id in self._items:
                item = self._items[item_id]

                # Don't evict CRITICAL priority items unless absolutely necessary
                if item.priority == Priority.CRITICAL and len(self._items) > self.max_size * 1.5:
                    # Try to find non-critical to evict
                    temp_queue = []
                    candidate = None
                    while self._eviction_queue:
                        p, ts, na, tid = heappop(self._eviction_queue)
                        if tid in self._items and self._items[tid].priority != Priority.CRITICAL:
                            candidate = (p, ts, na, tid)
                            break
                        temp_queue.append((p, ts, na, tid))

                    # Restore temp queue
                    for entry in temp_queue:
                        heappush(self._eviction_queue, entry)

                    if candidate:
                        # Evict the non-critical candidate
                        _, _, _, evict_id = candidate
                        if evict_id in self._items:
                            del self._items[evict_id]
                            continue

                # If still here, evict this item
                if item_id in self._items:
                    del self._items[item_id]

    def _rebuild_eviction_queue(self) -> None:
        """Rebuild eviction queue from scratch (for cleanup)"""
        self._eviction_queue.clear()
        for item in self._items.values():
            self._update_eviction_queue(item)

    def get_by_tags(self, tags: set[str]) -> list[ContextItem]:
        """Get all items matching any of the given tags"""
        return [
            item for item in self._items.values()
            if item.tags & tags
        ]

    def get_by_agent(self, agent_id: str) -> list[ContextItem]:
        """Get all items from specific agent"""
        return [
            item for item in self._items.values()
            if item.agent_id == agent_id
        ]

    def query(self, **filters) -> list[ContextItem]:
        """
        Query items by arbitrary filters.

        Supported filters:
            agent_id: str
            tags: set[str] (matches any)
            min_priority: Priority
            min_attention: float
            max_access_count: int
        """
        results = []
        for item in self._items.values():
            if "agent_id" in filters and item.agent_id != filters["agent_id"]:
                continue
            if "tags" in filters and not (item.tags & filters["tags"]):
                continue
            if "min_priority" in filters and item.priority.value > filters["min_priority"].value:
                continue
            if "min_attention" in filters and item.attention_score < filters["min_attention"]:
                continue
            if "max_access_count" in filters and item.access_count > filters["max_access_count"]:
                continue
            results.append(item)
        return results

    def update_attention(self, item_id: str, attention_delta: float) -> bool:
        """Update attention score for an item"""
        item = self._items.get(item_id)
        if item:
            item.attention_score = max(0.0, min(1.0, item.attention_score + attention_delta))
            self._rebuild_eviction_queue()
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove all expired items, return count removed"""
        expired_ids = [
            item_id for item_id, item in self._items.items()
            if item.is_expired()
        ]
        for item_id in expired_ids:
            del self._items[item_id]
        if expired_ids:
            self._rebuild_eviction_queue()
        return len(expired_ids)

    def stats(self) -> dict:
        """Get window statistics"""
        priorities = {p: 0 for p in Priority}
        for item in self._items.values():
            priorities[item.priority] += 1

        return {
            "total_items": len(self._items),
            "capacity": self.max_size,
            "utilization": len(self._items) / self.max_size if self.max_size > 0 else 0,
            "priority_distribution": {p.name: count for p, count in priorities.items()},
            "avg_attention": sum(i.attention_score for i in self._items.values()) / len(self._items) if self._items else 0,
            "avg_access_count": sum(i.access_count for i in self._items.values()) / len(self._items) if self._items else 0,
        }

    def snapshot(self) -> dict:
        """Get complete snapshot of all items"""
        return {
            "items": [item.to_dict() for item in self._items.values()],
            "stats": self.stats(),
            "timestamp": time.time(),
        }


class WorkingMemory:
    """
    Multi-context working memory manager for an agent.

    Maintains separate windows for different types of context:
    - primary: Main reasoning context (largest)
    - observations: Facts and observations about the code/task
    - actions: History of actions taken
    - results: Outcomes of actions
    - long_term: Items that have been promoted for long retention
    """

    def __init__(
        self,
        primary_capacity: int = 100,
        observations_capacity: int = 50,
        actions_capacity: int = 30,
        results_capacity: int = 30,
        long_term_capacity: int = 200,
    ):
        self.windows = {
            "primary": ContextWindow(primary_capacity),
            "observations": ContextWindow(observations_capacity),
            "actions": ContextWindow(actions_capacity),
            "results": ContextWindow(results_capacity),
            "long_term": ContextWindow(long_term_capacity),  # Promoted items
        }
        self._cross_links: dict[str, set[str]] = {}  # item_id -> set of linked item IDs

    def add(
        self,
        content: Any,
        context_type: str = "primary",
        **kwargs
    ) -> str:
        """
        Add item to specified context window.

        Args:
            content: Memory content
            context_type: Which window to store in
            **kwargs: Passed to ContextItem constructor

        Returns:
            Item ID
        """
        if context_type not in self.windows:
            raise ValueError(f"Unknown context type: {context_type}")

        item_id = self.windows[context_type].add(content, **kwargs)
        return item_id

    def get(self, item_id: str, context_type: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve item by ID, optionally restricting to specific window.

        If item not in specified window, searches all windows.
        """
        if context_type:
            return self.windows[context_type].get(item_id)

        # Search all windows
        for window in self.windows.values():
            if item_id in window._items:
                return window.get(item_id)
        return None

    def link_items(self, item_id1: str, item_id2: str) -> None:
        """Create bidirectional link between two memory items"""
        self._cross_links.setdefault(item_id1, set()).add(item_id2)
        self._cross_links.setdefault(item_id2, set()).add(item_id1)

    def get_linked(self, item_id: str) -> list[ContextItem]:
        """Get all items linked to given item"""
        linked_ids = self._cross_links.get(item_id, set())
        results = []
        for window in self.windows.values():
            for lid in linked_ids:
                item = window.get_item(lid)
                if item:
                    results.append(item)
        return results

    def query(
        self,
        context_type: Optional[str] = None,
        **filters
    ) -> list[ContextItem]:
        """
        Query across all windows or specific window.

        Args:
            context_type: If provided, only query this window
            **filters: Passed to ContextWindow.query()
        """
        results = []
        windows = [self.windows[context_type]] if context_type else self.windows.values()
        for window in windows:
            results.extend(window.query(**filters))
        return results

    def promote_to_long_term(self, item_id: str) -> bool:
        """
        Promote an item from its current window to long-term memory.

        Long-term items get higher retention priority.
        """
        # Find item in any window
        source_window = None
        item = None
        for window in self.windows.values():
            if item_id in window._items:
                source_window = window
                item = window.get_item(item_id)
                break

        if not item or not source_window:
            return False

        # Remove from source
        source_window.remove(item_id)

        # Add to long-term with CRITICAL priority
        long_term = self.windows["long_term"]
        long_term.add(
            content=item.content,
            priority=Priority.CRITICAL,
            tags=item.tags,
            agent_id=item.agent_id,
        )
        return True

    def cleanup_expired(self) -> dict[str, int]:
        """Clean up expired items across all windows"""
        counts = {}
        for name, window in self.windows.items():
            counts[name] = window.cleanup_expired()
        return counts

    def snapshot(self) -> dict:
        """Get complete working memory state"""
        return {
            "windows": {name: win.snapshot() for name, win in self.windows.items()},
            "cross_links": {k: list(v) for k, v in self._cross_links.items()},
        }

    def clear(self) -> None:
        """Clear all windows and links"""
        for window in self.windows.values():
            window.clear()
        self._cross_links.clear()

    def to_dict(self) -> dict:
        """Serialize to dictionary for persistence"""
        return {
            "windows": {
                name: win.snapshot()
                for name, win in self.windows.items()
            },
            "cross_links": {k: list(v) for k, v in self._cross_links.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        """Deserialize from dictionary"""
        memory = cls()
        # Reconstruct windows
        for name, win_data in data.get("windows", {}).items():
            if name in memory.windows:
                window = memory.windows[name]
                for item_dict in win_data.get("items", []):
                    item = ContextItem.from_dict(item_dict)
                    window._items[item.id] = item
                    window._update_eviction_queue(item)
        # Reconstruct cross-links
        memory._cross_links = {
            k: set(v) for k, v in data.get("cross_links", {}).items()
        }
        return memory
