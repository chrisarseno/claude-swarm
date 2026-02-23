# Getting Started with Claude Swarm

Welcome! Claude Swarm has been created and is ready to help you orchestrate multiple Claude Code instances.

## What You Have

A complete orchestration system with:

### Core System
- **Orchestrator**: Coordinates all operations
- **Instance Manager**: Manages Claude Code instances
- **Task Queue**: Handles task scheduling and dependencies
- **Claude Wrapper**: Interfaces with Claude Code CLI
- **API Server**: REST and WebSocket endpoints

### Interfaces
1. **REST API**: HTTP endpoints for programmatic access
2. **WebSocket API**: Real-time streaming
3. **CLI Tool**: Command-line interface
4. **Python Library**: Direct integration

### Configuration
- YAML-based configuration
- Environment variable support
- Flexible and extensible

### Examples
- Multi-project workflows
- Code analysis workflows
- CI/CD pipeline
- Python integration examples

## Quick Start (5 minutes)

### Step 1: Install Dependencies

```bash
cd claude-swarm
pip install -r requirements.txt
```

### Step 2: Test the CLI

```bash
# Check status
python scripts/cli.py status

# Spawn instances
python scripts/cli.py spawn --count 2

# List instances
python scripts/cli.py instances
```

### Step 3: Start the API Server

```bash
python scripts/start_swarm.py
```

Visit http://localhost:8766/docs for interactive API documentation.

### Step 4: Try a Workflow

```bash
# Edit the example workflow for your project
python scripts/cli.py workflow examples/multi_project_workflow.yaml
```

## Integration with Your Web UI

Your web UI can communicate with Claude Swarm via the API:

### Option 1: REST API

```javascript
// Submit a task
const response = await fetch('http://localhost:8766/tasks', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    prompt: 'Your task here',
    priority: 'high'
  })
});

const { task_id } = await response.json();

// Check status
const status = await fetch(`http://localhost:8766/tasks/${task_id}`);
const task = await status.json();
```

### Option 2: WebSocket (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8766/ws/stream');

ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  // Update your UI with real-time status
  updateDashboard(status);
};
```

### Option 3: Python Integration

```python
from swarm.core.orchestrator import SwarmOrchestrator
from swarm.utils.config import Config

async def main():
    config = Config()
    orchestrator = SwarmOrchestrator(config)
    await orchestrator.start(initial_instances=3)

    task_id = await orchestrator.submit_task(
        prompt="Your task",
        priority=TaskPriority.HIGH
    )

    # ... monitor and get results
```

## Next Steps

### 1. Customize Configuration

Edit `config/swarm.yaml`:

```yaml
swarm:
  max_instances: 10  # Adjust based on your system
  default_timeout: 300
  claude_command: "claude"  # Or full path if needed

api:
  host: "0.0.0.0"
  port: 8766  # Change if needed

logging:
  level: "INFO"  # DEBUG for more detail
```

### 2. Create Your Workflows

Create YAML files for your common tasks:

```yaml
name: "My Workflow"
instances: 3

tasks:
  - name: "Task 1"
    directory: "./my-project"
    command: "npm test"

  - name: "Task 2"
    prompt: "Review this code for issues"
    depends_on: ["Task 1"]
```

### 3. Integrate with Your Web UI

1. Start the API server: `python scripts/start_swarm.py`
2. Configure your web UI to call the API endpoints
3. Use WebSocket for real-time updates
4. Display instance and task status in your dashboard

### 4. Build Custom Extensions

Extend the system for your needs:

- Custom task types
- Additional API endpoints
- Workflow processors
- Event handlers
- Monitoring integrations

## Common Use Cases

### Use Case 1: Parallel Testing

Run tests across multiple projects simultaneously:

```bash
python scripts/cli.py task "Run frontend tests" --dir ./frontend &
python scripts/cli.py task "Run backend tests" --dir ./backend &
python scripts/cli.py task "Run integration tests" --dir ./tests &
```

### Use Case 2: Code Review Automation

Submit multiple review tasks:

