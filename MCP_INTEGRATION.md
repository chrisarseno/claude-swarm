# Claude Swarm MCP Integration

Claude Swarm can be registered as an MCP (Model Context Protocol) server, allowing you to use it directly from any Claude Code session as a built-in tool.

## Setup

### 1. Install Claude Swarm

```bash
cd claude-swarm
pip install -r requirements.txt
pip install -e .
```

### 2. Register the MCP Server

Add the following to your Claude MCP settings file (`~/.claude/mcp_settings.json`):

```json
{
  "mcpServers": {
    "claude-swarm": {
      "command": "python",
      "args": ["-m", "swarm.mcp_server"],
      "cwd": "/path/to/claude-swarm"
    }
  }
}
```

Replace `/path/to/claude-swarm` with the actual path to your clone.

### 3. Restart Claude Code

Start a new Claude Code session for the MCP server to become available.

## How to Use

### In Any Claude Code Session

You can now use Claude Swarm tools directly! Just ask Claude to use them:

```
"Spawn 3 swarm instances and submit these tasks in parallel:
1. Review the authentication module for security issues
2. Analyze database queries for performance
3. Check the API for proper error handling"
```

Claude will automatically use the swarm tools to:
1. Spawn instances
2. Submit tasks
3. Monitor progress
4. Return results

## 🔧 Available Tools

### 1. swarm_spawn_instances
Spawn new Claude Code instances for parallel work.

**Example**:
```
"Spawn 5 swarm instances to handle multiple tasks"
```

### 2. swarm_submit_task
Submit a single task to the swarm.

**Example**:
```
"Submit a high-priority task to the swarm: 'Fix the login bug'"
```

### 3. swarm_submit_batch
Submit multiple tasks at once.

**Example**:
```
"Submit these tasks to the swarm in batch:
- Test the payment flow
- Review the checkout code
- Analyze cart performance"
```

### 4. swarm_get_status
Get current swarm status.

**Example**:
```
"What's the status of my swarm?"
```

### 5. swarm_list_tasks
List all tasks or filter by status.

**Example**:
```
"Show me all running tasks in the swarm"
```

### 6. swarm_get_task
Get details about a specific task.

**Example**:
```
"Get the status of task abc123"
```

### 7. swarm_list_instances
List all instances in the swarm.

**Example**:
```
"List all swarm instances"
```

### 8. swarm_scale
Scale instances up or down.

**Example**:
```
"Scale the swarm to 8 instances"
```

### 9. swarm_execute_workflow
Execute a workflow from a YAML file.

**Example**:
```
"Execute the CI workflow at examples/continuous_integration.yaml"
```

### 10. swarm_cancel_task
Cancel a pending task.

**Example**:
```
"Cancel task xyz789"
```

## 💡 Common Usage Patterns

### Pattern 1: Parallel Code Review

```
"I need a comprehensive code review. Can you:
1. Spawn 4 swarm instances
2. Review these areas in parallel:
   - Security vulnerabilities in auth/
   - Performance issues in database queries
   - Code quality in the API endpoints
   - Documentation completeness"
```

### Pattern 2: Multi-Project Testing

```
"Run tests across all my microservices in parallel:
- frontend/ - npm test
- backend/ - pytest
- api/ - go test
- worker/ - cargo test"
```

### Pattern 3: CI/CD Pipeline

```
"Execute my CI pipeline using the swarm:
1. Spawn 3 instances
2. Run the workflow at workflows/ci-pipeline.yaml
3. Monitor and report status"
```

### Pattern 4: Batch Analysis

```
"Analyze all these files for security issues in parallel:
- auth/login.py
- auth/signup.py
- api/users.py
- api/payments.py
- api/admin.py"
```

### Pattern 5: Dependency Chain

```
"I need to:
1. Build the frontend (task A)
2. Run backend tests (task B)
3. Only after both complete, deploy to staging (task C)
Can you coordinate this using the swarm with dependencies?"
```

## 🚀 Quick Start Examples

### Example 1: Simple Parallel Work

You:
```
"Spawn 2 instances and have them analyze these in parallel:
1. Check authentication for SQL injection
2. Review API endpoints for proper error handling"
```

Claude will:
1. Call `swarm_spawn_instances` with count=2
2. Call `swarm_submit_batch` with your tasks
3. Monitor with `swarm_list_tasks`
4. Report results

### Example 2: Workflow Execution

You:
```
"Execute the multi-project workflow"
```

Claude will:
1. Check status with `swarm_get_status`
2. Scale if needed with `swarm_scale`
3. Execute with `swarm_execute_workflow`
4. Monitor progress

### Example 3: Status Check

You:
```
"What's happening with my swarm right now?"
```

Claude will:
1. Call `swarm_get_status`
2. Call `swarm_list_tasks` with status filters
3. Format and present the information

## Verify Installation

After registering the MCP server and starting a new Claude Code session:
1. Open a new terminal
2. Run `claude`
3. Ask: "Can you show me the swarm status?"

## 🛠️ Configuration

The MCP server uses the configuration from:
```
config/swarm.yaml
```

You can modify:
- Max instances
- Default timeout
- Logging level
- etc.

## 📊 Monitoring

The swarm runs in the background. To monitor:

```
"Show me swarm status"
"List all running tasks"
"How many instances are active?"
```

## 🔧 Troubleshooting

### Issue: "Tool not available"

**Solution**:
1. Start a new Claude Code session
2. Check MCP settings: `cat ~/.claude/mcp_settings.json`
3. Verify server path is correct

### Issue: "Server not responding"

**Solution**:
1. Check Python is in PATH: `python --version`
2. Check dependencies: `pip list | grep fastapi`
3. Check logs in `logs/`

### Issue: "Instances not spawning"

**Solution**:
1. Verify Claude Code is installed: `claude --version`
2. Check system resources (memory, CPU)
3. Reduce max_instances in config

## 🎯 Advanced Usage

### Custom Workflows

Create YAML workflows and execute them:

```yaml
# my-workflow.yaml
name: "My Custom Workflow"
instances: 3
tasks:
  - name: "Task 1"
    prompt: "Do something"
  - name: "Task 2"
    prompt: "Do something else"
    depends_on: ["Task 1"]
```

Then ask Claude:
```
"Execute my-workflow.yaml using the swarm"
```

### Dynamic Scaling

```
"Scale the swarm based on workload:
- Start with 2 instances
- If queue depth > 10, scale to 5
- When queue clears, scale back to 2"
```

### Integration with Your Web UI

The swarm also runs an API server. Your web UI can:
1. Use the API directly (`http://localhost:8766`)
2. Monitor via WebSocket
3. Submit tasks programmatically

## 📚 Learn More

- **Architecture**: See `ARCHITECTURE.md`
- **API Reference**: Run server and visit `http://localhost:8766/docs`
- **Examples**: Check `examples/` directory
- **Quickstart**: See `QUICKSTART.md`

## 🎉 You're Ready!

Claude Swarm is now available as an MCP tool in all your Claude Code sessions. Just ask Claude to use it naturally, and it will orchestrate multiple instances for you automatically!

Try it now:
```
"Spawn 2 swarm instances and list them"
```
