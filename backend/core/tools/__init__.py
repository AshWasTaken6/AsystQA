"""
Tool System - Agent Tool-Calling Interface

Exports:
- Tool, SimpleTool, ToolResult, ToolContext, ToolPermission (base classes)
- ToolRegistry (registry)
- get_tool_registry() (global registry getter)
"""

from .base import (
    Tool,
    SimpleTool,
    ToolResult,
    ToolContext,
    ToolPermission,
)
from .registry import (
    ToolRegistry,
    ToolUsageStats,
    create_builtin_tools,
    get_tool_registry,
)

__all__ = [
    "Tool",
    "SimpleTool",
    "ToolResult",
    "ToolContext",
    "ToolPermission",
    "ToolRegistry",
    "ToolUsageStats",
    "create_builtin_tools",
    "get_tool_registry",
]
