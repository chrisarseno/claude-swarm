
# Local-First Claude Swarm Guide

Run a complete AI coding swarm **entirely on your machine** with **zero API costs** and **complete privacy**.

## Why Local-First?

### ✅ Benefits

- **$0.00 Cost**: No API fees, completely free
- **Complete Privacy**: Code never leaves your machine
- **No Rate Limits**: Use as much as you want
- **Works Offline**: No internet required
- **Customizable**: Run any open-source model
- **Fast**: No network latency
- **Eco-Friendly**: No data center energy

### 💰 Cost Comparison

**API-Based (100 tasks/day):**
- Claude Haiku: ~$0.90/month
- Claude Sonnet: ~$9/month
- GPT-4o: ~$15/month

**Local-First:**
- **$0/month** ✨

**Yearly Savings: $108-$180**

## Hardware Requirements

### Minimum (Entry Level)
- **GPU**: 4GB VRAM (GTX 1650, RTX 3050)
- **RAM**: 8GB system RAM
- **Storage**: 10GB for models
- **Models**: 1-2 small models (1-7B params)

### Recommended (Standard)
- **GPU**: 8-12GB VRAM (RTX 3060, RTX 4060)
- **RAM**: 16GB system RAM
- **Storage**: 50GB for models
- **Models**: 5-7 models (mix of sizes)

### High-End (Enthusiast)
- **GPU**: 16-24GB VRAM (RTX 4090, RTX 3090)
- **RAM**: 32GB system RAM
- **Storage**: 100GB for models
- **Models**: 10+ models including large ones

### Apple Silicon
- **M1/M2/M3 Macs**: Use unified memory
- **8GB**: 1-2 small models
- **16GB**: 5-7 models
- **32GB+**: 10+ models including large ones

### CPU-Only (Slower)
- Works but 10-50x slower
- Usable for occasional tasks
- Not recommended for heavy use

## Quick Start

### 1. Install Ollama

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from https://ollama.ai/download/windows

### 2. Verify Installation

```bash
ollama --version
ollama list  # Should show no models initially
```

### 3. Setup Claude Swarm

```bash
# Install Claude Swarm
cd claude-swarm

# Run local setup
python -m swarm setup-local

# Or use the quick setup script
python examples/local_setup.py
```

This will:
1. Check your available VRAM
2. Recommend appropriate models
3. Automatically download models
4. Create specialized agent pool
5. Run test benchmarks

### 4. Start Using

```python
from swarm.agents import OllamaManager
import asyncio

async def main():
    # Quick setup
    manager = await setup_local_swarm(max_vram_gb=8)

    # Use specialized agents
    result = await manager.agents["balanced-1"].execute(
        "Write a Python function to sort a list"
    )

    print(result["output"])

asyncio.run(main())
```

## Model Catalog

### Tier 1: Fast & Light (< 2GB VRAM)

**DeepSeek Coder 1.3B** - Ultra-fast for simple tasks
- Size: 1GB VRAM
- Speed: ⚡⚡⚡⚡⚡ 10/10
- Quality: ⭐⭐⭐⭐⭐⭐ 6/10
- Best for: Code completion, simple functions, syntax fixes

```bash
ollama pull deepseek-coder:1.3b
```

### Tier 2: Balanced (4-7GB VRAM)

**DeepSeek Coder 6.7B** - Best overall value
- Size: 4GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡⚡⚡ 8/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐ 7/10
- Best for: General coding, reviews, bug fixing

```bash
ollama pull deepseek-coder:6.7b
```

**Code Llama 7B** - Meta's general code model
- Size: 4GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡⚡⚡ 8/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐ 7/10
- Best for: Multi-language, explanations

```bash
ollama pull codellama:7b
```

**WizardCoder Python 7B** - Python specialist
- Size: 4GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡⚡⚡ 8/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐ 8/10
- Best for: Python development, Django, Flask

```bash
ollama pull wizardcoder-python:7b
```

**SQLCoder 7B** - SQL specialist
- Size: 4GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡⚡⚡ 8/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐⭐ 9/10
- Best for: SQL queries, database design

```bash
ollama pull sqlcoder:7b
```

**Mistral 7B** - Excellent general model
- Size: 4GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡⚡⚡⚡ 9/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐ 7/10
- Best for: Quick tasks, documentation, analysis

```bash
ollama pull mistral:7b
```

### Tier 3: Quality (7-15GB VRAM)

**Code Llama 13B** - Larger, better reasoning
- Size: 7GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡ 6/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐ 8/10
- Best for: Complex algorithms, detailed reviews

```bash
ollama pull codellama:13b
```

**WizardCoder 13B** - Instruction-tuned
- Size: 7GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡ 6/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐ 7/10
- Best for: Complex tasks, multi-step instructions

```bash
ollama pull wizardcoder:13b
```

**StarCoder2 15B** - Latest StarCoder
- Size: 8GB VRAM
- Speed: ⚡⚡⚡⚡⚡⚡ 6/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐ 8/10
- Best for: Production code, modern patterns

