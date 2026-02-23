"""
Swarm Tools Package.

Provides model-agnostic tool calling for any LLM backend.
"""

from .base import ToolDefinition, ToolResult, ToolRegistry
from .builtin import register_builtin_tools
from .agent_loop import AgentLoop
from .backends import (
    OllamaToolFormatter,
    ClaudeToolFormatter,
    OpenAIToolFormatter,
    GenericToolFormatter,
    get_formatter_for_backend,
)

__all__ = [
    "ToolDefinition",
    "ToolResult",
    "ToolRegistry",
    "register_builtin_tools",
    "AgentLoop",
    "OllamaToolFormatter",
    "ClaudeToolFormatter",
    "OpenAIToolFormatter",
    "GenericToolFormatter",
    "get_formatter_for_backend",
]
