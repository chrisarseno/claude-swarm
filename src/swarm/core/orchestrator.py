"""Main orchestrator for Claude Swarm."""

import asyncio
import time
from pathlib import Path
from typing import Optional, Any, Callable
import yaml

from .backend_manager import BackendManager
from .instance_manager import InstanceManager
from .task_queue import TaskQueue, Task, TaskPriority, TaskStatus
from .task_analyzer import TaskAnalyzer
from .swarm_router import SwarmRouter
from ..agents.model_registry import LiveModelRegistry
from ..claude.wrapper import ClaudeCommand
from ..utils.logger import get_logger
from ..utils.config import Config
from ..licensing import license_gate

logger = get_logger(__name__)


class SwarmOrchestrator:
    """Main orchestrator coordinating instances and tasks."""

    def __init__(self, config: Config):
        self.config = config

        # Initialize multi-backend manager
        self.backend_manager = BackendManager(config.swarm.backends)

        # Initialize model registry with backend awareness
        self.model_registry = LiveModelRegistry(
            ollama_url=config.swarm.ollama_url,
            backend_manager=self.backend_manager,
        )

        self.instance_manager = InstanceManager(
            max_instances=config.swarm.max_instances,
            claude_command=config.swarm.claude_command,
            default_working_dir=Path(config.swarm.workspace_root),
            backend=config.swarm.backend.value,
            ollama_url=config.swarm.ollama_url,
            ollama_model=config.swarm.ollama_model,
            model_registry=self.model_registry,
            backend_manager=self.backend_manager,
        )

        self.task_queue = TaskQueue()
        self.task_analyzer = TaskAnalyzer()
        self.swarm_router = SwarmRouter(
            self.model_registry,
            backend_manager=self.backend_manager,
        )
        self._running = False
        self._worker_tasks: list[asyncio.Task] = []

    async def start(self, initial_instances: int = 1) -> None:
        """Start the orchestrator."""
        if self._running:
            logger.warning("orchestrator_already_running")
            return

        logger.info("starting_orchestrator", initial_instances=initial_instances)

        # Start backend health monitoring
        await self.backend_manager.start()

        # Spawn initial instances
        await self.instance_manager.spawn_multiple(initial_instances)

        # Start worker tasks
        self._running = True
        worker_count = min(initial_instances, self.config.swarm.max_instances)

        for i in range(worker_count):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)

        logger.info("orchestrator_started", workers=worker_count,
                     backends=len(self.config.swarm.backends))

    async def stop(self) -> None:
        """Stop the orchestrator."""
        if not self._running:
            return

        logger.info("stopping_orchestrator")

        # Stop workers
        self._running = False
        for task in self._worker_tasks:
            task.cancel()

        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        self._worker_tasks.clear()

        # Terminate all instances
        await self.instance_manager.terminate_all()

        # Stop backend health monitoring
        await self.backend_manager.stop()

        logger.info("orchestrator_stopped")

    async def _worker_loop(self, worker_id: str) -> None:
        """Worker loop that processes tasks with intelligent routing."""
        logger.info("worker_started", worker_id=worker_id)

        while self._running:
            try:
                # Get next task
                task = await self.task_queue.get_next_task()
                if not task:
                    await asyncio.sleep(0.5)
                    continue

                logger.info("worker_processing_task", worker_id=worker_id, task_id=task.id)

                # --- Task Analysis & Routing ---
                analysis = None
                routing_decision = None
                auto_select = getattr(self.config.swarm, "models", None)
                use_routing = (
                    auto_select
                    and getattr(auto_select, "auto_select", False)
                    and self.config.swarm.backend.value == "ollama"
                    and not task.instance_id
                )

                if use_routing:
                    try:
                        analysis = self.task_analyzer.analyze(task.prompt)
                        # Merge config preferred models with metadata preferred_model
                        preferred = list(auto_select.preferred or [])
                        meta_preferred = task.metadata.get("preferred_model")
                        if meta_preferred and meta_preferred not in preferred:
                            preferred.insert(0, meta_preferred)
                        routing_decision = await self.swarm_router.route(
                            analysis=analysis,
                            prefer_speed=task.metadata.get("prefer_speed", False),
                            preferred_models=preferred or None,
                            fallback_model=auto_select.fallback,
                        )
                        logger.info("task_routed", task_id=task.id,
                                     model=routing_decision.model,
                                     backend=routing_decision.backend_name,
                                     score=routing_decision.score,
                                     reason=routing_decision.reason)
                    except Exception as e:
                        logger.warning("routing_failed_using_default", error=str(e))

                # Get an instance
                instance = None
                backend_name = routing_decision.backend_name if routing_decision else None

                if task.instance_id:
                    instance = await self.instance_manager.get_instance(task.instance_id)
                elif routing_decision:
                    # Try to get/spawn an instance with the routed model on the routed backend
                    instance = await self.instance_manager.get_or_spawn_for_model(
                        routing_decision.model,
                        task.working_directory,
                        backend_name=backend_name,
                    )
                if not instance:
                    instance = await self.instance_manager.get_idle_instance()

                if not instance:
                    # Requeue the task
                    task.status = TaskStatus.QUEUED
                    await self.task_queue.pending_queue.put(task.id)
                    await asyncio.sleep(1)
                    continue

                # Acquire backend slot
                acquired = False
                actual_backend = getattr(instance, "backend_name", None) or backend_name
                if actual_backend:
                    acquired = await self.backend_manager.acquire(actual_backend)
                    if not acquired:
                        # Backend is full, requeue
                        task.status = TaskStatus.QUEUED
                        await self.task_queue.pending_queue.put(task.id)
                        await asyncio.sleep(1)
                        continue

                # Execute task
                t0 = time.time()
                try:
                    meta = dict(task.metadata)
                    meta["task_id"] = task.id
                    if analysis:
                        meta["task_type"] = analysis.task_type.value
                        meta["complexity"] = analysis.complexity.value
                    if routing_decision:
                        meta["routed_model"] = routing_decision.model
                        meta["routing_score"] = routing_decision.score
                        meta["routed_backend"] = routing_decision.backend_name

                    command = ClaudeCommand(
                        prompt=task.prompt,
                        working_directory=task.working_directory,
                        timeout=task.timeout,
                        metadata=meta,
                    )

                    result = await instance.execute(command)
                    duration_ms = (time.time() - t0) * 1000

                    # Check if the backend reported an error
                    if result.get("status") == "error":
                        error_msg = result.get("error", "Unknown backend error")
                        logger.warning("task_backend_error", task_id=task.id, error=error_msg)
                        await self.task_queue.fail_task(task.id, error_msg)
                        result["_failed"] = True

                        # Release backend slot with failure
                        if actual_backend:
                            await self.backend_manager.release(
                                actual_backend, success=False,
                                latency_ms=duration_ms, error=error_msg,
                            )
                    else:
                        await self.task_queue.complete_task(task.id, result)

                        # Release backend slot with success
                        if actual_backend:
                            await self.backend_manager.release(
                                actual_backend, success=True,
                                latency_ms=duration_ms,
                            )

                    # Record routing outcome for feedback
                    if routing_decision and analysis:
                        success = result.get("status") == "completed"
                        self.swarm_router.record_outcome(
                            model=routing_decision.model,
                            task_type=analysis.task_type.value,
                            success=success,
                            duration_ms=duration_ms,
                            backend_name=actual_backend,
                        )

                except Exception as e:
                    duration_ms = (time.time() - t0) * 1000
                    logger.error("task_execution_failed", task_id=task.id, error=str(e))
                    await self.task_queue.fail_task(task.id, str(e))

                    # Release backend slot
                    if actual_backend:
                        await self.backend_manager.release(
                            actual_backend, success=False,
                            latency_ms=duration_ms, error=str(e),
                        )

                    if routing_decision and analysis:
                        self.swarm_router.record_outcome(
                            model=routing_decision.model,
                            task_type=analysis.task_type.value,
                            success=False,
                            duration_ms=duration_ms,
                            backend_name=actual_backend,
                        )

            except asyncio.CancelledError:
                logger.info("worker_cancelled", worker_id=worker_id)
                break
            except Exception as e:
                logger.error("worker_error", worker_id=worker_id, error=str(e))
                await asyncio.sleep(1)

        logger.info("worker_stopped", worker_id=worker_id)

    async def ensure_workers(self, count: int) -> int:
        """Ensure at least `count` workers are running."""
        current = len(self._worker_tasks)
        if count <= current:
            return current
        for i in range(current, count):
            task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._worker_tasks.append(task)
        logger.info("workers_scaled", previous=current, current=len(self._worker_tasks))
        return len(self._worker_tasks)

    async def submit_task(
        self,
        prompt: str,
        name: Optional[str] = None,
        working_directory: Optional[Path] = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = None,
        instance_id: Optional[str] = None,
        depends_on: Optional[list[str]] = None,
        metadata: Optional[dict[str, Any]] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """Submit a task to the queue."""
        task = Task(
            name=name or prompt[:50],
            prompt=prompt,
            working_directory=working_directory,
            priority=priority,
            timeout=timeout or self.config.swarm.default_timeout,
            instance_id=instance_id,
            depends_on=depends_on or [],
            metadata=metadata or {},
            callback=callback
        )

        task_id = await self.task_queue.add_task(task)
        logger.info("task_submitted", task_id=task_id, name=task.name)
        return task_id

    async def submit_batch(
        self,
        prompts: list[str],
        working_directory: Optional[Path] = None,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> list[str]:
        """Submit multiple tasks at once."""
        license_gate.gate("std.swarm.advanced")
        task_ids = []
        for prompt in prompts:
            task_id = await self.submit_task(
                prompt=prompt,
                working_directory=working_directory,
                priority=priority
            )
            task_ids.append(task_id)

        logger.info("batch_submitted", count=len(task_ids))
        return task_ids

    async def execute_workflow(self, workflow_path: Path) -> dict[str, Any]:
        """Execute a workflow from a YAML file."""
        license_gate.gate("std.swarm.advanced")
        logger.info("executing_workflow", path=str(workflow_path))

        with open(workflow_path, "r") as f:
            workflow = yaml.safe_load(f)

        workflow_name = workflow.get("name", "unnamed")
        tasks = workflow.get("tasks", [])
        required_instances = workflow.get("instances", 1)

        # Ensure we have enough instances
        await self.instance_manager.scale_to(required_instances)

        # Submit tasks
        task_mapping = {}  # workflow task name -> queue task id

        for task_def in tasks:
            depends_on_names = task_def.get("depends_on", [])
            depends_on_ids = [task_mapping.get(name) for name in depends_on_names if name in task_mapping]

            task_id = await self.submit_task(
                name=task_def["name"],
                prompt=task_def.get("command", task_def.get("prompt", "")),
                working_directory=Path(task_def["directory"]) if "directory" in task_def else None,
                instance_id=task_def.get("instance"),
                depends_on=depends_on_ids,
                metadata={"workflow": workflow_name}
            )

            task_mapping[task_def["name"]] = task_id

        logger.info("workflow_submitted", name=workflow_name, tasks=len(task_mapping))

        return {
            "workflow_name": workflow_name,
            "task_ids": list(task_mapping.values()),
            "task_mapping": task_mapping
        }

    async def get_status(self) -> dict[str, Any]:
        """Get overall swarm status."""
        instance_stats = await self.instance_manager.get_stats()
        queue_stats = await self.task_queue.get_queue_stats()

        return {
            "running": self._running,
            "workers": len(self._worker_tasks),
            "instances": instance_stats,
            "tasks": queue_stats,
            "backends": self.backend_manager.get_status(),
        }

    async def scale_instances(self, target: int) -> int:
        """Scale the number of instances."""
        license_gate.gate("std.swarm.advanced")
        current = len(self.instance_manager.instances)
        result = await self.instance_manager.scale_to(target)
        logger.info("scaled_instances", from_count=current, to_count=result, target=target)
        return result

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task."""
        return await self.task_queue.cancel_task(task_id)

    async def get_task_status(self, task_id: str) -> Optional[dict[str, Any]]:
        """Get status of a specific task."""
        task = await self.task_queue.get_task(task_id)
        return task.get_info(include_result=True) if task else None

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List tasks."""
        return await self.task_queue.list_tasks(status, limit)

    async def list_instances(self) -> list[dict[str, Any]]:
        """List all instances."""
        return await self.instance_manager.list_instances()

    async def get_instance_output(
        self,
        instance_id: str,
        lines: int = 50
    ) -> Optional[list[str]]:
        """Get recent output from an instance."""
        instance = await self.instance_manager.get_instance(instance_id)
        return instance.get_recent_output(lines) if instance else None
