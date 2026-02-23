"""FastAPI server for Claude Swarm."""

import asyncio
from pathlib import Path
from typing import Optional, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import uvicorn

from .dashboard import DASHBOARD_HTML

from ..core.orchestrator import SwarmOrchestrator
from ..core.task_queue import TaskPriority, TaskStatus
from ..utils.config import Config, load_config
from ..utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


# ---- Global event bus for streaming tokens to WebSocket clients ----
class StreamBus:
    """Broadcast streaming events to connected WebSocket clients."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def publish(self, event: dict):
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subscribers.remove(q)


stream_bus = StreamBus()


# Request/Response models
class TaskSubmitRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to send to Claude")
    name: Optional[str] = Field(None, description="Task name")
    working_directory: Optional[str] = Field(None, description="Working directory")
    priority: str = Field(default="normal", description="Task priority (low, normal, high, critical)")
    timeout: Optional[int] = Field(None, description="Task timeout in seconds")
    instance_id: Optional[str] = Field(None, description="Specific instance ID to use")
    depends_on: Optional[list[str]] = Field(None, description="Task IDs this task depends on")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")


class TaskBatchRequest(BaseModel):
    prompts: list[str] = Field(..., description="List of prompts")
    working_directory: Optional[str] = Field(None, description="Working directory")
    priority: str = Field(default="normal", description="Task priority")


class WorkflowExecuteRequest(BaseModel):
    workflow_path: str = Field(..., description="Path to workflow YAML file")


class InstanceSpawnRequest(BaseModel):
    count: int = Field(default=1, description="Number of instances to spawn")
    working_directory: Optional[str] = Field(None, description="Working directory")


class ScaleRequest(BaseModel):
    target: int = Field(..., description="Target number of instances")


class WorkerScaleRequest(BaseModel):
    count: int = Field(..., description="Target number of workers")


# Global orchestrator instance
orchestrator: Optional[SwarmOrchestrator] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the FastAPI app."""
    global orchestrator

    # Startup
    config_path = Path("config/swarm.yaml")
    config = load_config(config_path if config_path.exists() else None)

    setup_logging(
        level=config.logging.level,
        log_file=config.logging.file,
        json_logs=config.logging.json_logs
    )

    logger.info("starting_swarm_api", config=config.model_dump())

    orchestrator = SwarmOrchestrator(config)
    await orchestrator.start(initial_instances=1)

    # Wire up the external agent bridge
    from .csuite_bridge import set_orchestrator as set_bridge_orch
    set_bridge_orch(orchestrator)

    yield

    # Shutdown
    if orchestrator:
        await orchestrator.stop()
    logger.info("swarm_api_stopped")


