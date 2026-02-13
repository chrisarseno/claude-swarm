# Claude Swarm Architecture

This document provides a detailed overview of Claude Swarm's architecture, design decisions, and extension points.

## Overview

Claude Swarm is a distributed orchestration system for managing multiple Claude Code CLI instances. It provides task queuing, load balancing, dependency management, and a REST/WebSocket API for integration.

## Core Components

### 1. Orchestrator (`core/orchestrator.py`)

The central coordinator that ties all components together.

**Responsibilities**:
- Starting/stopping the system
- Managing worker loops
- Coordinating between instance manager and task queue
- Exposing high-level operations

**Key Methods**:
- `start()` - Initialize and start worker loops
- `submit_task()` - Add tasks to queue
- `execute_workflow()` - Process YAML workflows
- `get_status()` - System-wide status

**Design Decisions**:
- Uses worker pattern with configurable worker count
- Workers poll task queue and execute on available instances
- Async/await throughout for efficient I/O

### 2. Instance Manager (`core/instance_manager.py`)

Manages the pool of Claude Code instances.

**Responsibilities**:
- Spawning new instances
- Tracking instance status
- Finding available instances
- Scaling up/down
- Health monitoring

**Key Methods**:
- `spawn_instance()` - Create new Claude instance
- `get_idle_instance()` - Find available instance
- `scale_to()` - Adjust instance count
- `health_check()` - Monitor instance health

**Design Decisions**:
- Instances run as subprocesses
- Each instance maintains its own state and output buffer
- Instances can be pinned to specific working directories
- Automatic cleanup on termination

### 3. Task Queue (`core/task_queue.py`)

Priority queue with dependency management.

**Responsibilities**:
- Task queuing and prioritization
- Dependency tracking
- Task lifecycle management
- Status reporting

**Key Methods**:
- `add_task()` - Queue new task
- `get_next_task()` - Retrieve task for execution
- `complete_task()` - Mark task complete
- `_check_dependent_tasks()` - Unblock waiting tasks

**Design Decisions**:
- Async queue for non-blocking operations
- Task dependencies stored as ID references
- Automatic dependency resolution
- Priority levels (LOW, NORMAL, HIGH, CRITICAL)

### 4. Claude Instance Wrapper (`claude/wrapper.py`)

Low-level interface to Claude Code CLI.

**Responsibilities**:
- Process management
- Input/output handling
- Status tracking
- Error handling

**Key Methods**:
- `start()` - Launch Claude process
- `execute()` - Send command and capture output
- `stop()` - Terminate process
- `get_info()` - Instance metadata

**Design Decisions**:
- Subprocess communication via stdin/stdout
- Output buffering for retrieval
- Timeout handling
- Resource monitoring (CPU, memory)

### 5. API Server (`api/server.py`)

FastAPI-based REST and WebSocket API.

**Endpoints**:
```
GET    /health              - Health check
GET    /status              - Swarm status
POST   /instances/spawn     - Create instances
GET    /instances           - List instances
GET    /instances/{id}      - Instance details
DELETE /instances/{id}      - Terminate instance
POST   /instances/scale     - Scale instances
POST   /tasks               - Submit task
POST   /tasks/batch         - Submit multiple
GET    /tasks               - List tasks
GET    /tasks/{id}          - Task details
DELETE /tasks/{id}          - Cancel task
POST   /workflows/execute   - Run workflow
WS     /ws/stream           - Real-time updates
```

**Design Decisions**:
- FastAPI for automatic OpenAPI docs
- CORS middleware for web UI integration
- WebSocket for real-time streaming
- Pydantic models for validation
- Lifespan events for setup/teardown

## Data Flow

### Task Submission Flow

```
1. User/API submits task
   ↓
2. Orchestrator creates Task object
   ↓
3. Task added to TaskQueue
   ↓
4. Dependencies checked
   ↓
5. If ready → Queue, else → Pending
   ↓
6. Worker retrieves task
   ↓
7. Worker gets idle instance
   ↓
8. Task executed on instance
   ↓
9. Result captured
   ↓
10. Task marked complete
   ↓
11. Dependent tasks checked
```

### Instance Management Flow

```
1. Instance spawned
   ↓
2. Claude Code process started
   ↓
3. Instance marked IDLE
   ↓
4. Worker requests instance
   ↓
5. Instance marked BUSY
   ↓
6. Command executed
   ↓
7. Output captured
   ↓
8. Instance marked IDLE
   ↓
9. Available for next task
```

### Workflow Execution Flow

```
1. YAML file parsed
   ↓
2. Tasks extracted
   ↓
3. Dependencies mapped
   ↓
4. Instances scaled if needed
   ↓
5. Tasks submitted to queue
   ↓
6. Execution follows dependency graph
   ↓
7. Results collected
```

## Concurrency Model

### Worker Pattern

