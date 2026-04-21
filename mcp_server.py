#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2024-2026 Chris Arsenault / 1450 Enterprises LLC
"""MCP Server for Claude Swarm.

Exposes Claude Swarm orchestration as MCP tools for Claude Code and other
MCP clients. Implemented with FastMCP — the protocol envelope (JSON-RPC 2.0,
initialize / notifications / shutdown) is handled by the SDK.

Run via: python mcp_server.py  (stdio transport, invoked by Claude Code)
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

# Add src to path so the swarm package is importable when invoked as a script.
sys.path.insert(0, str(Path(__file__).parent / "src"))

from swarm.core.orchestrator import SwarmOrchestrator
from swarm.core.task_queue import TaskPriority, TaskStatus
from swarm.utils.config import Config, load_config
from swarm.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

mcp = FastMCP("claude-swarm", json_response=True)

# ---------------------------------------------------------------------------
# Orchestrator — lazy singleton, initialised on first tool call
# ---------------------------------------------------------------------------
_orchestrator: Optional[SwarmOrchestrator] = None
_orchestrator_lock = asyncio.Lock()


async def get_orchestrator() -> SwarmOrchestrator:
    global _orchestrator
    if _orchestrator is not None:
        return _orchestrator

    async with _orchestrator_lock:
        if _orchestrator is not None:
            return _orchestrator

        config_path = Path(__file__).parent / "config" / "swarm.yaml"
        config = load_config(config_path if config_path.exists() else None)
        setup_logging(level=config.logging.level)

        _orchestrator = SwarmOrchestrator(config)
        await _orchestrator.start(initial_instances=2)
        logger.info("orchestrator_started")
        return _orchestrator


def _format(data: Any) -> str:
    """Return a JSON string for MCP text content."""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, default=str, indent=2)
    except (TypeError, ValueError):
        return str(data)


_PRIORITY_MAP = {
    "low": TaskPriority.LOW,
    "normal": TaskPriority.NORMAL,
    "high": TaskPriority.HIGH,
    "critical": TaskPriority.CRITICAL,
}


# ══════════════════════════════════════════════════════════════════════════
# MCP Tools
# ══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def swarm_spawn_instances(count: int, working_directory: str = "") -> str:
    """Spawn new Claude Code instances in the swarm.

    Use this to add more parallel processing capacity.

    Args:
        count: Number of instances to spawn (1-10).
        working_directory: Optional working directory for the instances.
    """
    try:
        orch = await get_orchestrator()
        working_dir = Path(working_directory) if working_directory else None
        instances = await orch.instance_manager.spawn_multiple(count, working_dir)
        return _format({
            "success": True,
            "spawned": len(instances),
            "instances": [i.get_info() for i in instances],
        })
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_spawn_instances", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_submit_task(
    prompt: str,
    name: str = "",
    priority: str = "normal",
    working_directory: str = "",
    depends_on: Optional[list[str]] = None,
) -> str:
    """Submit a task to the swarm for execution.

    The task will be assigned to an available Claude instance.

    Args:
        prompt: The task prompt / instruction to send to a Claude instance.
        name: Optional descriptive name for the task.
        priority: low, normal, high, or critical (default: normal).
        working_directory: Optional working directory for the task.
        depends_on: Optional list of task IDs this task depends on.
    """
    try:
        orch = await get_orchestrator()
        task_id = await orch.submit_task(
            prompt=prompt,
            name=name or None,
            priority=_PRIORITY_MAP.get(priority, TaskPriority.NORMAL),
            working_directory=Path(working_directory) if working_directory else None,
            depends_on=depends_on,
        )
        return _format({"success": True, "task_id": task_id, "status": "queued"})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_submit_task", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_submit_batch(
    prompts: list[str],
    priority: str = "normal",
    working_directory: str = "",
) -> str:
    """Submit multiple tasks to the swarm at once for parallel execution.

    Args:
        prompts: Array of task prompts to execute in parallel.
        priority: Priority level for all tasks (low, normal, high, critical).
        working_directory: Working directory for all tasks.
    """
    try:
        orch = await get_orchestrator()
        task_ids = await orch.submit_batch(
            prompts=prompts,
            working_directory=Path(working_directory) if working_directory else None,
            priority=_PRIORITY_MAP.get(priority, TaskPriority.NORMAL),
        )
        return _format({"success": True, "task_ids": task_ids, "count": len(task_ids)})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_submit_batch", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_get_status() -> str:
    """Get the current status of the swarm including instances, tasks, and workers."""
    try:
        orch = await get_orchestrator()
        status = await orch.get_status()
        return _format(status)
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_get_status", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_list_tasks(status: str = "", limit: int = 50) -> str:
    """List all tasks or filter by status.

    Args:
        status: Optional status filter (pending, queued, running, completed, failed).
        limit: Maximum number of tasks to return (default: 50).
    """
    try:
        orch = await get_orchestrator()
        status_filter = TaskStatus(status) if status else None
        tasks = await orch.list_tasks(status_filter, limit)
        return _format({"tasks": tasks, "count": len(tasks)})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_list_tasks", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_get_task(task_id: str) -> str:
    """Get detailed information about a specific task including its status and results.

    Args:
        task_id: The task ID to query.
    """
    try:
        orch = await get_orchestrator()
        task_info = await orch.get_task_status(task_id)
        if not task_info:
            return _format({"success": False, "error": f"Task {task_id} not found"})
        return _format({"success": True, "task": task_info})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_get_task", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_list_instances() -> str:
    """List all Claude Code instances in the swarm with their status and statistics."""
    try:
        orch = await get_orchestrator()
        instances = await orch.list_instances()
        return _format({"instances": instances, "count": len(instances)})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_list_instances", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_scale(target: int) -> str:
    """Scale the number of instances in the swarm up or down.

    Args:
        target: Target number of instances (0-10).
    """
    try:
        orch = await get_orchestrator()
        result = await orch.scale_instances(target)
        return _format({"success": True, "target": target, "actual": result})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_scale", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_execute_workflow(workflow_path: str) -> str:
    """Execute a workflow from a YAML file with multiple coordinated tasks.

    Args:
        workflow_path: Path to the workflow YAML file.
    """
    try:
        orch = await get_orchestrator()
        path = Path(workflow_path)
        if not path.exists():
            return _format({"success": False, "error": f"Workflow file not found: {path}"})
        result = await orch.execute_workflow(path)
        return _format({"success": True, **result})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_execute_workflow", error=str(e))
        return _format({"success": False, "error": str(e)})


@mcp.tool()
async def swarm_cancel_task(task_id: str) -> str:
    """Cancel a pending or queued task.

    Args:
        task_id: The task ID to cancel.
    """
    try:
        orch = await get_orchestrator()
        success = await orch.cancel_task(task_id)
        return _format({"success": success, "task_id": task_id})
    except Exception as e:
        logger.error("tool_call_error", tool="swarm_cancel_task", error=str(e))
        return _format({"success": False, "error": str(e)})


# ══════════════════════════════════════════════════════════════════════════
# Entry point
# ══════════════════════════════════════════════════════════════════════════


def main():
    """Run the Claude Swarm MCP server (stdio transport)."""
    logger.info("claude_swarm_mcp_server_starting")
    try:
        mcp.run()
    finally:
        # Best-effort cleanup. mcp.run() handles stdio teardown.
        logger.info("server_shutdown")


if __name__ == "__main__":
    main()