def create_app() -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        title="Claude Swarm API",
        description="Orchestration API for multiple Claude Code instances",
        version="0.1.0",
        lifespan=lifespan
    )

    # Include external agent bridge router
    from .csuite_bridge import router as csuite_router
    app.include_router(csuite_router)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # WARNING: Restrict this in production (e.g. ["https://yourdomain.com"])
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "claude-swarm"}

    # Dashboard
    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        """Live dashboard UI."""
        return DASHBOARD_HTML

    # Status endpoints
    @app.get("/status")
    async def get_status():
        """Get overall swarm status."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        return await orchestrator.get_status()

    # Instance endpoints
    @app.post("/instances/spawn")
    async def spawn_instances(request: InstanceSpawnRequest):
        """Spawn new Claude Code instances."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        working_dir = Path(request.working_directory) if request.working_directory else None
        instances = await orchestrator.instance_manager.spawn_multiple(
            count=request.count,
            working_directory=working_dir
        )

        return {
            "spawned": len(instances),
            "instances": [i.get_info() for i in instances]
        }

    @app.get("/instances")
    async def list_instances():
        """List all instances."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        return await orchestrator.list_instances()

    @app.get("/instances/{instance_id}")
    async def get_instance(instance_id: str):
        """Get instance details."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        instance = await orchestrator.instance_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        return instance.get_info()

    @app.get("/instances/{instance_id}/output")
    async def get_instance_output(instance_id: str, lines: int = 50):
        """Get recent output from an instance."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        output = await orchestrator.get_instance_output(instance_id, lines)
        if output is None:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        return {"instance_id": instance_id, "output": output}

    @app.get("/instances/{instance_id}/stream")
    async def get_instance_stream(instance_id: str):
        """Get live streaming buffer from a running instance."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        instance = await orchestrator.instance_manager.get_instance(instance_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        return {
            "instance_id": instance_id,
            "status": instance.status.value,
            "current_task": instance.current_task,
            "partial_output": getattr(instance, "stream_buffer", ""),
        }

    @app.delete("/instances/{instance_id}")
    async def terminate_instance(instance_id: str):
        """Terminate an instance."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        success = await orchestrator.instance_manager.terminate_instance(instance_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Instance {instance_id} not found")

        return {"success": True, "instance_id": instance_id}

    @app.post("/instances/scale")
    async def scale_instances(request: ScaleRequest):
        """Scale instances to target count."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        result = await orchestrator.scale_instances(request.target)
        return {"target": request.target, "actual": result}

    @app.post("/workers/scale")
    async def scale_workers(request: WorkerScaleRequest):
        """Scale worker count to enable parallel task processing."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        result = await orchestrator.ensure_workers(request.count)
        return {"target": request.count, "actual": result}

    # Task endpoints
    @app.post("/tasks")
    async def submit_task(request: TaskSubmitRequest):
        """Submit a task to the queue."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }

        task_id = await orchestrator.submit_task(
            prompt=request.prompt,
            name=request.name,
            working_directory=Path(request.working_directory) if request.working_directory else None,
            priority=priority_map.get(request.priority.lower(), TaskPriority.NORMAL),
            timeout=request.timeout,
            instance_id=request.instance_id,
            depends_on=request.depends_on,
            metadata=request.metadata
        )

        return {"task_id": task_id, "status": "queued"}

    @app.post("/tasks/batch")
    async def submit_batch(request: TaskBatchRequest):
        """Submit multiple tasks at once."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL
        }

        task_ids = await orchestrator.submit_batch(
            prompts=request.prompts,
            working_directory=Path(request.working_directory) if request.working_directory else None,
            priority=priority_map.get(request.priority.lower(), TaskPriority.NORMAL)
        )

        return {"task_ids": task_ids, "count": len(task_ids)}

    @app.get("/tasks")
    async def list_tasks(status: Optional[str] = None, limit: int = 100):
        """List tasks."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        status_filter = None
        if status:
            try:
                status_filter = TaskStatus(status.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

        return await orchestrator.list_tasks(status_filter, limit)

    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get task status."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        task_info = await orchestrator.get_task_status(task_id)
        if not task_info:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        return task_info

    @app.delete("/tasks/{task_id}")
    async def cancel_task(task_id: str):
        """Cancel a pending task."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        success = await orchestrator.cancel_task(task_id)
        if not success:
            return {"success": False, "message": "Task cannot be cancelled (not pending/queued or not found)"}

        return {"success": True, "task_id": task_id}

    # Workflow endpoints
    @app.post("/workflows/execute")
    async def execute_workflow(request: WorkflowExecuteRequest):
        """Execute a workflow from a YAML file."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        workflow_path = Path(request.workflow_path)
        if not workflow_path.exists():
            raise HTTPException(status_code=404, detail=f"Workflow file not found: {request.workflow_path}")

        result = await orchestrator.execute_workflow(workflow_path)
        return result

    # Model & routing endpoints
    @app.get("/models")
    async def list_models():
        """List available models and their capabilities."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")

        models = await orchestrator.model_registry.get_installed_models()
        result = []
        for m in models:
            profile = m.get("profile")
            entry = {
                "name": m["name"],
                "size_gb": round(m.get("size_bytes", 0) / (1024 ** 3), 2),
                "has_profile": profile is not None,
            }
            if profile:
                entry.update({
                    "quality_rating": profile.quality_rating,
                    "speed_rating": profile.speed_rating,
                    "supports_tool_calling": profile.supports_tool_calling,
                    "tool_calling_quality": profile.tool_calling_quality,
                    "task_tags": profile.task_tags or [],
                    "context_window": profile.context_window,
                })
            result.append(entry)
        return result

    @app.get("/models/stats")
    async def model_stats():
        """Get model registry statistics."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        return await orchestrator.model_registry.get_stats()

    @app.get("/routing/stats")
    async def routing_stats():
        """Get routing performance statistics."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        return orchestrator.swarm_router.get_stats()

    @app.get("/backends")
    async def list_backends():
        """List all backend endpoints and their status."""
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized")
        return orchestrator.backend_manager.get_status()

    # WebSocket endpoint for real-time updates + streaming tokens
    @app.websocket("/ws/stream")
    async def websocket_stream(websocket: WebSocket):
        """WebSocket endpoint for streaming instance output and status."""
        await websocket.accept()
        logger.info("websocket_connected")

        queue = stream_bus.subscribe()

        async def send_events():
            """Forward stream bus events to this client."""
            try:
                while True:
                    event = await queue.get()
                    await websocket.send_json(event)
            except (WebSocketDisconnect, Exception):
                pass

        async def send_status():
            """Send periodic status updates."""
            try:
                while True:
                    if orchestrator:
                        status = await orchestrator.get_status()
                        await websocket.send_json({"type": "status", **status})
                    await asyncio.sleep(2)
            except (WebSocketDisconnect, Exception):
                pass

        try:
            event_task = asyncio.create_task(send_events())
            status_task = asyncio.create_task(send_status())
            # Wait for client disconnect
            await asyncio.gather(event_task, status_task)
        except (WebSocketDisconnect, Exception):
            pass
        finally:
            stream_bus.unsubscribe(queue)
            logger.info("websocket_disconnected")

    return app


def start_server(host: str = "0.0.0.0", port: int = 8766, reload: bool = False):
    """Start the API server."""
    uvicorn.run(
        "swarm.api.server:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )
