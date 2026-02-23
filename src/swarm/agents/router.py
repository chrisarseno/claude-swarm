"""
Agent Router
Smart routing of tasks to appropriate agents based on capabilities and cost
"""

from typing import List, Optional, Dict, Any
from enum import Enum
import re

from .base import BaseAgent, AgentCapability, AgentProvider


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class TaskComplexity(Enum):
    """Estimated task complexity"""
    SIMPLE = "simple"      # Small edits, simple queries
    MODERATE = "moderate"  # Standard code changes
    COMPLEX = "complex"    # Large refactors, architecture
    VERY_COMPLEX = "very_complex"  # Multi-file changes, complex logic


class AgentRouter:
    """
    Smart router for selecting the best agent for a task.

    Considers:
    - Task requirements (capabilities needed)
    - Cost constraints
    - Performance requirements
    - Model capabilities
    - Agent availability
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agents: List[BaseAgent] = []

        # Routing preferences
        self.prefer_local = self.config.get("prefer_local", False)
        self.cost_threshold = self.config.get("cost_threshold", 0.10)  # $ per task
        self.performance_mode = self.config.get("performance_mode", "balanced")

    def register_agent(self, agent: BaseAgent):
        """Register an agent with the router"""
        self.agents.append(agent)

    def unregister_agent(self, agent_id: str):
        """Remove an agent from the router"""
        self.agents = [a for a in self.agents if a.agent_id != agent_id]

    def analyze_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze a task to determine requirements.

        Returns:
            Dict with required_capabilities, complexity, estimated_tokens
        """
        task_lower = task.lower()
        context = context or {}

        # Detect required capabilities
        required_capabilities = set()

        # Code generation indicators
        if any(word in task_lower for word in [
            "write", "create", "implement", "build", "develop", "generate"
        ]):
            required_capabilities.add(AgentCapability.CODE_GENERATION)

        # Code review indicators
        if any(word in task_lower for word in [
            "review", "analyze", "check", "validate", "audit"
        ]):
            required_capabilities.add(AgentCapability.CODE_REVIEW)

        # Debugging indicators
        if any(word in task_lower for word in [
            "debug", "fix", "bug", "error", "issue", "problem"
        ]):
            required_capabilities.add(AgentCapability.DEBUGGING)

        # Testing indicators
        if any(word in task_lower for word in [
            "test", "testing", "unit test", "integration test"
        ]):
            required_capabilities.add(AgentCapability.TESTING)

        # Documentation indicators
        if any(word in task_lower for word in [
            "document", "documentation", "comment", "docstring", "readme"
        ]):
            required_capabilities.add(AgentCapability.DOCUMENTATION)

        # Refactoring indicators
        if any(word in task_lower for word in [
            "refactor", "optimize", "improve", "restructure", "reorganize"
        ]):
            required_capabilities.add(AgentCapability.REFACTORING)

        # Security indicators
        if any(word in task_lower for word in [
            "security", "vulnerability", "exploit", "injection", "xss"
        ]):
            required_capabilities.add(AgentCapability.SECURITY)

        # Performance indicators
        if any(word in task_lower for word in [
            "performance", "optimize", "speed", "slow", "latency"
        ]):
            required_capabilities.add(AgentCapability.PERFORMANCE)

        # Default to general if no specific capability detected
        if not required_capabilities:
            required_capabilities.add(AgentCapability.GENERAL)

        # Estimate complexity
        complexity = self._estimate_complexity(task, context)

        # Estimate tokens needed
        estimated_tokens = self._estimate_tokens(task, context, complexity)

        return {
            "required_capabilities": list(required_capabilities),
            "complexity": complexity,
            "estimated_tokens": estimated_tokens
        }

    def _estimate_complexity(self, task: str, context: Dict[str, Any]) -> TaskComplexity:
        """Estimate task complexity"""
        # Check for complexity indicators
        task_lower = task.lower()

        # Very complex indicators
        if any(word in task_lower for word in [
            "architecture", "redesign", "migrate", "large refactor",
            "entire system", "all files"
        ]):
            return TaskComplexity.VERY_COMPLEX

        # Complex indicators
        if any(word in task_lower for word in [
            "multiple files", "refactor", "major", "complex"
        ]):
            return TaskComplexity.COMPLEX

        # Simple indicators
        if any(word in task_lower for word in [
            "small", "simple", "quick", "minor", "typo"
        ]):
            return TaskComplexity.SIMPLE

        # Check context size
        file_count = len(context.get("files", []))
        if file_count > 5:
            return TaskComplexity.COMPLEX
        elif file_count > 2:
            return TaskComplexity.MODERATE

        return TaskComplexity.MODERATE

    def _estimate_tokens(
        self,
        task: str,
        context: Dict[str, Any],
        complexity: TaskComplexity
    ) -> int:
        """Estimate total tokens (input + output)"""
        # Count task tokens (rough estimate: 1 token ≈ 4 chars)
        task_tokens = len(task) // 4

        # Count context tokens
        context_tokens = 0
        for file in context.get("files", []):
            context_tokens += len(file.get("content", "")) // 4

        # Estimate output tokens based on complexity
        output_tokens = {
            TaskComplexity.SIMPLE: 500,
            TaskComplexity.MODERATE: 2000,
            TaskComplexity.COMPLEX: 4000,
            TaskComplexity.VERY_COMPLEX: 8000
        }[complexity]

        return task_tokens + context_tokens + output_tokens

    def select_agent(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        cost_limit: Optional[float] = None
    ) -> Optional[BaseAgent]:
        """
        Select the best agent for a task.

        Args:
            task: Task description
            context: Additional context
            priority: Task priority
            cost_limit: Maximum cost in dollars

        Returns:
            Selected agent or None if no suitable agent found
        """
        # Analyze task
        analysis = self.analyze_task(task, context)
        required_capabilities = analysis["required_capabilities"]
        estimated_tokens = analysis["estimated_tokens"]

        # Filter agents by capability
        capable_agents = [
            agent for agent in self.agents
            if agent.is_available and
            all(agent.has_capability(cap) for cap in required_capabilities)
        ]

        if not capable_agents:
            return None

        # Score agents
        scored_agents = []
        for agent in capable_agents:
            score = self._score_agent(
                agent,
                estimated_tokens,
                priority,
                cost_limit
            )
            scored_agents.append((score, agent))

        # Sort by score (higher is better)
        scored_agents.sort(key=lambda x: x[0], reverse=True)

        # Return best agent
        return scored_agents[0][1] if scored_agents else None

    def _score_agent(
        self,
        agent: BaseAgent,
        estimated_tokens: int,
        priority: TaskPriority,
        cost_limit: Optional[float]
    ) -> float:
        """
        Score an agent for a task.

        Higher score = better match.
        """
        score = 0.0

        # Cost scoring
        cost = self._estimate_cost(agent, estimated_tokens)
        if cost_limit and cost > cost_limit:
            return -1000.0  # Exclude if over budget

        # Prefer free/cheap models for low priority
        if priority == TaskPriority.LOW:
            if cost == 0:
                score += 100  # Local models
            elif cost < 0.01:
                score += 50  # Very cheap models
        elif priority == TaskPriority.CRITICAL:
            # Prefer best models regardless of cost
            if agent.provider == AgentProvider.CLAUDE_CODE:
                score += 100
            elif agent.provider == AgentProvider.ANTHROPIC_API:
                score += 90

        # Performance mode scoring
        if self.performance_mode == "fast":
            # Prefer API-based models
            if agent.provider in [AgentProvider.ANTHROPIC_API, AgentProvider.OPENAI]:
                score += 50
        elif self.performance_mode == "cost":
            # Prefer free models
            if cost == 0:
                score += 100
            else:
                score -= cost * 100  # Penalize by cost
        elif self.performance_mode == "quality":
            # Prefer best models
            if agent.provider == AgentProvider.CLAUDE_CODE:
                score += 100
            elif "opus" in agent.model_name.lower():
                score += 90
            elif "gpt-4" in agent.model_name.lower():
                score += 80

        # Context window scoring
        if estimated_tokens > agent.get_context_window():
            return -1000.0  # Exclude if context too large

        # Local preference
        if self.prefer_local and agent.provider == AgentProvider.OLLAMA:
            score += 50

        return score

    def _estimate_cost(self, agent: BaseAgent, estimated_tokens: int) -> float:
        """Estimate cost in dollars for this task"""
        costs = agent.get_cost_per_token()

        # Assume 70% input, 30% output split
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        # Calculate cost (costs are per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]

        return input_cost + output_cost

    def get_available_agents(self) -> List[BaseAgent]:
        """Get all available agents"""
        return [a for a in self.agents if a.is_available]

    def get_agent_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """Get specific agent by ID"""
        for agent in self.agents:
            if agent.agent_id == agent_id:
                return agent
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics"""
        return {
            "total_agents": len(self.agents),
            "available_agents": len(self.get_available_agents()),
            "agents_by_provider": {
                provider.value: len([
                    a for a in self.agents
                    if a.provider == provider
                ])
                for provider in AgentProvider
            },
            "performance_mode": self.performance_mode,
            "prefer_local": self.prefer_local
        }
