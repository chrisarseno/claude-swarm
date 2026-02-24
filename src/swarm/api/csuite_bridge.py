"""
C-Suite Bridge API Endpoints.

REST endpoints for C-Suite agents to submit tasks, get outcomes,
and provide routing feedback.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..licensing import license_gate

router = APIRouter(prefix="/bridge", tags=["csuite-bridge"])


# Request/Response models

class BridgeTaskRequest(BaseModel):
    prompt: str = Field(..., description="Task prompt")
    agent_id: str = Field(default="", description="C-Suite agent code")
    personality: Optional[Dict[str, Any]] = Field(None, description="Agent personality traits")
    context: Optional[Dict[str, Any]] = Field(None, description="Task context")
    priority: str = Field(default="normal", description="Task priority")
    task_type: Optional[str] = Field(None, description="Pre-classified task type")
    timeout: int = Field(default=300, description="Timeout in seconds")


class RoutingFeedbackRequest(BaseModel):
    model: str = Field(..., description="Model that was used")
    task_type: str = Field(..., description="Task type that was executed")
    success: bool = Field(..., description="Whether the task succeeded")
    duration_ms: float = Field(default=0.0, description="Task duration in ms")
    quality_score: Optional[float] = Field(None, description="Quality score (0-1)")


# Global reference to orchestrator (set by server.py)
_orchestrator = None


def set_orchestrator(orch):
    """Set the orchestrator reference (called by server.py during startup)."""
    global _orchestrator
    _orchestrator = orch


@router.post("/task")
async def submit_bridge_task(request: BridgeTaskRequest):
    """
    Submit a task from C-Suite with agent metadata.

    The Swarm will analyze the task, route to the best model,
    and return the task ID for polling.
    """
    license_gate.gate("std.swarm.enterprise")
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    metadata = {
        "csuite_agent": request.agent_id,
        "source": "csuite_bridge",
    }
    if request.personality:
        metadata["personality"] = request.personality
    if request.context:
        metadata["context"] = request.context
    if request.task_type:
        metadata["task_type"] = request.task_type

    from ..core.task_queue import TaskPriority

    priority_map = {
        "low": TaskPriority.LOW,
        "normal": TaskPriority.NORMAL,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL,
    }

    task_id = await _orchestrator.submit_task(
        prompt=request.prompt,
        name=f"[{request.agent_id}] {request.prompt[:50]}",
        priority=priority_map.get(request.priority, TaskPriority.NORMAL),
        timeout=request.timeout,
        metadata=metadata,
    )

    return {"task_id": task_id, "status": "queued"}


@router.get("/outcomes")
async def get_outcomes(limit: int = 50):
    """
    Get completed task outcomes for metacognition feed.

    Returns recent completed tasks with their results and metadata.
    """
    license_gate.gate("std.swarm.enterprise")
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    from ..core.task_queue import TaskStatus

    tasks = await _orchestrator.list_tasks(status=TaskStatus.COMPLETED, limit=limit)

    # Filter to bridge tasks only
    outcomes = []
    for task in tasks:
        meta = task.get("metadata", {})
        if meta.get("source") == "csuite_bridge":
            outcomes.append({
                "task_id": task.get("id", ""),
                "agent_id": meta.get("csuite_agent", ""),
                "task_type": meta.get("task_type", ""),
                "status": task.get("status", ""),
                "duration_seconds": task.get("duration_seconds", 0),
                "model": task.get("result", {}).get("model", ""),
                "tool_calls_count": len(task.get("result", {}).get("tool_calls", [])),
                "success": task.get("status") == "completed",
            })

    return outcomes


@router.post("/routing-feedback")
async def submit_routing_feedback(request: RoutingFeedbackRequest):
    """
    Receive routing performance feedback from C-Suite.

    C-Suite can report how well a model performed at a task type,
    which the Swarm uses to improve future routing decisions.
    """
    license_gate.gate("std.swarm.enterprise")
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    _orchestrator.swarm_router.record_outcome(
        model=request.model,
        task_type=request.task_type,
        success=request.success,
        duration_ms=request.duration_ms,
    )

    return {"status": "recorded"}
