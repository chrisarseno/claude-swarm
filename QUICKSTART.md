> For a more detailed guide, see [GET_STARTED.md](GET_STARTED.md).

# Claude Swarm Quickstart Guide

Get started with Claude Swarm in 5 minutes!

## Installation

```bash
cd claude-swarm

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Basic Usage

### 1. Start the API Server

```bash
python scripts/start_swarm.py
```

The server will start on `http://localhost:8765`. Visit `http://localhost:8765/docs` for interactive API documentation.

### 2. Use the CLI

Open a new terminal and try these commands:

```bash
# Start the orchestrator with 3 instances
python scripts/cli.py start --instances 3

# In another terminal:

# Check status
python scripts/cli.py status

# Spawn more instances
python scripts/cli.py spawn --count 2

# Submit a task
python scripts/cli.py task "Analyze the authentication module for security issues" --wait

# List all tasks
python scripts/cli.py tasks

# List all instances
python scripts/cli.py instances

# Execute a workflow
python scripts/cli.py workflow examples/multi_project_workflow.yaml
```

### 3. Use the REST API

```bash
# Submit a task via API
curl -X POST http://localhost:8765/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Review the code for performance issues",
    "name": "Performance Review",
    "priority": "high"
  }'

# Check status
curl http://localhost:8765/status

# List instances
curl http://localhost:8765/instances

# List tasks
curl http://localhost:8765/tasks
```

### 4. Use with Your Web UI

If you have a web UI, connect it to the API:

```javascript
// Example: Submit a task from your web app
const response = await fetch('http://localhost:8765/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'Fix the bug in the login flow',
    name: 'Login Bug Fix',
    priority: 'critical'
  })
});

const result = await response.json();
console.log('Task ID:', result.task_id);

// Check task status
const taskStatus = await fetch(`http://localhost:8765/tasks/${result.task_id}`);
const task = await taskStatus.json();
console.log('Task status:', task.status);

// WebSocket for real-time updates
const ws = new WebSocket('ws://localhost:8765/ws/stream');
ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log('Swarm status:', status);
};
```

## Common Workflows

### Parallel Testing Across Multiple Projects

Create a workflow file `my_workflow.yaml`:

```yaml
name: "Run All Tests"
instances: 3

tasks:
  - name: "Test Frontend"
    directory: "./frontend"
    command: "npm test"
    instance: 1

  - name: "Test Backend"
    directory: "./backend"
    command: "pytest"
    instance: 2

  - name: "Test API"
    directory: "./api"
    command: "npm test"
    instance: 3
```

Execute it:

```bash
python scripts/cli.py workflow my_workflow.yaml
```

### Code Review Automation

```python
import asyncio
import httpx

async def automated_review():
    async with httpx.AsyncClient() as client:
        # Submit multiple review tasks
        tasks = [
            "Review security of authentication system",
            "Review error handling in API endpoints",
            "Review database query efficiency",
            "Review frontend component structure"
        ]

        task_ids = []
        for task in tasks:
            response = await client.post(
                'http://localhost:8765/tasks',
                json={'prompt': task, 'priority': 'high'}
            )
            task_ids.append(response.json()['task_id'])

        # Wait for all to complete
        while True:
            all_complete = True
            for task_id in task_ids:
                response = await client.get(f'http://localhost:8765/tasks/{task_id}')
                task = response.json()
                if task['status'] not in ['completed', 'failed']:
                    all_complete = False
                    break

            if all_complete:
                break

            await asyncio.sleep(2)

        print("All reviews complete!")

asyncio.run(automated_review())
```

### Load Testing with Multiple Instances

```bash
# Spawn 10 instances
python scripts/cli.py spawn --count 10

# Submit 100 tasks
for i in {1..100}; do
  python scripts/cli.py task "Task $i: Analyze module X" &
done

# Monitor progress
watch -n 1 python scripts/cli.py status
```

## Configuration

Edit `config/swarm.yaml` to customize:

- Maximum number of instances
- Default timeouts
- API port and host
- Logging settings

## Tips

1. **Start Small**: Begin with 1-2 instances and scale up as needed
2. **Use Task Dependencies**: Chain tasks that depend on each other
3. **Monitor Resource Usage**: Each instance consumes memory and CPU
4. **Use Priorities**: Mark urgent tasks as 'high' or 'critical' priority
5. **Workflow Files**: Create reusable workflows for common operations

## Troubleshooting

**Problem**: Instances fail to start

- Check that `claude` command is in your PATH
- Try specifying full path in `config/swarm.yaml`: `claude_command: "C:/path/to/claude.exe"`

**Problem**: Tasks stuck in queue

- Check instance status: `python scripts/cli.py instances`
- Spawn more instances if all are busy

**Problem**: High memory usage

- Reduce `max_instances` in config
- Terminate idle instances
- Clear completed tasks periodically

## Next Steps

- Read the full [README.md](README.md) for architecture details
- Check out [examples/](examples/) for more workflow examples
- Integrate with your existing tools and workflows
- Build custom extensions and plugins

Happy swarming! 🐝
