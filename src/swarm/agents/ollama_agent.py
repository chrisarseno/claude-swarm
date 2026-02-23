"""
Ollama Agent
Integration with local models via Ollama
"""

from typing import Optional, Dict, Any
import aiohttp
from .base import BaseAgent, AgentProvider, AgentCapability, AgentStatus


class OllamaAgent(BaseAgent):
    """
    Agent implementation using Ollama for local models.

    Supports running models locally without API costs.
    Good for privacy-sensitive tasks, development, and cost savings.

    Popular models:
    - codellama: Meta's Code Llama (7B, 13B, 34B)
    - deepseek-coder: DeepSeek Coder (1.3B, 6.7B, 33B)
    - phind-codellama: Phind's fine-tuned Code Llama
    - wizardcoder: WizardCoder models
    - mistral: Mistral models
    """

    # Model capabilities (approximate)
    MODEL_CAPABILITIES = {
        "codellama": [
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.CODE_REVIEW
        ],
        "deepseek-coder": [
            AgentCapability.CODE_GENERATION,
            AgentCapability.CODE_REVIEW,
            AgentCapability.DEBUGGING,
            AgentCapability.REFACTORING
        ],
        "phind-codellama": [
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING,
            AgentCapability.ANALYSIS
        ],
        "wizardcoder": [
            AgentCapability.CODE_GENERATION,
            AgentCapability.DEBUGGING
        ],
        "mistral": [
            AgentCapability.CODE_GENERATION,
            AgentCapability.ANALYSIS,
            AgentCapability.GENERAL
        ]
    }

    def __init__(
        self,
        agent_id: str,
        model_name: str = "codellama",
        ollama_url: str = "http://localhost:11434",
        config: Optional[Dict[str, Any]] = None
    ):
        # Get capabilities based on model
        base_model = model_name.split(":")[0]  # Handle model:tag format
        capabilities = self.MODEL_CAPABILITIES.get(
            base_model,
            [AgentCapability.CODE_GENERATION, AgentCapability.GENERAL]
        )

        super().__init__(
            agent_id=agent_id,
            provider=AgentProvider.OLLAMA,
            model_name=model_name,
            capabilities=capabilities,
            config=config
        )

        self.ollama_url = ollama_url
        self._session: Optional[aiohttp.ClientSession] = None

    async def start(self) -> bool:
        """Initialize Ollama connection"""
        try:
            self.status = AgentStatus.STARTING
            self._session = aiohttp.ClientSession()

            # Check if Ollama is running
            async with self._session.get(f"{self.ollama_url}/api/tags") as resp:
                if resp.status != 200:
                    raise Exception("Ollama not accessible")

            # Check if model is available
            data = await resp.json()
            model_names = [m["name"] for m in data.get("models", [])]

            if self.model_name not in model_names:
                # Try to pull the model
                await self._pull_model()

            self.status = AgentStatus.IDLE
            return True

        except Exception as e:
            self.status = AgentStatus.ERROR
            if self._session:
                await self._session.close()
            return False

    async def stop(self) -> bool:
        """Cleanup Ollama connection"""
        try:
            if self._session:
                await self._session.close()
                self._session = None

            self.status = AgentStatus.STOPPED
            return True
        except Exception:
            return False

    async def _pull_model(self):
        """Pull model from Ollama registry"""
        if not self._session:
            return

        async with self._session.post(
            f"{self.ollama_url}/api/pull",
            json={"name": self.model_name}
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to pull model {self.model_name}")

    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute task with Ollama"""
        if not self._session:
            return {
                "success": False,
                "error": "Agent not started",
                "output": ""
            }

        try:
            self.status = AgentStatus.BUSY
            self._current_task = context.get("task_id") if context else None

            # Build prompt
            system_prompt = self.config.get(
                "system_prompt",
                "You are an expert software engineer. Provide clear, "
                "concise, and correct code solutions."
            )

            # Add context if provided
            if context and context.get("files"):
                context_text = "\n\n".join([
                    f"File: {f['path']}\n```\n{f['content']}\n```"
                    for f in context["files"]
                ])
                prompt = f"Context:\n{context_text}\n\nTask:\n{task}"
            else:
                prompt = task

            # Call Ollama API
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": self.config.get("temperature", 0.0),
                    "num_predict": self.config.get("max_tokens", 4096)
                }
            }

            timeout_obj = aiohttp.ClientTimeout(total=timeout) if timeout else None

            async with self._session.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=timeout_obj
            ) as resp:
                if resp.status != 200:
                    raise Exception(f"Ollama API error: {resp.status}")

                data = await resp.json()
                output = data.get("response", "")

            self.status = AgentStatus.IDLE
            self._current_task = None

            return {
                "success": True,
                "output": output,
                "error": None,
                "usage": {
                    "input_tokens": data.get("prompt_eval_count", 0),
                    "output_tokens": data.get("eval_count", 0)
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
        """Check if Ollama is responsive"""
        if not self._session:
            return False

        try:
            async with self._session.get(f"{self.ollama_url}/api/tags") as resp:
                return resp.status == 200
        except Exception:
            return False

    def get_cost_per_token(self) -> Dict[str, float]:
        """Local models have no API cost"""
        return {"input": 0.0, "output": 0.0}

    def get_context_window(self) -> int:
        """Context window varies by model"""
        # Code Llama and similar models typically support 16K
        return 16384

    def get_max_output_tokens(self) -> int:
        """Max output tokens"""
        return 4096
