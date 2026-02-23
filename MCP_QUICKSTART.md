> For the full MCP integration guide, see [MCP_INTEGRATION.md](MCP_INTEGRATION.md).

# Using Claude Swarm via MCP - 2 Minute Guide

Claude Swarm is now available as a tool in Claude Code! No need to run separate servers or manage APIs - just ask Claude to use it.

## ✅ Setup Status

**The MCP server is already registered!** It was added to:
```
~/.claude/mcp_settings.json
```

## 🎯 Try It Now

### Step 1: Start a New Claude Session

Open a new terminal and run:
```bash
claude
```

### Step 2: Ask Claude to Use the Swarm

Try these examples:

#### Example 1: Simple Status Check
```
You: "What's the status of my Claude Swarm?"
```

Claude will call `swarm_get_status` and show you the current state.

#### Example 2: Spawn Instances
```
You: "Spawn 3 Claude instances in the swarm"
```

Claude will call `swarm_spawn_instances` with count=3.

#### Example 3: Submit Parallel Tasks
```
You: "I need to analyze three files in parallel:
1. Check auth/login.py for security issues
2. Review api/users.py for performance
3. Analyze database/queries.py for optimizations"
```

Claude will:
1. Check if instances are available
2. Spawn more if needed
3. Submit tasks using `swarm_submit_batch`
4. Monitor and report results

#### Example 4: Execute a Workflow
```
You: "Execute the CI pipeline workflow at
examples/continuous_integration.yaml"
```

Claude will orchestrate the entire workflow with dependencies.

## 🔧 Common Commands

### Check Status
```
"Show me the swarm status"
"How many instances are running?"
"List all tasks"
```

### Spawn Instances
```
"Spawn 5 instances"
"Create 3 more swarm instances"
"Add 2 Claude instances to the pool"
```

### Submit Tasks
```
"Submit this task to the swarm: [your task]"
"Run these tasks in parallel: [task list]"
"Execute a high-priority task: [task]"
```

### Scale
```
"Scale the swarm to 8 instances"
"Reduce swarm to 2 instances"
```

### Monitor
```
"Show all running tasks"
"List completed tasks"
"Get status of task abc123"
```

## 💡 Use Cases

### Use Case 1: Code Review
```
"Review my codebase in parallel. Check:
- Security issues in authentication
- Performance in database queries
- Code quality in API endpoints
- Documentation completeness"
```

### Use Case 2: Testing
```
"Run tests across all my projects:
- frontend: npm test
- backend: pytest
- api: go test"
```

### Use Case 3: Multi-File Analysis
```
"Analyze these 10 files for bugs in parallel"
[list files]
```

### Use Case 4: CI/CD
```
"Execute my CI workflow using the swarm"
```

## 🎨 Natural Language

You don't need to know the exact tool names! Just describe what you want:

❌ Don't say:
```
"Call swarm_spawn_instances with count 3"
```

✅ Instead say:
```
"Create 3 swarm instances"
```

Claude will figure out which tools to use!

## 🔍 Verification

To verify it's working, ask:
```
"List all available MCP tools"
```

You should see tools like:
- swarm_spawn_instances
- swarm_submit_task
- swarm_get_status
- etc.

## 📊 Example Session

```
You: "I need help with parallel code analysis"

Claude: "I can use the Claude Swarm to help! Let me check its status first."
[calls swarm_get_status]

Claude: "The swarm is running with 2 instances. What would you like to analyze?"

You: "Review these modules for security: auth/, api/, database/"

Claude: "I'll spawn one more instance and distribute the security reviews."
[calls swarm_spawn_instances and swarm_submit_batch]

Claude: "Tasks submitted! I'm monitoring progress..."
[calls swarm_list_tasks periodically]

Claude: "All reviews complete! Here are the findings..."
```

## 🛠️ Configuration

The swarm uses settings from:
```
config/swarm.yaml
```

You can modify:
- `max_instances`: Max parallel instances (default: 10)
- `default_timeout`: Task timeout (default: 300s)
- `logging.level`: Log verbosity

## 📚 Learn More

- **Full MCP Guide**: [MCP_INTEGRATION.md](MCP_INTEGRATION.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Examples**: [examples/](examples/)
- **API Docs**: Start server and visit http://localhost:8765/docs

## 🎉 That's It!

You're ready to use Claude Swarm! Just ask Claude naturally and it will orchestrate multiple instances for you automatically.

**Pro tip**: The swarm is most useful when you have multiple independent tasks that can run in parallel. Think: testing multiple projects, reviewing multiple files, or running different analysis passes.

---

**Next**: Try it in your next Claude Code session! Just ask Claude to use the swarm.
