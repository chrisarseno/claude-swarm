#!/usr/bin/env python3
"""MCP Server for Claude Swarm.

This server exposes Claude Swarm functionality as MCP tools that can be used
by Claude Code and other MCP clients.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from swarm.core.orchestrator import SwarmOrchestrator
from swarm.core.task_queue import TaskPriority, TaskStatus
from swarm.utils.config import Config, load_config
from swarm.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)

# Global orchestrator instance
_orchestrator: Optional[SwarmOrchestrator] = None


async def get_orchestrator() -> SwarmOrchestrator:
    """Get or create the global orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        config_path = Path(__file__).parent / "config" / "swarm.yaml"
        config = load_config(config_path if config_path.exists() else None)
        setup_logging(level=config.logging.level)

        _orchestrator = SwarmOrchestrator(config)
        await _orchestrator.start(initial_instances=2)
        logger.info("orchestrator_started")

    return _orchestrator


async def shutdown_orchestrator():
    """Shutdown the orchestrator."""
    global _orchestrator
    if _orchestrator:
        await _orchestrator.stop()
        _orchestrator = None
        logger.info("orchestrator_stopped")


# MCP Tool Definitions
TOOLS = [
    {
        "name": "swarm_spawn_instances",
        "description": "Spawn new Claude Code instances in the swarm. Use this to add more parallel processing capacity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "count": {
                    "type": "number",
                    "description": "Number of instances to spawn (1-10)",
                    "minimum": 1,
                    "maximum": 10
                },
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the instances"
                }
            },
            "required": ["count"]
        }
    },
    {
        "name": "swarm_submit_task",
        "description": "Submit a task to the swarm for execution. The task will be assigned to an available Claude instance.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The task prompt/instruction to send to a Claude instance"
                },
                "name": {
                    "type": "string",
                    "description": "Optional descriptive name for the task"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "critical"],
                    "description": "Task priority level (default: normal)"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the task"
                },
                "depends_on": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of task IDs this task depends on"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "swarm_submit_batch",
        "description": "Submit multiple tasks to the swarm at once for parallel execution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompts": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of task prompts to execute in parallel"
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high", "critical"],
                    "description": "Priority level for all tasks"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Working directory for all tasks"
                }
            },
            "required": ["prompts"]
        }
    },
    {
        "name": "swarm_get_status",
        "description": "Get the current status of the swarm including instances, tasks, and workers.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "swarm_list_tasks",
        "description": "List all tasks or filter by status (pending, queued, running, completed, failed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["pending", "queued", "running", "completed", "failed"],
                    "description": "Optional status filter"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of tasks to return (default: 50)"
                }
            }
        }
    },
    {
        "name": "swarm_get_task",
        "description": "Get detailed information about a specific task including its status and results.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to query"
                }
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "swarm_list_instances",
        "description": "List all Claude Code instances in the swarm with their status and statistics.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "swarm_scale",
        "description": "Scale the number of instances in the swarm up or down.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "number",
                    "description": "Target number of instances (0-10)",
                    "minimum": 0,
                    "maximum": 10
                }
            },
            "required": ["target"]
        }
    },
    {
        "name": "swarm_execute_workflow",
        "description": "Execute a workflow from a YAML file with multiple coordinated tasks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "workflow_path": {
                    "type": "string",
                    "description": "Path to the workflow YAML file"
                }
            },
            "required": ["workflow_path"]
        }
    },
    {
        "name": "swarm_cancel_task",
        "description": "Cancel a pending or queued task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task ID to cancel"
                }
            },
            "required": ["task_id"]
        }
    }
]