```bash
ollama pull starcoder2:15b
```

### Tier 4: Premium (18GB+ VRAM)

**DeepSeek Coder 33B** - Highest quality code model
- Size: 18GB VRAM (Q4)
- Speed: ⚡⚡⚡⚡⚡ 5/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐⭐ 9/10
- Best for: Complex refactoring, architecture, security

```bash
ollama pull deepseek-coder:33b
```

**Code Llama 34B** - Largest Code Llama
- Size: 18GB VRAM (Q4)
- Speed: ⚡⚡⚡⚡ 4/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐⭐ 9/10
- Best for: Critical code, architecture design

```bash
ollama pull codellama:34b
```

**Phind Code Llama 34B** - Fine-tuned for Q&A
- Size: 18GB VRAM (Q4)
- Speed: ⚡⚡⚡⚡ 4/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐ 8/10
- Best for: Debugging, code explanation, Q&A

```bash
ollama pull phind-codellama:34b
```

**Mixtral 8x7B** - Mixture of Experts
- Size: 26GB VRAM (Q4)
- Speed: ⚡⚡⚡⚡ 4/10
- Quality: ⭐⭐⭐⭐⭐⭐⭐⭐⭐ 9/10
- Best for: Complex problems, large context (32K)

```bash
ollama pull mixtral:8x7b
```

## Recommended Setups

### Setup 1: Budget (4-6GB VRAM)

**~5GB total**

```bash
# Fast for simple tasks (1GB)
ollama pull deepseek-coder:1.3b

# Balanced for general coding (4GB)
ollama pull deepseek-coder:6.7b
```

**Use case**: Solo developer, moderate usage

### Setup 2: Standard (8-12GB VRAM)

**~20GB total**

```bash
# Fast (1GB)
ollama pull deepseek-coder:1.3b

# Balanced (4GB each)
ollama pull deepseek-coder:6.7b
ollama pull codellama:7b
ollama pull sqlcoder:7b
ollama pull wizardcoder-python:7b
```

**Use case**: Professional development, heavy usage

### Setup 3: High-End (16-24GB VRAM)

**~45GB total**

```bash
# Fast (1GB)
ollama pull deepseek-coder:1.3b

# Balanced (4GB each)
ollama pull deepseek-coder:6.7b
ollama pull codellama:7b

# Quality (18GB + 7GB)
ollama pull deepseek-coder:33b
ollama pull codellama:13b

# Specialized (4GB each)
ollama pull sqlcoder:7b
ollama pull wizardcoder-python:7b
```

**Use case**: Team environments, complex projects

### Setup 4: Maximum (32GB+ VRAM)

**~80GB total**

```bash
# Full suite including Mixtral 8x7B (26GB)
# All models from Setup 3 plus:
ollama pull mixtral:8x7b
ollama pull llama3:70b  # If 40GB+ VRAM
```

**Use case**: Research, experimentation, maximum quality

## Configuration

### Edit config/local-first.yaml

```yaml
# Set your VRAM limit
system:
  max_vram_gb: 8  # Adjust for your GPU

# Enable appropriate VRAM profile
vram_profiles:
  medium_vram:
    enable: true  # For 8-12GB VRAM
```

### Customize Agent Pool

```yaml
agents:
  # Add more of your favorite models
  - id: "custom-1"
    model: "your-model:tag"
    count: 1
    priority_for:
      - your_use_case
```

## Usage Patterns

### Pattern 1: Task-Based Selection

```python
from swarm.agents import OllamaManager, recommend_model_for_task

manager = await OllamaManager().initialize()

# Get recommendation for task
models = recommend_model_for_task(
    "Write SQL query to find top customers",
    max_vram_gb=8
)

# Use recommended model
agent = await manager.create_agent(models[0].name)
result = await agent.execute("SELECT ...")
```

### Pattern 2: Specialized Pool

```python
# Create specialized pool
pool = await manager.create_specialized_pool(max_vram_gb=8)

# Use specialized agents
sql_result = await pool["sql"][0].execute("CREATE TABLE ...")
python_result = await pool["python"][0].execute("def hello()...")
debug_result = await pool["debug"][0].execute("Fix this bug...")
```

### Pattern 3: Workflow Integration

```yaml
# workflow.yaml
tasks:
  - name: "Quick Syntax Check"
    agent: "deepseek-coder:1.3b"  # Fast

  - name: "Generate Code"
    agent: "deepseek-coder:6.7b"  # Balanced

  - name: "Security Review"
    agent: "deepseek-coder:33b"  # Quality (if available)
```

## Performance Tips

### 1. Keep Models Loaded

```yaml
model_management:
  keep_loaded: true  # Faster inference, uses more VRAM
  unload_after_seconds: 3600  # Unload after 1 hour idle
```

### 2. Use Quantization

