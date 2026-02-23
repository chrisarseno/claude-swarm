"""Basic tests for Claude Swarm."""

import pytest
import asyncio
from pathlib import Path

from swarm.core.orchestrator import SwarmOrchestrator
from swarm.core.task_queue import TaskQueue, Task, TaskPriority, TaskStatus
from swarm.core.instance_manager import InstanceManager
from swarm.utils.config import Config


class TestTaskQueue:
    """Test task queue functionality."""

    @pytest.mark.asyncio
    async def test_add_task(self):
        """Test adding a task to the queue."""
        queue = TaskQueue()
        task = Task(
            name="Test Task",
            prompt="Test prompt",
            priority=TaskPriority.NORMAL
        )

        task_id = await queue.add_task(task)
        assert task_id == task.id
        assert task.id in queue.tasks

    @pytest.mark.asyncio
    async def test_task_dependencies(self):
        """Test task dependencies."""
        queue = TaskQueue()

        # Add first task
        task1 = Task(name="Task 1", prompt="First")
        task1_id = await queue.add_task(task1)

        # Add dependent task
        task2 = Task(name="Task 2", prompt="Second", depends_on=[task1_id])
        task2_id = await queue.add_task(task2)

        # Task 1 should be queued, Task 2 should be pending
        assert queue.tasks[task1_id].status == TaskStatus.QUEUED
        assert queue.tasks[task2_id].status == TaskStatus.PENDING

        # Complete Task 1
        await queue.complete_task(task1_id, {"result": "done"})

        # Task 2 should now be queued
        assert queue.tasks[task2_id].status == TaskStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_next_task(self):
        """Test getting next task from queue."""
        queue = TaskQueue()

        task = Task(name="Test", prompt="Test")
        await queue.add_task(task)

        next_task = await queue.get_next_task()
        assert next_task is not None
        assert next_task.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a task."""
        queue = TaskQueue()

        task = Task(name="Test", prompt="Test")
        task_id = await queue.add_task(task)

        success = await queue.cancel_task(task_id)
        assert success is True
        assert queue.tasks[task_id].status == TaskStatus.CANCELLED


class TestInstanceManager:
    """Test instance manager functionality."""

    @pytest.mark.asyncio
    async def test_spawn_instance(self):
        """Test spawning an instance."""
        manager = InstanceManager(max_instances=5)

        # Note: This will try to actually spawn Claude Code
        # In real tests, you'd want to mock this
        # instance = await manager.spawn_instance()
        # assert instance is not None
        # assert instance.id in manager.instances

        # For now, just test the structure
        assert manager.max_instances == 5
        assert len(manager.instances) == 0

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting instance stats."""
        manager = InstanceManager(max_instances=10)

        stats = await manager.get_stats()
        assert stats['total_instances'] == 0
        assert stats['max_instances'] == 10
        assert stats['available_slots'] == 10


class TestOrchestrator:
    """Test orchestrator functionality."""

    @pytest.mark.asyncio
    async def test_create_orchestrator(self):
        """Test creating an orchestrator."""
        config = Config()
        orchestrator = SwarmOrchestrator(config)

        assert orchestrator is not None
        assert orchestrator.config == config
        assert orchestrator._running is False

    @pytest.mark.asyncio
    async def test_submit_task(self):
        """Test submitting a task."""
        config = Config()
        orchestrator = SwarmOrchestrator(config)

        # Don't actually start instances for unit test
        task_id = await orchestrator.submit_task(
            prompt="Test task",
            priority=TaskPriority.NORMAL
        )

        assert task_id is not None
        task = await orchestrator.task_queue.get_task(task_id)
        assert task is not None
        assert task.prompt == "Test task"


class TestConfig:
    """Test configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = Config()

        assert config.swarm.max_instances == 10
        assert config.swarm.default_timeout == 300
        assert config.api.port == 8766
        assert config.logging.level == "INFO"

    def test_config_from_dict(self):
        """Test creating config from dict."""
        config = Config(
            swarm={"max_instances": 5, "default_timeout": 600},
            api={"port": 9000}
        )

        assert config.swarm.max_instances == 5
        assert config.swarm.default_timeout == 600
        assert config.api.port == 9000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