- Multiple worker coroutines run concurrently
- Each worker independently polls for tasks
- Workers coordinate through the task queue
- Lock-free where possible, using asyncio.Lock when needed

### Async Architecture

```python
# Worker loop (simplified)
async def worker_loop():
    while running:
        task = await queue.get_next_task()
        if task:
            instance = await get_idle_instance()
            result = await instance.execute(task)
            await queue.complete_task(task.id, result)
```

### Locking Strategy

- TaskQueue: Lock for queue modifications
- InstanceManager: Lock for pool modifications
- Instance: No locking (single owner)

## Configuration

### Hierarchy

```
1. Environment variables (.env)
2. Config file (config/swarm.yaml)
3. Default values (in Config class)
```

### Config Structure

```python
Config
├── swarm (SwarmConfig)
│   ├── max_instances
│   ├── default_timeout
│   ├── workspace_root
│   └── claude_command
├── api (APIConfig)
│   ├── host
│   ├── port
│   ├── enable_websocket
│   └── cors_origins
└── logging (LoggingConfig)
    ├── level
    ├── file
    └── json_logs
```

## Extension Points

### 1. Custom Task Types

Extend the `Task` class:

```python
@dataclass
class CustomTask(Task):
    custom_field: str = ""

    async def execute(self, instance):
        # Custom execution logic
        pass
```

### 2. Custom Instance Types

Extend `ClaudeInstance`:

```python
class RemoteClaudeInstance(ClaudeInstance):
    async def start(self):
        # Connect to remote Claude instance
        pass
```

### 3. Middleware

Add FastAPI middleware:

```python
@app.middleware("http")
async def custom_middleware(request, call_next):
    # Custom logic
    response = await call_next(request)
    return response
```

### 4. Event Handlers

Add task callbacks:

```python
def on_task_complete(result):
    # Custom handling
    pass

task = Task(
    prompt="...",
    callback=on_task_complete
)
```

### 5. Custom Workflows

Create workflow processors:

```python
class CustomWorkflowEngine:
    async def execute(self, workflow_path):
        # Custom workflow logic
        pass
```

## Scaling Considerations

### Horizontal Scaling

Current: Single-node orchestrator with multiple instances

Future possibilities:
- Distributed task queue (Redis, RabbitMQ)
- Multiple orchestrator nodes
- Shared instance pool
- Load balancing

### Resource Limits

- CPU: One Claude instance per task
- Memory: ~200-500MB per instance
- Network: API server + WebSocket
- Disk: Logs and output buffers

### Performance Tuning

1. **Worker Count**: Match to max_instances
2. **Instance Pooling**: Pre-spawn instances
3. **Task Batching**: Group similar tasks
4. **Output Buffering**: Limit buffer size
5. **Cleanup**: Periodically clear completed tasks

## Security Considerations

### Current

- No authentication on API
- CORS set to allow all origins
- No rate limiting
- Subprocess isolation only

### Recommendations for Production

1. Add API authentication (JWT, API keys)
2. Configure CORS properly
3. Implement rate limiting
4. Add request validation
5. Sandbox instances
6. Encrypt sensitive data
7. Audit logging

## Testing Strategy

### Unit Tests

- Test individual components in isolation
- Mock external dependencies (Claude CLI)
- Test error conditions

### Integration Tests

- Test component interactions
- Test workflow execution
- Test API endpoints

### Load Tests

- Test with many instances
- Test with many tasks
- Test dependency resolution at scale

## Monitoring

### Metrics to Track

- Instance count and status
- Task queue depth
- Task completion rate
- Error rate
- Resource usage (CPU, memory)
- API latency

### Logging

- Structured logging with context
- Log levels for filtering
- Correlation IDs for tracing
- JSON format option for parsing

## Future Enhancements

### Planned Features

1. **Web UI Dashboard**: Real-time visualization
2. **Task Scheduling**: Cron-like scheduling
3. **Result Persistence**: Database storage
4. **Retries**: Automatic retry logic
5. **Notifications**: Webhooks, email, Slack
6. **Resource Quotas**: CPU/memory limits
7. **Plugin System**: Dynamic extensions
8. **Multi-tenancy**: Isolated workspaces

### Integration Ideas

- CI/CD systems (GitHub Actions, GitLab CI)
- Project management tools (Jira, Linear)
- Chat platforms (Slack, Discord)
- IDE extensions (VS Code, IntelliJ)
- Monitoring systems (Prometheus, Grafana)

## Contributing

See main README for contribution guidelines.

Key areas for contribution:
- Additional workflow examples
- Performance optimizations
- Better error handling
- Documentation improvements
- Test coverage
- Feature implementations

## References

- FastAPI: https://fastapi.tiangolo.com/
- Asyncio: https://docs.python.org/3/library/asyncio.html
- Claude Code CLI: https://github.com/anthropics/claude-code