```python
prompts = [
    "Review authentication for security issues",
    "Check database queries for performance",
    "Analyze error handling patterns",
    "Review API endpoint documentation"
]

task_ids = await orchestrator.submit_batch(prompts)
```

### Use Case 3: CI/CD Pipeline

Execute your CI workflow:

```bash
python scripts/cli.py workflow examples/continuous_integration.yaml
```

### Use Case 4: Multi-Environment Deployment

Deploy to multiple environments in parallel:

```yaml
tasks:
  - name: "Deploy Staging"
    command: "deploy staging"
    instance: 1

  - name: "Deploy QA"
    command: "deploy qa"
    instance: 2

  - name: "Deploy Prod"
    command: "deploy production"
    depends_on: ["Deploy Staging", "Deploy QA"]
```

## Troubleshooting

### Problem: "Claude command not found"

**Solution**: Specify full path in config:
```yaml
swarm:
  claude_command: "C:/path/to/claude.exe"
```

### Problem: Instances not starting

**Solution**:
1. Check Claude is installed: `claude --version`
2. Check system resources (memory, CPU)
3. Reduce `max_instances` in config

### Problem: Tasks stuck in queue

**Solution**:
1. Check instance status: `python scripts/cli.py instances`
2. Spawn more instances: `python scripts/cli.py spawn --count 2`
3. Check task dependencies: `python scripts/cli.py tasks`

### Problem: High memory usage

**Solution**:
1. Reduce `max_instances`
2. Clear completed tasks periodically
3. Limit output buffer size

### Problem: API connection refused

**Solution**:
1. Ensure server is running: `python scripts/start_swarm.py`
2. Check firewall settings
3. Verify port is not in use: `netstat -ano | findstr :8766`

## Documentation

- **[README.md](README.md)**: Overview and features
- **[QUICKSTART.md](QUICKSTART.md)**: Quick start guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Technical architecture
- **[examples/README.md](examples/README.md)**: Workflow examples

## API Documentation

Once the server is running:
- **Interactive Docs**: http://localhost:8766/docs
- **ReDoc**: http://localhost:8766/redoc

## Tips for Success

1. **Start Small**: Begin with 1-2 instances and scale up
2. **Use Dependencies**: Chain tasks that depend on each other
3. **Monitor Resources**: Watch CPU and memory usage
4. **Create Workflows**: Reusable workflows save time
5. **Use Priorities**: Mark urgent tasks as high/critical
6. **Log Everything**: Enable debug logging when troubleshooting
7. **Clean Up**: Periodically clear completed tasks
8. **Test Locally**: Test workflows before running in production

## Performance Tips

- Pre-spawn instances for faster task execution
- Use batch submission for many similar tasks
- Pin tasks to specific instances for consistency
- Scale dynamically based on queue depth
- Use async/await for concurrent operations

## Security Considerations

For production use:
1. Add API authentication
2. Configure CORS properly
3. Implement rate limiting
4. Enable HTTPS
5. Restrict network access
6. Audit logging

## Getting Help

1. Check the documentation files
2. Review example workflows
3. Look at integration examples
4. Check the test files for usage patterns

## What's Next?

Now that you have Claude Swarm set up, here are some ideas:

1. **Integrate with your web UI** - Connect it to the API
2. **Create custom workflows** - Automate your common tasks
3. **Build extensions** - Add features specific to your needs
4. **Scale up** - Test with more instances and tasks
5. **Monitor** - Add metrics and alerting
6. **Share** - Create workflows others can use

## Project Structure

```
claude-swarm/
├── src/swarm/           # Core source code
│   ├── core/            # Orchestrator, queue, instances
│   ├── claude/          # Claude Code wrapper
│   ├── api/             # API server
│   └── utils/           # Config, logging
├── config/              # Configuration files
├── scripts/             # CLI and startup scripts
├── examples/            # Example workflows
├── tests/               # Test suite
└── docs/                # Documentation (this file)
```

## Support the Project

If you find Claude Swarm useful:
- Star the repository if you find it useful!
- Report bugs and issues
- Contribute improvements
- Share your workflows
- Help others get started

---

Happy orchestrating! 🐝

For questions or issues, check the documentation or create an issue on GitHub.
