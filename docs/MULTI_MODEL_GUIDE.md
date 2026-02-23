# Multi-Model Agent System Guide

Claude Swarm now supports multiple AI providers and models, allowing you to:
- Use the best model for each task
- Optimize costs by using cheaper models for simple tasks
- Run local models for privacy-sensitive work
- Leverage specialized models (GPT-4o, CodeLlama, DeepSeek Coder, etc.)

## Quick Start

### 1. Install Dependencies

```bash
# For Anthropic API support
pip install anthropic

# For OpenAI support
pip install openai

# For local models (Ollama)
# Install Ollama from https://ollama.ai
# Then pull models:
ollama pull codellama:34b
ollama pull deepseek-coder:33b
```

### 2. Set API Keys

```bash
# Anthropic
export ANTHROPIC_API_KEY="your-key-here"

# OpenAI
export OPENAI_API_KEY="your-key-here"
```

### 3. Configure Agents

Copy the example configuration:

```bash
cp config/agents.example.yaml config/agents.yaml
```

Edit `config/agents.yaml` to configure your agent pool.

## Usage Examples

### Basic Usage - Single Model

```python
from swarm.agents import ClaudeCodeAgent, AnthropicAgent, OpenAIAgent, OllamaAgent
import asyncio

async def main():
    # Use Claude Code (requires Claude Code CLI)
    agent = ClaudeCodeAgent(
        agent_id="claude-1",
        model_name="sonnet"
    )

    await agent.start()

    result = await agent.execute(
        task="Write a Python function to calculate fibonacci numbers"
    )

    print(result["output"])

    await agent.stop()

asyncio.run(main())
```

### Smart Routing - Let Router Choose Best Model

```python
from swarm.agents import (
    ClaudeCodeAgent, AnthropicAgent, OllamaAgent,
    AgentRouter, TaskPriority
)
import asyncio

async def main():
    # Create agent pool
    agents = []

    # Add Claude Sonnet (high quality)
    claude = AnthropicAgent(
        agent_id="claude-sonnet",
        model_name="claude-sonnet-4.5"
    )
    await claude.start()
    agents.append(claude)

    # Add Claude Haiku (fast & cheap)
    haiku = AnthropicAgent(
        agent_id="claude-haiku",
        model_name="claude-haiku-4"
    )
    await haiku.start()
    agents.append(haiku)

    # Add local CodeLlama (free, private)
    codellama = OllamaAgent(
        agent_id="codellama",
        model_name="codellama:34b"
    )
    await codellama.start()
    agents.append(codellama)

    # Create router
    router = AgentRouter(config={
        "performance_mode": "balanced",
        "prefer_local": False
    })

    for agent in agents:
        router.register_agent(agent)

    # Router will choose best agent for each task
    tasks = [
        {
            "task": "Fix this typo in the comment",
            "priority": TaskPriority.LOW  # Will use Haiku or local
        },
        {
            "task": "Review this code for security vulnerabilities",
            "priority": TaskPriority.CRITICAL  # Will use Sonnet
        },
        {
            "task": "Write unit tests for this function",
            "priority": TaskPriority.NORMAL  # Will balance cost/quality
        }
    ]

    for task_info in tasks:
        # Let router select best agent
        agent = router.select_agent(
            task=task_info["task"],
            priority=task_info["priority"]
        )

        if agent:
            print(f"\nTask: {task_info['task']}")
            print(f"Selected: {agent.provider.value} - {agent.model_name}")

            result = await agent.execute(task_info["task"])
            print(f"Result: {result['output'][:100]}...")

    # Cleanup
    for agent in agents:
        await agent.stop()

asyncio.run(main())
```

### Cost-Optimized Configuration

```python
router = AgentRouter(config={
    "performance_mode": "cost",  # Prioritize cheap models
    "prefer_local": True,  # Use Ollama when possible
    "cost_threshold": 0.01  # Max $0.01 per task
})

# For LOW priority tasks, router will choose:
# 1. Ollama models (free) if available
# 2. Claude Haiku ($0.25/$1.25 per 1M tokens)
# 3. GPT-3.5 Turbo if needed
```

### Quality-Optimized Configuration

```python
router = AgentRouter(config={
    "performance_mode": "quality",  # Best models only
    "prefer_local": False,
    "cost_threshold": 1.00  # Allow expensive models
})

# For CRITICAL tasks, router will choose:
# 1. Claude Opus 4.5 (best overall)
# 2. Claude Sonnet 4.5
# 3. GPT-4o
```

### Task-Specific Model Selection

```python
# Security analysis - always use best model
agent = router.select_agent(
    task="Analyze this code for SQL injection vulnerabilities",
    priority=TaskPriority.CRITICAL,
    cost_limit=None  # No cost limit for security
)

# Simple formatting - use cheapest model
agent = router.select_agent(
    task="Format this Python code with black",
    priority=TaskPriority.LOW,
    cost_limit=0.001  # Max 0.1 cents
)

# Complex refactoring - balance cost and quality
agent = router.select_agent(
    task="Refactor this class to use dependency injection",
    priority=TaskPriority.NORMAL,
    cost_limit=0.10  # Max 10 cents
)
```

## Model Comparison

### Claude Models (via Anthropic API or Claude Code)

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| Claude Opus 4.5 | 200K | Medium | $$$ | Complex reasoning, security, architecture |
| Claude Sonnet 4.5 | 200K | Fast | $$ | General coding, reviews, refactoring |
| Claude Haiku 4 | 200K | Very Fast | $ | Simple tasks, quick fixes, linting |

**Capabilities**: ⭐⭐⭐⭐⭐ (Excellent for all coding tasks)

