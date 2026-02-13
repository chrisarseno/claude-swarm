"""Instance pool management for Claude Swarm."""

import asyncio
from pathlib import Path
from typing import Optional, Any

from ..claude.wrapper import ClaudeInstance, ClaudeCommand, InstanceStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class InstanceManager:
    """Manages a pool of Claude Code instances across multiple backends."""

    def __init__(
        self,
        max_instances: int = 5,
        claude_command: str = "claude",
        default_working_dir: Optional[Path] = None,
        backend: str = "claude",
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "devstral:24b",
        model_registry=None,
        backend_manager=None,
    ):
        self.max_instances = max_instances
        self.claude_command = claude_command
        self.default_working_dir = default_working_dir or Path.cwd()
        self.backend = backend
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.model_registry = model_registry  # LiveModelRegistry (optional)
        self.backend_manager = backend_manager  # BackendManager (optional)
        self.instances: dict[str, ClaudeInstance] = {}
        self._lock = asyncio.Lock()

    async def spawn_instance(
        self,
        working_directory: Optional[Path] = None
    ) -> Optional[ClaudeInstance]:
        """Spawn a new Claude instance."""
        async with self._lock:
            if len(self.instances) >= self.max_instances:
                logger.warning("max_instances_reached", max=self.max_instances)
                return None

            instance = ClaudeInstance(
                working_directory=working_directory or self.default_working_dir,
                backend=self.backend,
                ollama_url=self.ollama_url,
                ollama_model=self.ollama_model,
            )

            if await instance.start(self.claude_command):
                self.instances[instance.id] = instance
                logger.info("instance_spawned", instance_id=instance.id, total=len(self.instances))
                return instance

            return None

    async def spawn_multiple(
        self,
        count: int,
        working_directory: Optional[Path] = None
    ) -> list[ClaudeInstance]:
        """Spawn multiple instances."""
        instances = []
        available_slots = self.max_instances - len(self.instances)
        spawn_count = min(count, available_slots)

        logger.info("spawning_multiple_instances", count=spawn_count)

        tasks = [
            self.spawn_instance(working_directory)
            for _ in range(spawn_count)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, ClaudeInstance):
                instances.append(result)
            elif isinstance(result, Exception):
                logger.error("failed_to_spawn_instance", error=str(result))

        logger.info("instances_spawned", count=len(instances), total=len(self.instances))
        return instances

    async def get_instance(self, instance_id: str) -> Optional[ClaudeInstance]:
        """Get an instance by ID."""
        return self.instances.get(instance_id)

    async def get_idle_instance(self) -> Optional[ClaudeInstance]:
        """Get an idle instance from the pool."""
        async with self._lock:
            for instance in self.instances.values():
                if instance.status == InstanceStatus.IDLE:
                    return instance
            return None

    async def execute_on_instance(
        self,
        instance_id: str,
        command: ClaudeCommand
    ) -> dict[str, Any]:
        """Execute a command on a specific instance."""
        instance = await self.get_instance(instance_id)
        if not instance:
            raise ValueError(f"Instance {instance_id} not found")

        return await instance.execute(command)

    async def execute_on_any(self, command: ClaudeCommand) -> Optional[dict[str, Any]]:
        """Execute a command on any available instance."""
        # Try to get an idle instance
        instance = await self.get_idle_instance()

        if not instance:
            # Try to spawn a new one
            logger.info("no_idle_instance_spawning_new")
            instance = await self.spawn_instance(command.working_directory)

        if not instance:
            logger.warning("no_instance_available")
            return None

        return await instance.execute(command)

    async def terminate_instance(self, instance_id: str) -> bool:
        """Terminate a specific instance."""
        async with self._lock:
            instance = self.instances.get(instance_id)
            if not instance:
                return False

            await instance.stop()
            del self.instances[instance_id]
            logger.info("instance_terminated", instance_id=instance_id, remaining=len(self.instances))
            return True

    async def terminate_all(self) -> int:
        """Terminate all instances."""
        logger.info("terminating_all_instances", count=len(self.instances))

        tasks = [
            instance.stop()
            for instance in self.instances.values()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        count = len(self.instances)
        self.instances.clear()

        logger.info("all_instances_terminated", count=count)
        return count

    async def list_instances(self) -> list[dict[str, Any]]:
        """List all instances and their status."""
        return [
            instance.get_info()
            for instance in self.instances.values()
        ]

    async def get_stats(self) -> dict[str, Any]:
        """Get instance pool statistics."""
        status_counts = {}
        for instance in self.instances.values():
            status = instance.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        total_completed = sum(i.completed_tasks for i in self.instances.values())
        total_errors = sum(i.error_count for i in self.instances.values())

        return {
            "total_instances": len(self.instances),
            "max_instances": self.max_instances,
            "available_slots": self.max_instances - len(self.instances),
            "by_status": status_counts,
            "total_completed_tasks": total_completed,
            "total_errors": total_errors
        }

    async def scale_to(self, target_count: int) -> int:
        """Scale the instance pool to a target size."""
        current_count = len(self.instances)

        if target_count > current_count:
            # Scale up
            to_spawn = min(target_count - current_count, self.max_instances - current_count)
            await self.spawn_multiple(to_spawn)
            return len(self.instances)

        elif target_count < current_count:
            # Scale down - terminate idle instances first
            async with self._lock:
                idle_instances = [
                    i for i in self.instances.values()
                    if i.status == InstanceStatus.IDLE
                ]

                to_terminate = current_count - target_count
                for instance in idle_instances[:to_terminate]:
                    await instance.stop()
                    del self.instances[instance.id]

            return len(self.instances)

        return current_count

    async def spawn_instance_with_model(
        self,
        model: str,
        working_directory: Optional[Path] = None,
        backend_name: Optional[str] = None,
    ) -> Optional[ClaudeInstance]:
        """Spawn an instance using a specific Ollama model, optionally on a specific backend."""
        async with self._lock:
            if len(self.instances) >= self.max_instances:
                logger.warning("max_instances_reached", max=self.max_instances)
                return None

            # Resolve backend URL
            ollama_url = self.ollama_url
            if backend_name and self.backend_manager:
                state = self.backend_manager.get_backend(backend_name)
                if state:
                    ollama_url = state.config.url

            instance = ClaudeInstance(
                working_directory=working_directory or self.default_working_dir,
                backend="ollama",
                ollama_url=ollama_url,
                ollama_model=model,
                backend_name=backend_name or "local",
            )

            if await instance.start(self.claude_command):
                self.instances[instance.id] = instance
                logger.info("instance_spawned_with_model", instance_id=instance.id,
                            model=model, backend=backend_name,
                            total=len(self.instances))
                return instance

            return None

    async def get_or_spawn_for_model(
        self,
        model: str,
        working_directory: Optional[Path] = None,
        backend_name: Optional[str] = None,
    ) -> Optional[ClaudeInstance]:
        """Get an idle instance running the specified model, or spawn one."""
        # Check for existing idle instance with this model (and backend if specified)
        async with self._lock:
            for instance in self.instances.values():
                if instance.status != InstanceStatus.IDLE:
                    continue
                if instance.ollama_model != model:
                    continue
                if backend_name and getattr(instance, "backend_name", None) != backend_name:
                    continue
                return instance

        # Spawn a new one
        return await self.spawn_instance_with_model(model, working_directory, backend_name)

    async def health_check(self) -> dict[str, Any]:
        """Check health of all instances."""
        healthy = []
        unhealthy = []

        for instance in self.instances.values():
            if instance.status == InstanceStatus.ERROR:
                unhealthy.append(instance.id)
            else:
                healthy.append(instance.id)

        return {
            "healthy": healthy,
            "unhealthy": unhealthy,
            "total": len(self.instances)
        }
