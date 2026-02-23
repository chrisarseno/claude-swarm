"""
Claude Code Agent
Wraps the existing Claude Code CLI functionality
"""

from typing import Optional, Dict, Any
from ..claude.wrapper import ClaudeInstance
from .base import BaseAgent, AgentProvider, AgentCapability, AgentStatus


class ClaudeCodeAgent(BaseAgent):
    """
    Agent implementation for Claude Code CLI.

    Uses the local Claude Code installation to execute tasks.
    Supports all capabilities through Claude's frontier models.
    """

    def __init__(
        self,
        agent_id: str,
        model_name: str = "sonnet",  # sonnet, opus, haiku
        config: Optional[Dict[str, Any]] = None
    ):
        # Claude Code supports all capabilities
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
            provider=AgentProvider.CLAUDE_CODE,
            model_name=model_name,
            capabilities=capabilities,
            config=config
        )

        self._instance: Optional[ClaudeInstance] = None

    async def start(self) -> bool:
        """Initialize Claude Code instance"""
        try:
            self.status = AgentStatus.STARTING

            # Get working directory from config
            working_dir = self.config.get("working_dir", ".")

            # Create Claude instance
            self._instance = ClaudeInstance(
                instance_id=self.agent_id,
                working_directory=working_dir,
                model=self.model_name
            )

            # Start the instance
            success = await self._instance.start()

            if success:
                self.status = AgentStatus.IDLE
            else:
                self.status = AgentStatus.ERROR

            return success

        except Exception as e:
            self.status = AgentStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop Claude Code instance"""
        try:
            if self._instance:
                await self._instance.stop()
                self._instance = None

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
        """Execute task with Claude Code"""
        if not self._instance:
            return {
                "success": False,
                "error": "Agent not started",
                "output": ""
            }

        try:
            self.status = AgentStatus.BUSY
            self._current_task = context.get("task_id") if context else None

            # Execute with Claude Code
            result = await self._instance.execute(
                prompt=task,
                timeout=timeout
            )

            self.status = AgentStatus.IDLE
            self._current_task = None

            return {
                "success": result.get("success", False),
                "output": result.get("output", ""),
                "error": result.get("error")
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
        """Check if Claude Code is responsive"""
        if not self._instance:
            return False

        try:
            # Simple health check - try to get status
            return self._instance.is_running
        except Exception:
            return False

    def get_cost_per_token(self) -> Dict[str, float]:
        """Get Claude pricing (per 1M tokens)"""
        costs = {
            "sonnet": {"input": 3.0, "output": 15.0},  # Claude Sonnet 4.5
            "opus": {"input": 15.0, "output": 75.0},   # Claude Opus 4.5
            "haiku": {"input": 0.25, "output": 1.25}   # Claude Haiku 4
        }
        return costs.get(self.model_name, {"input": 3.0, "output": 15.0})

    def get_context_window(self) -> int:
        """Claude models support 200K context"""
        return 200000

    def get_max_output_tokens(self) -> int:
        """Claude Code output limit"""
        return 8192
