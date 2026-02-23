# Claude Swarm 🐝
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://python.org)

A powerful orchestration system for managing multiple Claude Code instances simultaneously.

## Features

- **Multi-Instance Management**: Spawn and control multiple Claude Code instances
- **Task Queue System**: Intelligent work distribution across instances
- **REST & WebSocket API**: Integrate with web UIs and other tools
- **Workflow Automation**: Define complex multi-step workflows in YAML
- **Real-time Monitoring**: Track instance status, task progress, and outputs
- **Load Balancing**: Distribute tasks efficiently across available instances
- **Parallel Execution**: Run tasks on different projects simultaneously
- **🎯 MCP Integration**: Available as a tool directly in Claude Code sessions!

## 🚀 Use in Claude Code (MCP Integration)

Claude Swarm can be registered as an MCP server so you can use it directly in any Claude Code session. See [MCP_QUICKSTART.md](MCP_QUICKSTART.md) for setup instructions.

Once configured, try:

```
"Spawn 3 swarm instances and analyze these in parallel:
1. Review authentication for security issues
2. Check database queries for performance
3. Analyze API error handling"
```

Claude will automatically:
- Spawn instances
- Distribute tasks
- Monitor progress
- Return results

**See [MCP_INTEGRATION.md](MCP_INTEGRATION.md) for complete details and examples.**

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web UI / CLI                           │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST/WebSocket API
┌───────────────────────▼─────────────────────────────────────┐
│                   Swarm Orchestrator                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Task Queue   │  │ Instance     │  │ Workflow     │     │
│  │ Manager      │  │ Manager      │  │ Engine       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼───────┐
│ Claude Code  │ │ Claude Code │ │ Claude Code │
│ Instance 1   │ │ Instance 2  │ │ Instance 3  │
└──────────────┘ └─────────────┘ └─────────────┘
```

## Quick Start

### Installation

```bash
cd claude-swarm
pip install -r requirements.txt
pip install -e .
```

### Start the Orchestrator

```bash
# Start API server
python scripts/start_swarm.py

# Or use the CLI
python scripts/cli.py spawn --count 3
python scripts/cli.py task add "Fix bug in auth module" --instance 1
python scripts/cli.py status
```

### Example Workflow

```yaml
# config/workflows/multi_project.yaml
name: "Multi-Project Build and Test"
instances: 3
tasks:
  - name: "Build Frontend"
    directory: "./frontend"
    command: "npm run build"
    instance: 1

  - name: "Run Backend Tests"
    directory: "./backend"
    command: "pytest tests/"
    instance: 2

  - name: "Lint All Code"
    directory: "."
    command: "ruff check ."
    instance: 3
    depends_on: ["Build Frontend", "Run Backend Tests"]
```

## API Endpoints

### REST API

- `POST /instances/spawn` - Create new Claude Code instance
- `GET /instances` - List all instances
- `GET /instances/{id}` - Get instance details
- `DELETE /instances/{id}` - Terminate instance
- `POST /tasks` - Add task to queue
- `GET /tasks` - List all tasks
- `POST /workflows/execute` - Execute workflow from config

### WebSocket

- `ws://localhost:8766/ws/stream` - Real-time instance output and events

## Configuration

Edit `config/swarm.yaml` to customize:

```yaml
swarm:
  max_instances: 10
  default_timeout: 300
  workspace_root: "."

api:
  host: "0.0.0.0"
  port: 8766
  enable_websocket: true

logging:
  level: "INFO"
  file: "logs/swarm.log"
```

## Use Cases

1. **Parallel Project Work**: Work on multiple codebases simultaneously
2. **CI/CD Orchestration**: Run tests, builds, and deployments in parallel
3. **Multi-Step Workflows**: Complex tasks with dependencies
4. **Load Testing**: Spawn many instances for stress testing
5. **Experimentation**: Try different approaches in parallel

## Advanced Features

- **Task Dependencies**: Define task execution order
- **Resource Management**: CPU/memory limits per instance
- **Failure Handling**: Automatic retries and fallbacks
- **State Persistence**: Save and restore swarm state
- **Plugin System**: Extend functionality with custom plugins

## Contributing

This is an experimental tool. Contributions welcome!

## License

This project is dual-licensed:

- **AGPL-3.0** — free for open-source use. See [LICENSE](LICENSE).
- **Commercial License** — for proprietary use without AGPL obligations. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

Copyright (c) 2025-2026 Chris Arsenault / 1450 Enterprises LLC.