# Tool Implementations
async def handle_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Handle a tool call and return the result."""
    orch = await get_orchestrator()

    try:
        if tool_name == "swarm_spawn_instances":
            count = arguments["count"]
            working_dir = Path(arguments["working_directory"]) if arguments.get("working_directory") else None

            instances = await orch.instance_manager.spawn_multiple(count, working_dir)

            return {
                "success": True,
                "spawned": len(instances),
                "instances": [i.get_info() for i in instances]
            }

        elif tool_name == "swarm_submit_task":
            priority_map = {
                "low": TaskPriority.LOW,
                "normal": TaskPriority.NORMAL,
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL
            }

            task_id = await orch.submit_task(
                prompt=arguments["prompt"],
                name=arguments.get("name"),
                priority=priority_map.get(arguments.get("priority", "normal"), TaskPriority.NORMAL),
                working_directory=Path(arguments["working_directory"]) if arguments.get("working_directory") else None,
                depends_on=arguments.get("depends_on")
            )

            return {
                "success": True,
                "task_id": task_id,
                "status": "queued"
            }

        elif tool_name == "swarm_submit_batch":
            priority_map = {
                "low": TaskPriority.LOW,
                "normal": TaskPriority.NORMAL,
                "high": TaskPriority.HIGH,
                "critical": TaskPriority.CRITICAL
            }

            task_ids = await orch.submit_batch(
                prompts=arguments["prompts"],
                working_directory=Path(arguments["working_directory"]) if arguments.get("working_directory") else None,
                priority=priority_map.get(arguments.get("priority", "normal"), TaskPriority.NORMAL)
            )

            return {
                "success": True,
                "task_ids": task_ids,
                "count": len(task_ids)
            }

        elif tool_name == "swarm_get_status":
            status = await orch.get_status()
            return status

        elif tool_name == "swarm_list_tasks":
            status_filter = None
            if arguments.get("status"):
                status_filter = TaskStatus(arguments["status"])

            limit = arguments.get("limit", 50)
            tasks = await orch.list_tasks(status_filter, limit)

            return {
                "tasks": tasks,
                "count": len(tasks)
            }

        elif tool_name == "swarm_get_task":
            task_info = await orch.get_task_status(arguments["task_id"])

            if not task_info:
                return {
                    "success": False,
                    "error": f"Task {arguments['task_id']} not found"
                }

            return {
                "success": True,
                "task": task_info
            }

        elif tool_name == "swarm_list_instances":
            instances = await orch.list_instances()

            return {
                "instances": instances,
                "count": len(instances)
            }

        elif tool_name == "swarm_scale":
            target = arguments["target"]
            result = await orch.scale_instances(target)

            return {
                "success": True,
                "target": target,
                "actual": result
            }

        elif tool_name == "swarm_execute_workflow":
            workflow_path = Path(arguments["workflow_path"])

            if not workflow_path.exists():
                return {
                    "success": False,
                    "error": f"Workflow file not found: {workflow_path}"
                }

            result = await orch.execute_workflow(workflow_path)

            return {
                "success": True,
                **result
            }

        elif tool_name == "swarm_cancel_task":
            success = await orch.cancel_task(arguments["task_id"])

            return {
                "success": success,
                "task_id": arguments["task_id"]
            }

        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }

    except Exception as e:
        logger.error("tool_call_error", tool=tool_name, error=str(e))
        return {
            "success": False,
            "error": str(e)
        }


# MCP Server Protocol
async def handle_message(message: dict) -> dict:
    """Handle an incoming MCP message."""
    method = message.get("method")

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "claude-swarm",
                "version": "0.1.0"
            }
        }

    elif method == "tools/list":
        return {
            "tools": TOOLS
        }

    elif method == "tools/call":
        tool_name = message["params"]["name"]
        arguments = message["params"].get("arguments", {})

        result = await handle_tool_call(tool_name, arguments)

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2)
                }
            ]
        }

    else:
        return {
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }


async def main():
    """Main MCP server loop."""
    logger.info("claude_swarm_mcp_server_starting")

    try:
        # Read from stdin, write to stdout (MCP protocol)
        while True:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )

            if not line:
                break

            try:
                message = json.loads(line)
                response = await handle_message(message)

                # Add ID from request if present
                if "id" in message:
                    response["id"] = message["id"]

                # Write response
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            except json.JSONDecodeError as e:
                logger.error("invalid_json", error=str(e))
            except Exception as e:
                logger.error("message_handling_error", error=str(e))

    except KeyboardInterrupt:
        logger.info("server_interrupted")
    finally:
        await shutdown_orchestrator()
        logger.info("server_shutdown")


if __name__ == "__main__":
    asyncio.run(main())
