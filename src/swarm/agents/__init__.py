"""
Multi-Model Agent System
Support for various AI providers and models
"""

from .base import (
    BaseAgent,
    AgentCapability,
    AgentProvider,
    AgentStatus
)

from .claude_code_agent import ClaudeCodeAgent
from .anthropic_agent import AnthropicAgent
from .openai_agent import OpenAIAgent
from .ollama_agent import OllamaAgent

from .router import AgentRouter, TaskPriority, TaskComplexity

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentCapability",
    "AgentProvider",
    "AgentStatus",

    # Agent implementations
    "ClaudeCodeAgent",
    "AnthropicAgent",
    "OpenAIAgent",
    "OllamaAgent",

    # Router
    "AgentRouter",
    "TaskPriority",
    "TaskComplexity"
]