- **Q4**: Best balance (recommended)
- **Q5**: Slightly better quality
- **Q8**: High quality, 2x size
- **Q2**: Smallest, lowest quality

```bash
# Pull specific quantization
ollama pull deepseek-coder:6.7b-q4
ollama pull deepseek-coder:6.7b-q5
ollama pull deepseek-coder:6.7b-q8
```

### 3. Optimize Context Length

```python
# Use shorter context for faster responses
agent.config["max_tokens"] = 2048  # Instead of 4096
```

### 4. Parallel Execution

```python
# Run multiple models in parallel
results = await asyncio.gather(
    agent1.execute(task1),
    agent2.execute(task2),
    agent3.execute(task3)
)
```

## Benchmarking

### Compare Your Models

```python
from swarm.agents import OllamaManager

manager = await OllamaManager().initialize()

# Benchmark models
results = await manager.compare_models([
    "deepseek-coder:1.3b",
    "deepseek-coder:6.7b",
    "codellama:7b"
])

# See performance
for r in results:
    print(f"{r['model']}: {r['tokens_per_second']} tokens/sec")
```

### Expected Performance

| Model | GPU | Tokens/Second |
|-------|-----|---------------|
| DeepSeek 1.3B | RTX 3060 | ~100 |
| DeepSeek 6.7B | RTX 3060 | ~40 |
| Code Llama 7B | RTX 3060 | ~35 |
| DeepSeek 33B | RTX 4090 | ~20 |
| Mixtral 8x7B | RTX 4090 | ~15 |

## Troubleshooting

### Models Not Found

```bash
# List installed models
ollama list

# Pull missing model
ollama pull model-name

# Remove old models
ollama rm model-name
```

### Out of VRAM

```bash
# Use smaller quantization
ollama pull deepseek-coder:6.7b-q4  # Instead of q8

# Use smaller model
ollama pull deepseek-coder:1.3b  # Instead of 6.7b

# Reduce concurrent tasks in config
```

### Slow Performance

```bash
# Check GPU usage
nvidia-smi  # Should show high GPU usage

# Use GPU acceleration
# Ollama automatically uses GPU if available

# Check CPU vs GPU
# CPU-only will be MUCH slower
```

### Model Updates

```bash
# Check for updates
ollama list

# Update model
ollama pull model-name

# Will download only changed layers
```

## Best Practices

### 1. Start Small

Begin with 2-3 models:
- 1 fast model (1.3B)
- 1 balanced model (6.7B)
- 1 specialized model (SQL/Python)

### 2. Specialize

Use the right model for each task:
- SQL tasks → sqlcoder
- Python → wizardcoder-python
- General → deepseek-coder/codellama

### 3. Monitor VRAM

```python
# Check VRAM usage
import subprocess
result = subprocess.run(['nvidia-smi'], capture_output=True)
print(result.stdout.decode())
```

### 4. Experiment

Try different models for your use case:
- Benchmark on your tasks
- Compare quality vs speed
- Find your preferred models

## Advanced: Custom Models

### Pull from HuggingFace

```bash
# Ollama can import GGUF models
ollama create my-model -f Modelfile

# Modelfile:
FROM ./path/to/model.gguf
```

### Fine-tune Models

Use Ollama with custom fine-tuned models:
1. Fine-tune on HuggingFace/local
2. Convert to GGUF format
3. Import to Ollama

## Community Models

Explore https://ollama.ai/library for more models:

- `dolphin-coder` - Uncensored code model
- `openchat` - ChatGPT alternative
- `neural-chat` - Intel's model
- `stablelm` - Stability AI model
- Many more!

## FAQ

**Q: Can I use CPU-only?**
A: Yes, but 10-50x slower. Not recommended for heavy use.

**Q: How much disk space?**
A: 5-10GB per 7B model, 20-30GB per 33B model.

**Q: Can models run simultaneously?**
A: Yes! Run multiple small models or 1-2 large models.

**Q: Which model is best?**
A: For general use: DeepSeek Coder 6.7B (best balance).

**Q: How do I save costs?**
A: Use local models exclusively - $0 forever!

**Q: Can I switch between local and API?**
A: Yes! Claude Swarm supports both seamlessly.

## Next Steps

1. ✅ Install Ollama
2. ✅ Run `python examples/local_setup.py`
3. ✅ Pull your first models
4. ✅ Run example workflows
5. ✅ Customize for your needs
6. ✅ Start coding with FREE AI!

## Resources

- **Ollama**: https://ollama.ai
- **Model Library**: https://ollama.ai/library
- **DeepSeek Coder**: https://github.com/deepseek-ai/DeepSeek-Coder
- **Code Llama**: https://ai.meta.com/code-llama
- **Community**: https://discord.gg/ollama

---

**Welcome to FREE, PRIVATE, LOCAL AI coding!** 🎉

No API keys, no costs, no limits, no data leaving your machine.

Just install, pull models, and start coding!
