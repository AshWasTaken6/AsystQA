"""
Tool Base Classes and Interfaces

Core abstractions for agent tools including permissions, results, and base types.
"""

import inspect
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class ToolPermission(Enum):
    """Tool permission levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    ADMIN = "admin"


@dataclass
class ToolContext:
    """
    Execution context for a tool call.
    """
    agent_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    permissions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "admin" in self.permissions


class ToolResult(BaseModel):
    """
    Standardized result from tool execution.
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time: float = 0.0
    cached: bool = False

    @classmethod
    def ok(cls, data: Any, **kwargs) -> "ToolResult":
        return cls(success=True, data=data, **kwargs)

    @classmethod
    def fail(cls, error: str, **kwargs) -> "ToolResult":
        return cls(success=False, error=error, **kwargs)


class Tool(ABC):
    """
    Abstract base class for all agent tools.

    Tools are self-describing capabilities that agents can invoke.
    Subclasses must implement execute() and get_schema().
    """

    def __init__(
        self,
        name: str,
        description: str,
        permission: ToolPermission = ToolPermission.PUBLIC,
        cache_ttl: Optional[int] = None,
        rate_limit: Optional[int] = None,
    ):
        self.name = name
        self.description = description
        self.permission = permission
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit

        # Statistics
        self.call_count = 0
        self.error_count = 0
        self.last_called: Optional[float] = None
        self._cache: Dict[str, tuple[Any, float]] = {}

    @abstractmethod
    def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        """Execute tool logic"""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON schema for parameters"""
        pass

    def can_execute(self, context: ToolContext) -> bool:
        """Check if tool can run in this context"""
        if not context.has_permission(self.permission.value):
            logger.warning(f"Tool {self.name}: Permission denied for {context.agent_id}")
            return False
        return True

    def _cache_key(self, **kwargs) -> str:
        import hashlib, json
        key_data = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.md5(key_data.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        result, expiry = self._cache[key]
        if expiry and time.time() > expiry:
            del self._cache[key]
            return None
        return result

    def _set_cached(self, key: str, result: Any) -> None:
        if self.cache_ttl:
            expiry = time.time() + self.cache_ttl
        else:
            expiry = None
        self._cache[key] = (result, expiry)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(1, self.call_count),
            "last_called": self.last_called,
        }

    def clear_cache(self) -> None:
        self._cache.clear()


class SimpleTool(Tool):
    """
    Wraps a function as a Tool.
    """

    def __init__(
        self,
        name: str,
        func: Callable,
        description: str,
        param_schema: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        import inspect
        from typing import Callable

        super().__init__(name, description, **kwargs)
        self.func = func
        self._param_schema = param_schema or self._infer_schema(func)

    def _infer_schema(self, func: Callable) -> Dict[str, Any]:
        sig = inspect.signature(func)
        properties = {}
        required = []

        for name, param in sig.parameters.items():
            if name in ("self", "context"):
                continue
            param_info = {"type": "string", "description": f"Parameter {name}"}
            if param.annotation != inspect.Parameter.empty:
                type_map = {str: "string", int: "integer", float: "number",
                           bool: "boolean", list: "array", dict: "object"}
                if param.annotation in type_map:
                    param_info["type"] = type_map[param.annotation]
            properties[name] = param_info
            if param.default == inspect.Parameter.empty:
                required.append(name)

        return {"type": "object", "properties": properties, "required": required}

    def execute(self, context: ToolContext, **kwargs) -> ToolResult:
        import time
        self.call_count += 1
        self.last_called = time.time()

        try:
            start = time.time()
            cache_key = self._cache_key(**kwargs) if self.cache_ttl else None
            if cache_key:
                cached = self._get_cached(cache_key)
                if cached is not None:
                    return ToolResult.ok(data=cached, execution_time=0.0, cached=True)

            result = self.func(context, **kwargs)

            if cache_key and isinstance(result, ToolResult) and result.success:
                self._set_cached(cache_key, result.data if hasattr(result, 'data') else result)
            elif cache_key and cache_key in self._cache:
                self._set_cached(cache_key, result)

            exec_time = time.time() - start
            return ToolResult.ok(
                data=result.data if hasattr(result, 'data') else result,
                execution_time=exec_time
            )
        except Exception as e:
            self.error_count += 1
            logger.error(f"Tool {self.name} error: {e}", exc_info=True)
            return ToolResult.fail(error=str(e), execution_time=time.time() - start)

    def get_schema(self) -> Dict[str, Any]:
        return self._param_schema
