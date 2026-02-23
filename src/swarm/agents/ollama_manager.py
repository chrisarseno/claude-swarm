"""
Ollama Manager
Manages Ollama models - pulling, listing, health checks, and orchestration
"""

import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
import logging

from .ollama_registry import (
    OLLAMA_MODELS,
    ModelProfile,
    get_model_profile,
    recommend_model_for_task
)
from .ollama_agent import OllamaAgent
from .base import AgentCapability

logger = logging.getLogger(__name__)


class OllamaManager:
    """
    Manages a fleet of Ollama models.

    Features:
    - Automatic model pulling
    - Health monitoring
    - Model recommendations
    - Agent pool management
    - Resource optimization
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        auto_pull: bool = True,
        max_concurrent_pulls: int = 1
    ):
        self.ollama_url = ollama_url
        self.auto_pull = auto_pull
        self.max_concurrent_pulls = max_concurrent_pulls
        self.agents: Dict[str, OllamaAgent] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        """Initialize the manager"""
        self._session = aiohttp.ClientSession()

        # Check if Ollama is running
        if not await self.is_ollama_running():
            raise ConnectionError(
                f"Ollama not accessible at {self.ollama_url}. "
                "Is Ollama installed and running?"
            )

        logger.info("Ollama manager initialized")

    async def cleanup(self):
        """Cleanup resources"""
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()

        if self._session:
            await self._session.close()

    async def is_ollama_running(self) -> bool:
        """Check if Ollama is running"""
        try:
            async with self._session.get(f"{self.ollama_url}/api/tags") as resp:
                return resp.status == 200
        except Exception:
            return False

    async def list_installed_models(self) -> List[Dict[str, Any]]:
        """List models currently installed in Ollama"""
        try:
            async with self._session.get(f"{self.ollama_url}/api/tags") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("models", [])
                return []
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def is_model_installed(self, model_name: str) -> bool:
        """Check if a model is installed"""
        models = await self.list_installed_models()
        model_names = [m["name"] for m in models]

        # Check exact match and with :latest tag
        return (
            model_name in model_names or
            f"{model_name}:latest" in model_names or
            any(m.startswith(f"{model_name}:") for m in model_names)
        )

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama registry.

        Args:
            model_name: Model name (e.g., "deepseek-coder:6.7b")

        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling model: {model_name}")

            async with self._session.post(
                f"{self.ollama_url}/api/pull",
                json={"name": model_name}
            ) as resp:
                if resp.status != 200:
                    logger.error(f"Failed to pull {model_name}: {resp.status}")
                    return False

                # Stream progress (Ollama sends multiple JSON objects)
                async for line in resp.content:
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            status = data.get("status", "")

                            # Log significant progress
                            if "pulling" in status.lower():
                                logger.info(f"  {status}")
                            elif "success" in status.lower():
                                logger.info(f"✓ {model_name} pulled successfully")
                                return True
                        except json.JSONDecodeError:
                            pass

            return True

        except Exception as e:
            logger.error(f"Error pulling {model_name}: {e}")
            return False

    async def ensure_model(self, model_name: str) -> bool:
        """
        Ensure a model is installed, pulling if necessary.

        Args:
            model_name: Model name

        Returns:
            True if model is available
        """
        if await self.is_model_installed(model_name):
            logger.info(f"Model {model_name} already installed")
            return True

        if self.auto_pull:
            logger.info(f"Model {model_name} not found, pulling...")
            return await self.pull_model(model_name)
        else:
            logger.warning(
                f"Model {model_name} not installed and auto_pull disabled"
            )
            return False

    async def setup_recommended_models(
        self,
        max_vram_gb: int = 8,
        count: int = 5
    ) -> List[str]:
        """
        Setup recommended models based on available VRAM.

        Args:
            max_vram_gb: Available VRAM in GB
            count: Number of models to setup

        Returns:
            List of installed model names
        """
        logger.info(f"Setting up models for {max_vram_gb}GB VRAM...")

        # Get recommendations based on VRAM
        recommendations = []

        # Categorize by use case
        use_cases = {
            "fast_simple": {"prefer_speed": True, "task": "simple coding task"},
            "balanced": {"task": "general coding"},
            "quality": {"prefer_quality": True, "task": "complex refactoring"},
            "sql": {"task": "sql query optimization"},
            "python": {"task": "python code generation"},
            "debugging": {"task": "debug this error"}
        }

        installed = []

        # Get diverse set of models
        seen_models = set()
        for use_case, kwargs in use_cases.items():
            models = recommend_model_for_task(max_vram_gb=max_vram_gb, **kwargs)

            for profile in models:
                model_key = f"{profile.name}:{profile.params.lower()}"

                if model_key not in seen_models:
                    seen_models.add(model_key)
                    recommendations.append((use_case, profile))

                if len(recommendations) >= count:
                    break

            if len(recommendations) >= count:
                break

        # Install models
        for use_case, profile in recommendations[:count]:
            model_name = f"{profile.name}:{profile.params.lower()}"
            quant = profile.recommended_quant.value

            # Try with quantization suffix
            full_name = f"{model_name}-{quant}"

            logger.info(f"Installing {full_name} for {use_case}...")

            if await self.ensure_model(model_name):
                installed.append(model_name)
                logger.info(f"✓ {model_name} ready ({profile.description})")
            else:
                logger.warning(f"✗ Failed to install {model_name}")

        return installed

    async def create_agent(
        self,
        model_name: str,
        agent_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[OllamaAgent]:
        """
        Create an Ollama agent for a model.

        Args:
            model_name: Model name
            agent_id: Agent ID (auto-generated if None)
            config: Agent configuration

        Returns:
            OllamaAgent instance or None if failed
        """
        # Ensure model is available
        if not await self.ensure_model(model_name):
            logger.error(f"Cannot create agent: model {model_name} unavailable")
            return None

        # Generate agent ID
        if not agent_id:
            agent_id = f"ollama-{model_name.replace(':', '-')}-{len(self.agents)}"

        # Create agent
        agent = OllamaAgent(
            agent_id=agent_id,
            model_name=model_name,
            ollama_url=self.ollama_url,
            config=config or {}
        )

        # Start agent
        if await agent.start():
            self.agents[agent_id] = agent
            logger.info(f"✓ Agent {agent_id} created")
            return agent
        else:
            logger.error(f"✗ Failed to start agent {agent_id}")
            return None

    async def create_specialized_pool(
        self,
        max_vram_gb: int = 8
    ) -> Dict[str, List[OllamaAgent]]:
        """
        Create a pool of specialized agents.

        Returns:
            Dict mapping capability to list of agents
        """
        logger.info("Creating specialized agent pool...")

        pool = {
            "fast": [],      # Fast models for simple tasks
            "balanced": [],  # Balanced models for general tasks
            "quality": [],   # High-quality models for complex tasks
            "sql": [],       # SQL specialists
            "python": [],    # Python specialists
            "debug": []      # Debugging specialists
        }

        # Define model selections
        selections = []

        if max_vram_gb >= 24:
            # High VRAM - use large models
            selections = [
                ("fast", "deepseek-coder:1.3b"),
                ("balanced", "deepseek-coder:6.7b"),
                ("quality", "deepseek-coder:33b"),
                ("quality", "codellama:34b"),
                ("sql", "sqlcoder:7b"),
                ("python", "wizardcoder-python:7b"),
                ("debug", "phind-codellama:34b")
            ]
        elif max_vram_gb >= 12:
            # Medium VRAM - use medium models
            selections = [
                ("fast", "deepseek-coder:1.3b"),
                ("balanced", "deepseek-coder:6.7b"),
                ("balanced", "codellama:7b"),
                ("quality", "codellama:13b"),
                ("sql", "sqlcoder:7b"),
                ("python", "wizardcoder-python:7b"),
                ("debug", "wizardcoder:13b")
            ]
        else:
            # Low VRAM - use small models
            selections = [
                ("fast", "deepseek-coder:1.3b"),
                ("balanced", "deepseek-coder:6.7b"),
                ("balanced", "codellama:7b"),
                ("quality", "wizardcoder:7b"),
                ("python", "wizardcoder-python:7b"),
                ("debug", "mistral:7b")
            ]

        # Create agents
        for category, model_name in selections:
            agent = await self.create_agent(model_name)
            if agent:
                pool[category].append(agent)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Specialized Agent Pool Created:")
        logger.info("=" * 60)
        for category, agents in pool.items():
            if agents:
                models = ", ".join([a.model_name for a in agents])
                logger.info(f"  {category.upper()}: {models}")
        logger.info("=" * 60)

        return pool

    async def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about installed models"""
        models = await self.list_installed_models()

        total_size = 0
        model_info = []

        for model in models:
            size_bytes = model.get("size", 0)
            size_gb = size_bytes / (1024 ** 3)
            total_size += size_gb

            model_info.append({
                "name": model["name"],
                "size_gb": round(size_gb, 2),
                "modified": model.get("modified_at", "unknown")
            })

        return {
            "total_models": len(models),
            "total_size_gb": round(total_size, 2),
            "models": model_info,
            "active_agents": len(self.agents)
        }

    async def benchmark_model(
        self,
        model_name: str,
        test_prompt: str = "Write a Python function to sort a list"
    ) -> Dict[str, Any]:
        """
        Benchmark a model's performance.

        Returns:
            Dict with timing and token statistics
        """
        import time

        # Ensure model
        if not await self.ensure_model(model_name):
            return {"error": "Model not available"}

        # Create temporary agent
        agent = OllamaAgent(
            agent_id=f"bench-{model_name}",
            model_name=model_name,
            ollama_url=self.ollama_url
        )

        await agent.start()

        # Run benchmark
        start_time = time.time()
        result = await agent.execute(test_prompt)
        end_time = time.time()

        await agent.stop()

        if result["success"]:
            duration = end_time - start_time
            output_length = len(result["output"])
            usage = result.get("usage", {})

            tokens_per_sec = usage.get("output_tokens", 0) / duration if duration > 0 else 0

            return {
                "model": model_name,
                "duration_seconds": round(duration, 2),
                "output_length": output_length,
                "tokens_generated": usage.get("output_tokens", 0),
                "tokens_per_second": round(tokens_per_sec, 2),
                "success": True
            }
        else:
            return {
                "model": model_name,
                "error": result["error"],
                "success": False
            }

    async def compare_models(
        self,
        model_names: List[str],
        test_prompt: str = "Write a Python function to calculate fibonacci"
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple models on the same prompt.

        Returns:
            List of benchmark results
        """
        results = []

        logger.info(f"\nBenchmarking {len(model_names)} models...")
        logger.info(f"Prompt: {test_prompt}\n")

        for model_name in model_names:
            logger.info(f"Testing {model_name}...")
            result = await self.benchmark_model(model_name, test_prompt)
            results.append(result)

            if result.get("success"):
                logger.info(
                    f"  ✓ {result['duration_seconds']}s, "
                    f"{result['tokens_per_second']} tokens/sec"
                )
            else:
                logger.info(f"  ✗ {result.get('error', 'Failed')}")

        return results


async def setup_local_swarm(max_vram_gb: int = 8) -> OllamaManager:
    """
    Quick setup for local-first Claude Swarm.

    Args:
        max_vram_gb: Available VRAM

    Returns:
        Configured OllamaManager
    """
    # CLI output - interactive terminal display for setup wizard
    print("\n" + "=" * 70)
    print("CLAUDE SWARM - LOCAL-FIRST SETUP")
    print("=" * 70)
    print(f"\nConfiguring for {max_vram_gb}GB VRAM...")

    manager = OllamaManager(auto_pull=True)
    await manager.initialize()

    # Check Ollama
    if not await manager.is_ollama_running():
        print("\n❌ Ollama is not running!")
        print("Please install and start Ollama:")
        print("  https://ollama.ai\n")
        return None

    print("✓ Ollama is running\n")

    # Setup recommended models
    print("Installing recommended models...\n")
    installed = await manager.setup_recommended_models(
        max_vram_gb=max_vram_gb,
        count=5
    )

    print(f"\n✓ Installed {len(installed)} models")

    # Create specialized pool
    print("\nCreating specialized agent pool...")
    pool = await manager.create_specialized_pool(max_vram_gb)

    total_agents = sum(len(agents) for agents in pool.values())
    print(f"\n✓ Created {total_agents} specialized agents")

    print("\n" + "=" * 70)
    print("LOCAL SWARM READY!")
    print("=" * 70)
    print("\nYou now have a fleet of specialized local models")
    print("running for FREE with complete privacy!\n")

    return manager
