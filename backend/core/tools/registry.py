"""
Tool Registry - Central Registry and Discovery for Agent Tools

Manages tool registration, discovery, access control, and execution routing.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
import logging

from .base import Tool, ToolContext, ToolResult, ToolPermission, SimpleTool

logger = logging.getLogger(__name__)


@dataclass
class ToolUsageStats:
    """Statistics for tool usage"""
    call_count: int = 0
    error_count: int = 0
    last_called: Optional[float] = None
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    cache_hits: int = 0


class ToolRegistry:
    """
    Central registry for tool discovery and execution.

    Features:
    - Tool registration by name
    - Permission-based discovery
    - Owner-based management
    - Usage statistics
    - Global caching layer
    """

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._by_permission: Dict[ToolPermission, Set[str]] = {
            p: set() for p in ToolPermission
        }
        self._by_owner: Dict[str, Set[str]] = {}
        self._stats: Dict[str, ToolUsageStats] = {}
        self._global_cache: Dict[str, tuple[Any, float]] = {}

    def register(self, tool: Tool, owner: Optional[str] = None) -> None:
        """Register a tool"""
        if tool.name in self._tools:
            logger.warning(f"Tool {tool.name} already registered, overwriting")

        self._tools[tool.name] = tool
        self._by_permission[tool.permission].add(tool.name)
        self._stats[tool.name] = ToolUsageStats()

        if owner:
            self._by_owner.setdefault(owner, set()).add(tool.name)

        logger.info(f"Registered tool: {tool.name} (owner={owner})")

    def unregister(self, tool_name: str) -> bool:
        """Remove tool from registry"""
        if tool_name not in self._tools:
            return False

        tool = self._tools[tool_name]
        del self._tools[tool_name]
        self._by_permission[tool.permission].discard(tool_name)
        self._stats.pop(tool_name, None)

        # Remove from owner mappings
        for owner, tools in self._by_owner.items():
            tools.discard(tool_name)

        logger.info(f"Unregistered tool: {tool_name}")
        return True

    def get(self, tool_name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(tool_name)

    def list_tools(
        self,
        agent_permissions: Optional[List[str]] = None,
        owner: Optional[str] = None,
    ) -> List[Tool]:
        """
        List available tools based on permissions and ownership.

        Args:
            agent_permissions: Permissions the caller possesses
            owner: Filter by tool owner

        Returns:
            List of accessible tools
        """
        if owner:
            tool_names = self._by_owner.get(owner, set())
            return [self._tools[name] for name in tool_names if name in self._tools]

        perms = set(agent_permissions or ["public"])
        results = []
        for tool in self._tools.values():
            if tool.permission.value in perms or "admin" in perms:
                results.append(tool)
        return results

    def get_schemas(
        self,
        agent_permissions: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get JSON schemas for all accessible tools"""
        tools = self.list_tools(agent_permissions)
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.get_schema(),
                "permission": tool.permission.value,
            }
            for tool in tools
        ]

    def execute(
        self,
        tool_name: str,
        context: ToolContext,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool by name with full instrumentation.

        Handles permission checking, caching, and stats collection.
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult.fail(error=f"Tool not found: {tool_name}")

        # Permission check
        if not tool.can_execute(context):
            return ToolResult.fail(error="Insufficient permissions")

        # Rate limiting (basic implementation)
        # Could be enhanced with token bucket
        stats = self._stats[tool_name]

        # Check global cache
        cache_key = f"{tool_name}:{hash(str(kwargs))}"
        if cache_key in self._global_cache:
            result, expiry = self._global_cache[cache_key]
            if expiry > time.time() if expiry else True:
                stats.cache_hits += 1
                return ToolResult.ok(data=result, cached=True)

        # Execute
        start = time.time()
        try:
            result = tool.execute(context, **kwargs)
            exec_time = time.time() - start

            # Update stats
            stats.call_count += 1
            stats.total_execution_time += exec_time
            stats.avg_execution_time = stats.total_execution_time / stats.call_count
            stats.last_called = time.time()

            result.execution_time = exec_time

            # Cache successful results
            if result.success and result.data is not None:
                self._global_cache[cache_key] = (result.data, time.time() + 60)  # 1 min global cache

            return result

        except Exception as e:
            stats.error_count += 1
            logger.error(f"Tool {tool_name} execution error: {e}", exc_info=True)
            return ToolResult.fail(error=str(e), execution_time=time.time() - start)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics"""
        return {
            "total_tools": len(self._tools),
            "by_permission": {
                p.value: len(names)
                for p, names in self._by_permission.items()
            },
            "by_owner": {
                owner: len(names)
                for owner, names in self._by_owner.items()
            },
            "tools": [
                {**tool.get_stats(), "permission": tool.permission.value}
                for tool in self._tools.values()
            ]
        }

    def clear_all_caches(self) -> None:
        """Clear caches for all tools and global cache"""
        for tool in self._tools.values():
            tool.clear_cache()
        self._global_cache.clear()

    def reset_stats(self) -> None:
        """Reset all usage statistics"""
        for stat in self._stats.values():
            stat.call_count = 0
            stat.error_count = 0
            stat.last_called = None
            stat.avg_execution_time = 0.0
            stat.total_execution_time = 0.0


def create_builtin_tools() -> List[Tool]:
    """
    Create the set of built-in QA tools.
    This is a placeholder - actual implementations would delegate to agents.
    """
    tools = []

    # Tool: code_static_analysis
    def tool_static_analysis(context, code: str, language: str, **kwargs):
        from agents.sentinel import run_sentinel
        import asyncio
        findings = asyncio.run(run_sentinel(code, language))
        return {"findings": findings, "count": len(findings)}

    tools.append(SimpleTool(
        name="code_static_analysis",
        func=tool_static_analysis,
        description="Analyze code for execution risks, errors, and logical defects",
        permission=ToolPermission.PUBLIC,
        param_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Source code to analyze"},
                "language": {"type": "string", "description": "Programming language"},
            },
            "required": ["code", "language"],
        },
    ))

    # Tool: security_scan
    def tool_security_scan(context, code: str, language: str, **kwargs):
        from agents.security import run_security
        import asyncio
        findings = asyncio.run(run_security(code, language))
        return {"findings": findings, "count": len(findings)}

    tools.append(SimpleTool(
        name="security_scan",
        func=tool_security_scan,
        description="Scan code for security vulnerabilities (OWASP-based)",
        permission=ToolPermission.PUBLIC,
        param_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
            "required": ["code", "language"],
        },
    ))

    # Tool: formal_review
    def tool_formal_review(context, code: str, language: str, **kwargs):
        from agents.critic import run_critic
        import asyncio
        findings = asyncio.run(run_critic(code, language))
        return {"findings": findings, "count": len(findings)}

    tools.append(SimpleTool(
        name="formal_review",
        func=tool_formal_review,
        description="Perform formal code review for semantic and design issues",
        permission=ToolPermission.PUBLIC,
        param_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
            "required": ["code", "language"],
        },
    ))

    # Tool: chaos_testing
    def tool_chaos_testing(context, code: str, language: str, **kwargs):
        from agents.tester import run_tester
        import asyncio
        suggestions = asyncio.run(run_tester(code, language, kwargs.get("agent_context")))
        return {"suggestions": suggestions, "count": len(suggestions)}

    tools.append(SimpleTool(
        name="chaos_testing",
        func=tool_chaos_testing,
        description="Generate adversarial test strategies",
        permission=ToolPermission.INTERNAL,
        param_schema={
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"},
            },
            "required": ["code", "language"],
        },
    ))

    # Tool: memory_search
    def tool_memory_search(context, query: str, limit: int = 10, **kwargs):
        # This tool connects to agent's episodic memory
        # Actual implementation would need memory reference
        return {"matches": [], "count": 0, "query": query}

    tools.append(SimpleTool(
        name="memory_search",
        func=tool_memory_search,
        description="Search episodic memory for similar past experiences",
        permission=ToolPermission.INTERNAL,
        param_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "description": "Max results", "default": 10},
            },
            "required": ["query"],
        },
    ))

    return tools


# Global registry
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry, initializing if needed"""
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        # Do NOT auto-register builtin tools here.
        # Agents will register their own tools during initialization.
    return _global_registry
