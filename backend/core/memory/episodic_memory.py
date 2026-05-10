"""
Episodic Memory - Long-Term Semantic Memory with Vector Retrieval

Implements a vector database-backed memory system for storing and retrieving
past experiences, code analyses, and learned patterns using semantic similarity.

Features:
- Vector embeddings for semantic search (using sentence-transformers or OpenAI)
- Multiple storage backends: in-memory, SQLite, Pinecone, Weaviate, Qdrant
- Memory consolidation: similar memories get merged over time
- Forgetting curves: less relevant memories decay over time
- Temporal indexing: memories organized by recency and relevance
"""

import hashlib
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional
import numpy as np


class MemoryImportance(Enum):
    """Importance rating affecting retention"""
    CRITICAL = 1.0
    HIGH = 0.8
    MEDIUM = 0.6
    LOW = 0.4
    MINIMAL = 0.2


@dataclass
class MemoryEntry:
    """
    A single episodic memory entry with vector embedding.

    Attributes:
        id: Unique identifier
        content: Memory text/content
        embedding: Vector representation (numpy array)
        metadata: Structured metadata (language, agent, severity, etc.)
        timestamp: When memory was created
        importance: Importance score (affects retention)
        access_count: How many times retrieved
        last_accessed: Last retrieval timestamp
        decay_rate: Rate at which relevance decays (per day)
        linked_episodes: IDs of related memories
        source_agent: Which agent created this
    """
    id: str
    content: str
    embedding: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    importance: float = MemoryImportance.MEDIUM.value
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    decay_rate: float = 0.01  # Per day
    linked_episodes: list[str] = field(default_factory=list)
    source_agent: Optional[str] = None

    def current_relevance(self, current_time: Optional[float] = None) -> float:
        """
        Calculate current relevance score considering time decay.

        Args:
            current_time: Current timestamp (default: now)

        Returns:
            Relevance score between 0 and 1
        """
        now = current_time or time.time()
        days_elapsed = (now - self.timestamp) / 86400

        # Exponential decay
        decay_factor = np.exp(-self.decay_rate * days_elapsed)

        # Boost from access frequency (logarithmic to prevent abuse)
        access_boost = np.log1p(self.access_count) * 0.1

        # Importance factor
        relevance = (self.importance + access_boost) * decay_factor

        return max(0.0, min(1.0, relevance))

    def touch(self) -> None:
        """Mark as accessed"""
        self.access_count += 1
        self.last_accessed = time.time()

    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding.tolist() if self.embedding is not None else None,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "decay_rate": self.decay_rate,
            "linked_episodes": self.linked_episodes,
            "source_agent": self.source_agent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        """Deserialize from dictionary"""
        data["embedding"] = np.array(data["embedding"]) if data.get("embedding") else None
        return cls(**data)


@dataclass
class SimilaritySearchResult:
    """Result of a similarity search"""
    entry: MemoryEntry
    score: float  # 0-1 similarity
    rank: int


class VectorBackend(ABC):
    """Abstract base class for vector database backends"""

    @abstractmethod
    def add(self, entry: MemoryEntry) -> str:
        """Add entry to store"""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> list[SimilaritySearchResult]:
        """Search by vector similarity"""
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID"""
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete entry"""
        pass

    @abstractmethod
    def update(self, entry: MemoryEntry) -> bool:
        """Update existing entry"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all entries"""
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total count"""
        pass


class InMemoryVectorBackend(VectorBackend):
    """
    Simple in-memory vector store using numpy for similarity search.
    Suitable for development and small-scale deployments.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._entries: dict[str, MemoryEntry] = {}
        self._embeddings: Optional[np.ndarray] = None  # Matrix of all embeddings
        self._ids: list[str] = []
        self._dirty = True

    def add(self, entry: MemoryEntry) -> str:
        """Add entry to in-memory store"""
        if entry.embedding is None:
            raise ValueError("Entry must have embedding")
        if entry.embedding.shape[0] != self.dimension:
            raise ValueError(f"Embedding dimension mismatch: expected {self.dimension}, got {entry.embedding.shape[0]}")

        self._entries[entry.id] = entry
        self._dirty = True
        return entry.id

    def _ensure_index(self) -> None:
        """Rebuild embedding matrix for efficient search"""
        if not self._dirty:
            return
        if self._entries:
            self._ids = list(self._entries.keys())
            self._embeddings = np.stack([
                self._entries[eid].embedding
                for eid in self._ids
            ])
        else:
            self._embeddings = None
            self._ids = []
        self._dirty = False

    def search(
        self,
        query_embedding: np.ndarray,
        limit: int = 10,
        filters: Optional[dict] = None
    ) -> list[SimilaritySearchResult]:
        """Search by cosine similarity"""
        self._ensure_index()
        if self._embeddings is None or len(self._ids) == 0:
            return []

        # Normalize query
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)

        # Compute cosine similarities
        embeddings_norm = self._embeddings / (np.linalg.norm(self._embeddings, axis=1, keepdims=True) + 1e-8)
        similarities = np.dot(embeddings_norm, query_norm)

        # Get top-k indices
        top_k = min(limit, len(similarities))
        top_indices = np.argsort(-similarities)[:top_k]

        results = []
        for rank, idx in enumerate(top_indices):
            entry_id = self._ids[idx]
            entry = self._entries[entry_id]

            # Apply filters
            if filters:
                match = True
                for key, value in filters.items():
                    if key not in entry.metadata or entry.metadata[key] != value:
                        match = False
                        break
                if not match:
                    continue

            results.append(SimilaritySearchResult(
                entry=entry,
                score=float(similarities[idx]),
                rank=rank
            ))

        return results

    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        return self._entries.get(memory_id)

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._entries:
            del self._entries[memory_id]
            self._dirty = True
            return True
        return False

    def update(self, entry: MemoryEntry) -> bool:
        if entry.id in self._entries:
            self._entries[entry.id] = entry
            self._dirty = True
            return True
        return False

    def clear(self) -> None:
        self._entries.clear()
        self._embeddings = None
        self._ids = []
        self._dirty = True

    def count(self) -> int:
        return len(self._entries)


