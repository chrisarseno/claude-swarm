"""
OpenAI Agent
Integration with OpenAI's GPT models
"""

from typing import Optional, Dict, Any
import os
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .base import BaseAgent, AgentProvider, AgentCapability, AgentStatus


class OpenAIAgent(BaseAgent):
    """
    Agent implementation using OpenAI API.

    Supports GPT-4, GPT-4 Turbo, and specialized code models.
    Good for code generation and general-purpose tasks.
    """

    MODELS = {
        "gpt-4": {
            "context": 8192,
            "output": 8192,
            "cost": {"input": 30.0, "output": 60.0}
        },
        "gpt-4-turbo": {
            "context": 128000,
            "output": 4096,
            "cost": {"input": 10.0, "output": 30.0}
        },
        "gpt-4o": {
            "context": 128000,
            "output": 16384,
            "cost": {"input": 2.5, "output": 10.0}
        },
        "gpt-3.5-turbo": {
            "context": 16385,
            "output": 4096,
            "cost": {"input": 0.5, "output": 1.5}
        },
        "o1": {
            "context": 200000,
            "output": 100000,
            "cost": {"input": 15.0, "output": 60.0}
        },
        "o1-mini": {
            "context": 128000,
            "output": 65536,
            "cost": {"input": 3.0, "output": 12.0}
        }
    }

    def __init__(
        self,
        agent_id: str,
        model_name: str = "gpt-4o",
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        if not OPENAI_AVAILABLE:
            raise ImportError(
                "openai package not installed. "
                "Install with: pip install openai"
            )

        # OpenAI models support most capabilities
        capabilities = [
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.TESTING,
            AgentCapability.DOCUMENTATION,
            AgentCapability.ANALYSIS,
            AgentCapability.REFACTORING,
            AgentCapability.GENERAL
        ]

        super().__init__(
            agent_id=agent_id,
            provider=AgentProvider.OPENAI,
            model_name=model_name,
            capabilities=capabilities,
            config=config
        )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client: Optional[openai.OpenAI] = None

    async def start(self) -> bool:
        """Initialize OpenAI client"""
        try:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not set")

            self.status = AgentStatus.STARTING
            self._client = openai.OpenAI(api_key=self.api_key)
            self.status = AgentStatus.IDLE
            return True

        except Exception as e:
            self.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Cleanup OpenAI client"""
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
        """Execute task with OpenAI API"""
        if not self._client:
            return {
                "success": False,
                "error": "Agent not started",
                "output": ""
            }

        try:
            self.status = AgentStatus.BUSY
            self._current_task = context.get("task_id") if context else None

            # Build messages
            messages = []

            # System message
            system_prompt = self.config.get(
                "system_prompt",
                "You are an expert software engineer. Provide clear, "
                "concise, and correct code solutions."
            )
            messages.append({"role": "system", "content": system_prompt})

            # Add context if provided
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
                messages.append({"role": "user", "content": task})

            # Call API
            response = self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=self.config.get("max_tokens", 4096),
                temperature=self.config.get("temperature", 0.0)
            )

            output = response.choices[0].message.content

            self.status = AgentStatus.IDLE
            self._current_task = None

            return {
                "success": True,
                "output": output,
                "error": None,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
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
            self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            return True
        except Exception:
            return False

    def get_cost_per_token(self) -> Dict[str, float]:
        """Get pricing for this model"""
        model_info = self.MODELS.get(
            self.model_name,
            {"cost": {"input": 2.5, "output": 10.0}}
        )
        return model_info["cost"]

    def get_context_window(self) -> int:
        """Get context window for this model"""
        model_info = self.MODELS.get(
            self.model_name,
            {"context": 128000}
        )
        return model_info["context"]

    def get_max_output_tokens(self) -> int:
        """Get max output tokens"""
        model_info = self.MODELS.get(
            self.model_name,
            {"output": 4096}
        )
        return model_info["output"]
