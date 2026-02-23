"""
Anthropic API Agent
Direct integration with Anthropic's API for Claude models
"""

from typing import Optional, Dict, Any
import os
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base import BaseAgent, AgentProvider, AgentCapability, AgentStatus


class AnthropicAgent(BaseAgent):
    """
    Agent implementation using Anthropic API directly.

    More flexible than Claude Code for API-based workflows.
    Supports streaming, custom system prompts, and fine-grained control.
    """

    MODELS = {
        "claude-opus-4.5": {
            "context": 200000,
            "output": 8192,
            "cost": {"input": 15.0, "output": 75.0}
        },
        "claude-sonnet-4.5": {
            "context": 200000,
            "output": 8192,
            "cost": {"input": 3.0, "output": 15.0}
        },
        "claude-haiku-4": {
            "context": 200000,
            "output": 8192,
            "cost": {"input": 0.25, "output": 1.25}
        },
        "claude-3-5-sonnet-20241022": {
            "context": 200000,
            "output": 8192,
            "cost": {"input": 3.0, "output": 15.0}
        }
    }

    def __init__(
        self,
        agent_id: str,
        model_name: str = "claude-sonnet-4.5",
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        # All Claude models support all capabilities
        capabilities = [
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.ANALYSIS,
            AgentCapability.REFACTORING,
            AgentCapability.SECURITY,
            AgentCapability.PERFORMANCE,
            AgentCapability.GENERAL
        ]

        super().__init__(
            agent_id=agent_id,
            provider=AgentProvider.ANTHROPIC_API,
            model_name=model_name,
            capabilities=capabilities,
            config=config
        )

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client: Optional[anthropic.Anthropic] = None

    async def start(self) -> bool:
        """Initialize Anthropic client"""
        try:
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY not set")

            self.status = AgentStatus.STARTING
            self._client = anthropic.Anthropic(api_key=self.api_key)
            self.status = AgentStatus.IDLE
            return True

        except Exception as e:
            self.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Cleanup Anthropic client"""
        try:
            self._client = None
            self.status = AgentStatus.STOPPED
            return True
        except Exception:
            return False

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute task with Anthropic API"""
        if not self._client:
            return {
                "success": False,
                "error": "Agent not started",
                "output": ""
            }

        try:
            self.status = AgentStatus.BUSY
            self._current_task = context.get("task_id") if context else None

            # Build system prompt
            system_prompt = self.config.get(
                "system_prompt",
                "You are an expert software engineer. Provide clear, "
                "concise, and correct code solutions."
            )

            # Add context if provided
            messages = []
            if context and context.get("files"):
                context_text = "\n\n".join([
                    f"File: {f['path']}\n```\n{f['content']}\n```"
                    for f in context["files"]
                ])
                messages.append({
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nTask:\n{task}"
                })
            else:
                messages.append({
                    "role": "user",
                    "content": task
                })

            # Call API
            response = self._client.messages.create(
                model=self.model_name,
                max_tokens=self.config.get("max_tokens", 4096),
                system=system_prompt,
                messages=messages,
                temperature=self.config.get("temperature", 0.0)
            )

            output = response.content[0].text

            self.status = AgentStatus.IDLE
            self._current_task = None

            return {
                "success": True,
                "output": output,
                "error": None,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

        except Exception as e:
            self.status = AgentStatus.IDLE
            self._current_task = None

            return {
                "success": False,
                "error": str(e),
                "output": ""
            }

    async def is_healthy(self) -> bool:
        """Check if API is accessible"""
        if not self._client:
            return False

        try:
            # Simple test call
            self._client.messages.create(
                model=self.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception:
            return False

    def get_cost_per_token(self) -> Dict[str, float]:
        """Get pricing for this model"""
        model_info = self.MODELS.get(
            self.model_name,
            {"cost": {"input": 3.0, "output": 15.0}}
        )
        return model_info["cost"]

    def get_context_window(self) -> int:
        """Get context window for this model"""
        model_info = self.MODELS.get(
            self.model_name,
            {"context": 200000}
        )
        return model_info["context"]

    def get_max_output_tokens(self) -> int:
        """Get max output tokens"""
        model_info = self.MODELS.get(
            self.model_name,
            {"output": 8192}
        )
        return model_info["output"]
