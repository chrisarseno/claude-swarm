"""Claude Swarm - Multi-instance orchestration for Claude Code."""

__version__ = "0.1.0"
__author__ = "Claude Swarm Contributors"

from .core.orchestrator import SwarmOrchestrator
from .core.instance_manager import InstanceManager
from .core.task_queue import TaskQueue

__all__ = ["SwarmOrchestrator", "InstanceManager", "TaskQueue"]
