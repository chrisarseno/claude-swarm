"""
Base Agent Interface
Abstract interface for AI coding agents from different providers
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from enum import Enum
import asyncio


class AgentCapability(Enum):
    """Capabilities that different agents may have"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    REFACTORING = "refactoring"
    SECURITY = "security"
    PERFORMANCE = "performance"
    GENERAL = "general"


class AgentProvider(Enum):
    """Supported AI providers"""
    CLAUDE_CODE = "claude_code"  # Claude Code CLI
    ANTHROPIC_API = "anthropic_api"  # Anthropic API direct
    OPENAI = "openai"  # OpenAI models
    OLLAMA = "ollama"  # Local models via Ollama
    CODESTRAL = "codestral"  # Mistral's Codestral
    DEEPSEEK = "deepseek"  # DeepSeek Coder
    CUSTOM = "custom"  # Custom endpoint


class AgentStatus(Enum):
    """Agent status"""
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPED = "stopped"
    ERROR = "error"


class BaseAgent(ABC):
    """
    Abstract base class for AI coding agents.

    All agent implementations must inherit from this class and implement
    the required methods.
    """

    def __init__(
        self,
        agent_id: str,
        provider: AgentProvider,
        model_name: str,
        capabilities: list[AgentCapability],
        config: Optional[Dict[str, Any]] = None
    ):
        self.agent_id = agent_id
        self.provider = provider
        self.model_name = model_name
        self.capabilities = capabilities
        self.config = config or {}
        self.status = AgentStatus.STOPPED
        self._current_task: Optional[str] = None

    @abstractmethod
    async def start(self) -> bool:
        """
        Initialize and start the agent.

        Returns:
            bool: True if started successfully
        """
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """
        Stop the agent and cleanup resources.

        Returns:
            bool: True if stopped successfully
        """
        pass

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a task with the agent.

        Args:
            task: Task description or code to execute
            context: Additional context (files, environment, etc.)
            timeout: Maximum execution time in seconds

        Returns:
            Dict with 'output', 'success', 'error' keys
        """
        pass

    @abstractmethod
    async def is_healthy(self) -> bool:
        """
        Check if agent is healthy and responsive.

        Returns:
            bool: True if healthy
        """
        pass

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self.capabilities

    def get_cost_per_token(self) -> Dict[str, float]:
        """
        Get cost per token for this model.

        Returns:
            Dict with 'input' and 'output' costs per 1M tokens
        """
        # Default - override in subclasses
        return {"input": 0.0, "output": 0.0}

    def get_context_window(self) -> int:
        """Get maximum context window size in tokens"""
        # Default - override in subclasses
        return 200000

    def get_max_output_tokens(self) -> int:
        """Get maximum output tokens"""
        # Default - override in subclasses
        return 8192

    @property
    def is_available(self) -> bool:
        """Check if agent is available for new tasks"""
        return self.status == AgentStatus.IDLE

    @property
    def current_task(self) -> Optional[str]:
        """Get current task ID if any"""
        return self._current_task

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"id={self.agent_id}, "
            f"provider={self.provider.value}, "
            f"model={self.model_name}, "
            f"status={self.status.value})"
        )