class EpisodicMemory:
    """
    Long-term semantic memory with vector similarity search.

    Manages the storage and retrieval of past experiences, findings,
    and learned patterns using vector embeddings for semantic matching.
    """

    def __init__(
        self,
        backend: Optional[VectorBackend] = None,
        embedding_function: Optional[Callable[[str], np.ndarray]] = None,
        dimension: int = 384,
        consolidation_threshold: float = 0.95,
        max_entries: int = 10000,
    ):
        """
        Initialize episodic memory.

        Args:
            backend: Vector storage backend (default: InMemory)
            embedding_function: Function to convert text to embeddings
            dimension: Embedding dimension (must match embedding_function output)
            consolidation_threshold: Similarity threshold for memory consolidation
            max_entries: Maximum entries before forced pruning
        """
        self.backend = backend or InMemoryVectorBackend(dimension)
        self.embedding_function = embedding_function or self._default_embedding
        self.dimension = dimension
        self.consolidation_threshold = consolidation_threshold
        self.max_entries = max_entries
        self._consolidation_queue: list[tuple[str, str, float]] = []  # (id1, id2, similarity)

    def _default_embedding(self, text: str) -> np.ndarray:
        """
        Default embedding function using simple TF-IDF-like hashing.

        In production, replace with:
        - sentence-transformers (all-MiniLM-L6-v2)
        - OpenAI text-embedding-3-small
        - Cohere embed-english-v3.0
        """
        # Simple deterministic embedding based on character n-grams
        # This is a placeholder - use proper embeddings in production
        embedding = np.zeros(self.dimension, dtype=np.float32)
        if not text:
            return embedding

        # Use hash-based features to get deterministic embeddings
        for n in range(1, 4):  # 1-3 grams
            for i in range(len(text) - n + 1):
                gram = text[i:i+n]
                idx = int(hashlib.md5(gram.encode()).hexdigest(), 16) % self.dimension
                embedding[idx] += 1.0

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        return embedding

    def remember(
        self,
        content: str,
        metadata: Optional[dict] = None,
        importance: float = MemoryImportance.MEDIUM.value,
        embedding: Optional[np.ndarray] = None,
        source_agent: Optional[str] = None,
        linked_episodes: Optional[list[str]] = None,
    ) -> str:
        """
        Store a new episodic memory.

        Args:
            content: Textual description of the memory
            metadata: Structured metadata (language, issue_type, agent, etc.)
            importance: Importance score 0-1
            embedding: Pre-computed embedding (optional)
            source_agent: Agent that generated this memory
            linked_episodes: IDs of related memories

        Returns:
            Memory ID
        """
        if embedding is None:
            embedding = self.embedding_function(content)

        memory_id = str(uuid.uuid4())
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            embedding=embedding,
            metadata=metadata or {},
            importance=importance,
            source_agent=source_agent,
            linked_episodes=linked_episodes or [],
        )

        self.backend.add(entry)

        # Check if consolidation is needed
        self._check_consolidation(entry)

        # Prune if over limit
        if self.backend.count() > self.max_entries:
            self._prune_memories()

        return memory_id

    def recall(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.7,
        filters: Optional[dict] = None,
        time_range: Optional[tuple[float, float]] = None,
    ) -> list[SimilaritySearchResult]:
        """
        Retrieve memories by semantic similarity.

        Args:
            query: Natural language query
            limit: Maximum results
            min_similarity: Minimum similarity threshold
            filters: Metadata filters
            time_range: Optional (start_time, end_time) tuple

        Returns:
            Ordered list of similar memories with scores
        """
        query_embedding = self.embedding_function(query)
        results = self.backend.search(
            query_embedding,
            limit=limit * 2,  # Get more for filtering
            filters=filters
        )

        # Filter and re-rank
        filtered = []
        for result in results:
            # Temporal filtering
            if time_range:
                entry = result.entry
                if not (time_range[0] <= entry.timestamp <= time_range[1]):
                    continue

            # Apply temporal decay to score
            entry = result.entry
            relevance = entry.current_relevance()
            adjusted_score = result.score * relevance

            if adjusted_score >= min_similarity:
                result.score = adjusted_score
                filtered.append(result)
                entry.touch()  # Mark as accessed
                self.backend.update(entry)

        # Sort by adjusted score
        filtered.sort(key=lambda r: r.score, reverse=True)

        # Update rankings
        for rank, result in enumerate(filtered):
            result.rank = rank

        return filtered[:limit]

    def recall_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve specific memory by ID"""
        entry = self.backend.get(memory_id)
        if entry:
            entry.touch()
            self.backend.update(entry)
        return entry

    def forget(self, memory_id: str) -> bool:
        """Explicitly remove a memory"""
        return self.backend.delete(memory_id)

    def _check_consolidation(self, new_entry: MemoryEntry) -> None:
        """
        Check if new memory is similar to existing ones and consolidate.

        Consolidation merges very similar memories to avoid redundancy.
        """
        # Search for similar memories
        similar = self.backend.search(
            new_entry.embedding,
            limit=5,
            filters=None
        )

        for result in similar:
            if result.score >= self.consolidation_threshold:
                existing = result.entry
                # Merge content (very basic - could be more sophisticated)
                merged_content = f"{new_entry.content} | Also: {existing.content}"
                # Create consolidated entry
                new_id = self.remember(
                    content=merged_content,
                    metadata={**new_entry.metadata, **existing.metadata},
                    importance=max(new_entry.importance, existing.importance),
                    embedding=None,  # Re-compute
                    source_agent=new_entry.source_agent,
                    linked_episodes=list(set(
                        new_entry.linked_episodes + existing.linked_episodes
                    )),
                )
                # Remove the old redundant memory
                self.backend.delete(existing.id)
                break

    def _prune_memories(self) -> int:
        """
        Prune less relevant memories when over capacity.

        Uses a combination of:
        - Current relevance score
        - Importance
        - Access patterns
        """
        excess = self.backend.count() - self.max_entries
        if excess <= 0:
            return 0

        # Score all entries for retention
        scored = []
        for entry in self.backend._entries.values():
            relevance = entry.current_relevance()
            retention_score = relevance * entry.importance + (np.log1p(entry.access_count) * 0.1)
            scored.append((retention_score, entry.id))

        # Sort by retention score (ascending - lowest retention first)
        scored.sort(key=lambda x: x[0])

        # Remove lowest scored entries
        removed = 0
        for score, eid in scored[:excess]:
            if self.backend.delete(eid):
                removed += 1

        return removed

    def get_recent(self, hours: float = 24, limit: int = 20) -> list[MemoryEntry]:
        """Get recent memories"""
        cutoff = time.time() - (hours * 3600)
        results = []
        for entry in self.backend._entries.values():
            if entry.timestamp >= cutoff:
                results.append(entry)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_frequent(self, min_access: int = 5, limit: int = 20) -> list[MemoryEntry]:
        """Get most frequently accessed memories"""
        results = [
            e for e in self.backend._entries.values()
            if e.access_count >= min_access
        ]
        results.sort(key=lambda e: e.access_count, reverse=True)
        return results[:limit]

    def stats(self) -> dict:
        """Get memory statistics"""
        entries = list(self.backend._entries.values())
        if not entries:
            return {
                "total_entries": 0,
                "avg_relevance": 0,
                "avg_importance": 0,
                "avg_access_count": 0,
                "by_source": {},
            }

        return {
            "total_entries": len(entries),
            "avg_relevance": np.mean([e.current_relevance() for e in entries]),
            "avg_importance": np.mean([e.importance for e in entries]),
            "avg_access_count": np.mean([e.access_count for e in entries]),
            "by_source": {
                source: sum(1 for e in entries if e.source_agent == source)
                for source in set(e.source_agent for e in entries if e.source_agent)
            },
        }

    def export(self, path: str) -> int:
        """Export all memories to JSON file"""
        data = {
            "version": "1.0",
            "entries": [e.to_dict() for e in self.backend._entries.values()],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        return len(data["entries"])

    def import_from(self, path: str) -> int:
        """Import memories from JSON file"""
        with open(path, 'r') as f:
            data = json.load(f)

        count = 0
        for entry_dict in data.get("entries", []):
            try:
                entry = MemoryEntry.from_dict(entry_dict)
                self.backend.add(entry)
                count += 1
            except Exception as e:
                print(f"Failed to import entry: {e}")

        return count

    def clear(self) -> None:
        """Clear all episodic memories"""
        self.backend.clear()
