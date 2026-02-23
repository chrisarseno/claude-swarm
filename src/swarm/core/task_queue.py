"""Task queue management for Claude Swarm."""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Any, Callable

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Represents a task to be executed."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    prompt: str = ""
    working_directory: Optional[Path] = None
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300
    status: TaskStatus = TaskStatus.PENDING
    instance_id: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    callback: Optional[Callable[[dict], None]] = None

    def get_info(self, include_result: bool = False) -> dict[str, Any]:
        """Get task information as dictionary."""
        info = {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt[:100] if self.prompt else "",
            "status": self.status.value,
            "priority": self.priority.value,
            "instance_id": self.instance_id,
            "depends_on": self.depends_on,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.started_at and self.completed_at
                else None
            ),
            "error": self.error,
            "metadata": self.metadata
        }
        if include_result and self.result:
            info["result"] = self.result
        return info


class TaskQueue:
    """Manages task queue and scheduling."""

    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.pending_queue: asyncio.Queue = asyncio.Queue()
        self.completed_tasks: list[str] = []
        self._lock = asyncio.Lock()

    async def add_task(self, task: Task) -> str:
        """Add a task to the queue."""
        async with self._lock:
            self.tasks[task.id] = task

            # Check if dependencies are met
            if await self._dependencies_met(task):
                task.status = TaskStatus.QUEUED
                await self.pending_queue.put(task.id)
                logger.info("task_queued", task_id=task.id, name=task.name)
            else:
                task.status = TaskStatus.PENDING
                logger.info("task_pending_dependencies", task_id=task.id, depends_on=task.depends_on)

            return task.id

    async def get_next_task(self) -> Optional[Task]:
        """Get the next task from the queue."""
        try:
            # Get highest priority task
            task_id = await asyncio.wait_for(self.pending_queue.get(), timeout=0.1)
            async with self._lock:
                if task_id in self.tasks:
                    task = self.tasks[task_id]
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now()
                    logger.info("task_started", task_id=task.id, name=task.name)
                    return task
        except asyncio.TimeoutError:
            pass
        return None

    async def complete_task(self, task_id: str, result: dict[str, Any]) -> None:
        """Mark a task as completed."""
        async with self._lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            self.completed_tasks.append(task_id)

            logger.info("task_completed", task_id=task_id, name=task.name)

            # Trigger callback if provided
            if task.callback:
                try:
                    task.callback(result)
                except Exception as e:
                    logger.error("task_callback_failed", task_id=task_id, error=str(e))

            # Check for tasks waiting on this one
            await self._check_dependent_tasks(task_id)

    async def fail_task(self, task_id: str, error: str) -> None:
        """Mark a task as failed."""
        async with self._lock:
            if task_id not in self.tasks:
                return

            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = error

            logger.error("task_failed", task_id=task_id, name=task.name, error=error)

            # Trigger callback if provided
            if task.callback:
                try:
                    task.callback({"status": "failed", "error": error})
                except Exception as e:
                    logger.error("task_callback_failed", task_id=task_id, error=str(e))

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or queued task."""
        async with self._lock:
            if task_id not in self.tasks:
                return False

            task = self.tasks[task_id]
            if task.status in [TaskStatus.PENDING, TaskStatus.QUEUED]:
                task.status = TaskStatus.CANCELLED
                logger.info("task_cancelled", task_id=task_id, name=task.name)
                return True

            return False

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List tasks with optional filtering."""
        async with self._lock:
            tasks = list(self.tasks.values())

            if status:
                tasks = [t for t in tasks if t.status == status]

            # Sort by priority and creation time
            tasks.sort(
                key=lambda t: (t.priority.value, t.created_at),
                reverse=True
            )

            return [t.get_info() for t in tasks[:limit]]

    async def get_queue_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        async with self._lock:
            status_counts = {}
            for task in self.tasks.values():
                status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1

            return {
                "total_tasks": len(self.tasks),
                "queued": self.pending_queue.qsize(),
                "completed": len(self.completed_tasks),
                "by_status": status_counts
            }

    async def _dependencies_met(self, task: Task) -> bool:
        """Check if task dependencies are met."""
        if not task.depends_on:
            return True

        for dep_id in task.depends_on:
            if dep_id not in self.completed_tasks:
                return False

        return True

    async def _check_dependent_tasks(self, completed_task_id: str) -> None:
        """Check if any pending tasks can now be queued."""
        for task in self.tasks.values():
            if (
                task.status == TaskStatus.PENDING
                and completed_task_id in task.depends_on
                and await self._dependencies_met(task)
            ):
                task.status = TaskStatus.QUEUED
                await self.pending_queue.put(task.id)
                logger.info("task_queued_after_dependency", task_id=task.id, name=task.name)

    def clear_completed(self) -> int:
        """Remove completed tasks from memory."""
        count = 0
        to_remove = [
            task_id for task_id, task in self.tasks.items()
            if task.status == TaskStatus.COMPLETED
        ]
        for task_id in to_remove:
            del self.tasks[task_id]
            count += 1
        return count