### OpenAI Models

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| o1 | 200K | Slow | $$$$ | Complex algorithms, deep reasoning |
| o1-mini | 128K | Medium | $$ | Coding with reasoning |
| GPT-4o | 128K | Fast | $$ | General coding, fast responses |
| GPT-3.5 Turbo | 16K | Very Fast | $ | Simple tasks, high throughput |

**Capabilities**: ⭐⭐⭐⭐ (Very good for most tasks)

### Local Models (via Ollama)

| Model | Context | Speed | Cost | Best For |
|-------|---------|-------|------|----------|
| DeepSeek Coder 33B | 16K | Medium | FREE | Code generation, refactoring |
| CodeLlama 34B | 16K | Medium | FREE | General coding |
| Phind CodeLlama 34B | 16K | Medium | FREE | Code Q&A, debugging |
| WizardCoder 15B | 8K | Fast | FREE | Quick code generation |

**Capabilities**: ⭐⭐⭐ (Good for many tasks, limited context)

**Advantages**:
- ✅ No API costs
- ✅ Complete privacy (no data sent to cloud)
- ✅ No rate limits
- ✅ Works offline

**Disadvantages**:
- ❌ Requires local GPU/CPU resources
- ❌ Smaller context windows
- ❌ May be slower than API models
- ❌ Quality varies by model size

## Cost Optimization Strategies

### 1. Use Haiku for Simple Tasks

```python
# Before: Using Sonnet for everything
# Cost: ~$0.05 per 1000 tasks

# After: Use Haiku for simple tasks
# Cost: ~$0.008 per 1000 tasks (84% savings!)

# Configure router to prefer cheap models for low priority
router = AgentRouter(config={"performance_mode": "cost"})
```

### 2. Use Local Models When Possible

```python
# Run Ollama locally - zero API costs
# Good for:
# - Development/testing
# - Non-sensitive code generation
# - High-volume simple tasks

ollama_agent = OllamaAgent(
    agent_id="local-1",
    model_name="deepseek-coder:33b"
)
```

### 3. Set Cost Limits Per Task

```python
# Prevent expensive tasks
agent = router.select_agent(
    task=task,
    cost_limit=0.10  # Max 10 cents per task
)
```

### 4. Use Caching

```python
# Enable response caching for repeated queries
# (Coming soon - caches common patterns)
router = AgentRouter(config={
    "enable_caching": True
})
```

## Capability-Based Selection

The router automatically selects models based on required capabilities:

```python
# Security analysis → Claude Opus/Sonnet (best security capabilities)
agent = router.select_agent(
    task="Analyze for XSS vulnerabilities"
)

# Simple code generation → Any model with CODE_GENERATION
agent = router.select_agent(
    task="Write a hello world function"
)

# Complex refactoring → Claude Opus or o1 (best reasoning)
agent = router.select_agent(
    task="Refactor entire authentication system"
)
```

## Integration with Workflows

Use multi-model support in workflows:

```yaml
# workflow.yaml
name: "Smart Code Review"
agents:
  # Use cheap model for initial checks
  - task: "Check code formatting"
    model_preference: "haiku"

  # Use best model for security
  - task: "Security analysis"
    model_preference: "opus"

  # Use local model for tests
  - task: "Generate unit tests"
    model_preference: "ollama:deepseek-coder"

  # Let router decide for general review
  - task: "Code quality review"
    model_preference: "auto"
```

## Monitoring and Cost Tracking

```python
# Get router statistics
stats = router.get_stats()
print(f"Total agents: {stats['total_agents']}")
print(f"Available: {stats['available_agents']}")
print(f"By provider: {stats['agents_by_provider']}")

# Track costs per agent
for agent in agents:
    costs = agent.get_cost_per_token()
    print(f"{agent.model_name}: ${costs['input']}/{costs['output']} per 1M tokens")
```

## Best Practices

### 1. Match Model to Task Complexity

```python
# Simple tasks (typos, formatting)
→ Use Haiku or local models

# Standard tasks (code generation, basic reviews)
→ Use Sonnet or GPT-4o

# Complex tasks (architecture, security, algorithms)
→ Use Opus or o1

# Privacy-sensitive
→ Use local Ollama models
```

### 2. Set Appropriate Priorities

```python
TaskPriority.CRITICAL  # Security, production fixes
TaskPriority.HIGH      # Important features
TaskPriority.NORMAL    # Regular development
TaskPriority.LOW       # Formatting, docs, simple tasks
```

### 3. Configure Fallbacks

```python
# If preferred model fails, router will try alternatives
# Configure in agents.yaml:
fallback:
  claude-opus-4.5:
    - claude-sonnet-4.5
    - gpt-4o
    - codellama:34b
```

### 4. Use Local Models for Development

```python
# During development, use free local models
if os.getenv("ENV") == "development":
    router.config["prefer_local"] = True
else:
    router.config["prefer_local"] = False
```

## Troubleshooting

### Ollama Models Not Working

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Pull model if not available
ollama pull codellama:34b

# Check model list
ollama list
```

### API Authentication Errors

```bash
# Verify API keys are set
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Or set in code
agent = AnthropicAgent(
    agent_id="test",
    api_key="your-key-here"
)
```

### High Costs

```python
# Enable cost tracking
router = AgentRouter(config={
    "performance_mode": "cost",
    "cost_threshold": 0.01,  # Max per task
    "prefer_local": True
})

# Review agent selection
print(f"Selected: {agent.provider.value} - {agent.model_name}")
print(f"Estimated cost: ${router._estimate_cost(agent, tokens):.4f}")
```

## Examples

See `examples/multi_model_examples.py` for complete working examples.

## Next Steps

1. Configure your agent pool in `config/agents.yaml`
2. Set up API keys for providers you want to use
3. Install Ollama for local models
4. Run example workflows to test different models
5. Monitor costs and adjust configuration

For more information, see the [README](../README.md).
