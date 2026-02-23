"""
Tool definitions and registry for model-agnostic tool calling.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Defines a tool that can be called by any LLM."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema for parameters
    execute: Callable[..., Coroutine[Any, Any, "ToolResult"]]

    def to_json_schema(self) -> Dict[str, Any]:
        """Return the full JSON schema for this tool's parameters."""
        return {
            "type": "object",
            "properties": self.parameters.get("properties", {}),
            "required": self.parameters.get("required", []),
        }


@dataclass
class ToolResult:
    """Result of executing a tool."""

    success: bool
    output: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> str:
        """Format as a message string for inclusion in LLM context."""
        if self.success:
            return self.output
        return f"Error: {self.error}"


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """Remove a tool."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Look up a tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Return JSON schemas for all tools (for LLM context injection)."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.to_json_schema(),
            })
        return schemas

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Unknown tool: {name}",
            )
        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' raised: {e}",
            )
