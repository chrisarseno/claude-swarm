"""
Multi-Model Example
Demonstrates using different AI models for different tasks
"""

import asyncio
import os
from swarm.agents import (
    ClaudeCodeAgent,
    AnthropicAgent,
    OpenAIAgent,
    OllamaAgent,
    AgentRouter,
    TaskPriority,
    AgentCapability
)


async def example_single_model():
    """Example 1: Use a single model directly"""
    print("=== Example 1: Single Model ===\n")

    # Use Anthropic API with Claude Sonnet
    agent = AnthropicAgent(
        agent_id="claude-1",
        model_name="claude-sonnet-4.5",
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )

    await agent.start()

    task = "Write a Python function to reverse a string"
    print(f"Task: {task}\n")

    result = await agent.execute(task)

    if result["success"]:
        print(f"Output:\n{result['output']}\n")
        print(f"Tokens used: {result.get('usage', {})}\n")
    else:
        print(f"Error: {result['error']}\n")

    await agent.stop()


async def example_smart_routing():
    """Example 2: Let router choose best model for each task"""
    print("=== Example 2: Smart Routing ===\n")

    # Create agent pool with different models
    agents = []

    # High-quality model (Claude Sonnet)
    try:
        sonnet = AnthropicAgent(
            agent_id="sonnet",
            model_name="claude-sonnet-4.5"
        )
        await sonnet.start()
        agents.append(sonnet)
        print("✓ Claude Sonnet 4.5 ready")
    except Exception as e:
        print(f"✗ Claude Sonnet not available: {e}")

    # Fast, cheap model (Claude Haiku)
    try:
        haiku = AnthropicAgent(
            agent_id="haiku",
            model_name="claude-haiku-4"
        )
        await haiku.start()
        agents.append(haiku)
        print("✓ Claude Haiku 4 ready")
    except Exception as e:
        print(f"✗ Claude Haiku not available: {e}")

    # OpenAI model
    try:
        gpt4o = OpenAIAgent(
            agent_id="gpt4o",
            model_name="gpt-4o"
        )
        await gpt4o.start()
        agents.append(gpt4o)
        print("✓ GPT-4o ready")
    except Exception as e:
        print(f"✗ GPT-4o not available: {e}")

    # Local model (free, private)
    try:
        codellama = OllamaAgent(
            agent_id="codellama",
            model_name="codellama:7b"
        )
        await codellama.start()
        agents.append(codellama)
        print("✓ CodeLlama 7B (local) ready")
    except Exception as e:
        print(f"✗ CodeLlama not available: {e}")

    if not agents:
        print("\nNo agents available! Please configure at least one model.")
        return

    # Create router
    router = AgentRouter(config={
        "performance_mode": "balanced",
        "prefer_local": False
    })

    for agent in agents:
        router.register_agent(agent)

    print(f"\n{len(agents)} agents registered\n")

    # Different tasks with different priorities
    tasks = [
        {
            "task": "Fix typo: 'def helllo_world()' should be 'def hello_world()'",
            "priority": TaskPriority.LOW,
            "expected": "Should use cheapest/local model"
        },
        {
            "task": "Write a Python function to validate email addresses using regex",
            "priority": TaskPriority.NORMAL,
            "expected": "Should use balanced model"
        },
        {
            "task": "Analyze this code for SQL injection vulnerabilities: "
                   "cursor.execute('SELECT * FROM users WHERE id = ' + user_id)",
            "priority": TaskPriority.CRITICAL,
            "expected": "Should use best available model"
        },
        {
            "task": "Generate 5 unit test cases for a binary search function",
            "priority": TaskPriority.NORMAL,
            "expected": "Should use cost-effective model"
        }
    ]

    for i, task_info in enumerate(tasks, 1):
        print(f"\n--- Task {i} ---")
        print(f"Priority: {task_info['priority'].value}")
        print(f"Task: {task_info['task'][:80]}...")
        print(f"Expected: {task_info['expected']}")

        # Let router select best agent
        agent = router.select_agent(
            task=task_info["task"],
            priority=task_info["priority"]
        )

        if agent:
            print(f"✓ Selected: {agent.provider.value} - {agent.model_name}")

            # Estimate cost
            analysis = router.analyze_task(task_info["task"])
            cost = router._estimate_cost(agent, analysis["estimated_tokens"])
            print(f"  Estimated cost: ${cost:.4f}")

            # Execute task
            result = await agent.execute(task_info["task"])

            if result["success"]:
                output = result["output"][:200]
                print(f"  Output preview: {output}...")
            else:
                print(f"  ✗ Error: {result['error']}")
        else:
            print("✗ No suitable agent found")

    # Show router stats
    print("\n--- Router Statistics ---")
    stats = router.get_stats()
    print(f"Total agents: {stats['total_agents']}")
    print(f"Available agents: {stats['available_agents']}")
    print(f"Performance mode: {stats['performance_mode']}")
    print(f"Agents by provider:")
    for provider, count in stats['agents_by_provider'].items():
        if count > 0:
            print(f"  {provider}: {count}")

    # Cleanup
    for agent in agents:
        await agent.stop()


async def example_cost_optimization():
    """Example 3: Cost-optimized configuration"""
    print("=== Example 3: Cost Optimization ===\n")

    # Try to use local model first
    try:
        # Free local model
        agent = OllamaAgent(
            agent_id="local",
            model_name="codellama:7b"
        )
        await agent.start()
        print("✓ Using local CodeLlama (FREE)")

        task = "Write a hello world program in Python"
        result = await agent.execute(task)

        if result["success"]:
            print(f"\nOutput:\n{result['output']}\n")
            print(f"Cost: $0.00 (local model)")
        else:
            print(f"Error: {result['error']}")

        await agent.stop()

    except Exception as e:
        print(f"Local model not available: {e}")
        print("Fallback to API-based model...")

        # Fallback to cheap API model
        agent = AnthropicAgent(
            agent_id="haiku",
            model_name="claude-haiku-4"
        )
        await agent.start()
        print("✓ Using Claude Haiku (cheap API model)")

        task = "Write a hello world program in Python"
        result = await agent.execute(task)

        if result["success"]:
            print(f"\nOutput:\n{result['output']}\n")

            # Calculate actual cost
            usage = result.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            costs = agent.get_cost_per_token()
            cost = (
                (input_tokens / 1_000_000) * costs["input"] +
                (output_tokens / 1_000_000) * costs["output"]
            )
            print(f"Cost: ${cost:.6f}")

        await agent.stop()


async def example_compare_models():
    """Example 4: Compare different models on same task"""
    print("=== Example 4: Model Comparison ===\n")

    task = "Write a Python function to calculate factorial recursively"
    print(f"Task: {task}\n")

    models_to_try = [
        ("anthropic", "claude-haiku-4", "Fast & Cheap"),
        ("anthropic", "claude-sonnet-4.5", "Balanced"),
        ("openai", "gpt-4o", "Alternative")
    ]

    results = []

    for provider, model, description in models_to_try:
        print(f"\n--- Testing: {model} ({description}) ---")

        try:
            if provider == "anthropic":
                agent = AnthropicAgent(
                    agent_id=f"test-{model}",
                    model_name=model
                )
            elif provider == "openai":
                agent = OpenAIAgent(
                    agent_id=f"test-{model}",
                    model_name=model
                )
            else:
                continue

            await agent.start()

            import time
            start_time = time.time()
            result = await agent.execute(task)
            duration = time.time() - start_time

            if result["success"]:
                usage = result.get("usage", {})
                costs = agent.get_cost_per_token()

                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                cost = (
                    (input_tokens / 1_000_000) * costs["input"] +
                    (output_tokens / 1_000_000) * costs["output"]
                )

                results.append({
                    "model": model,
                    "duration": duration,
                    "cost": cost,
                    "output_length": len(result["output"]),
                    "success": True
                })

                print(f"✓ Completed in {duration:.2f}s")
                print(f"  Cost: ${cost:.6f}")
                print(f"  Output length: {len(result['output'])} chars")
                print(f"  Output preview:\n{result['output'][:200]}...\n")
            else:
                print(f"✗ Error: {result['error']}")
                results.append({
                    "model": model,
                    "success": False
                })

            await agent.stop()

        except Exception as e:
            print(f"✗ Failed: {e}")
            results.append({
                "model": model,
                "success": False,
                "error": str(e)
            })

    # Summary
    print("\n--- Comparison Summary ---")
    print(f"{'Model':<25} {'Time (s)':<12} {'Cost ($)':<12} {'Length'}")
    print("-" * 60)
    for r in results:
        if r["success"]:
            print(
                f"{r['model']:<25} "
                f"{r['duration']:<12.2f} "
                f"{r['cost']:<12.6f} "
                f"{r['output_length']}"
            )
        else:
            print(f"{r['model']:<25} Failed")


async def main():
    """Run all examples"""
    examples = [
        ("Single Model Usage", example_single_model),
        ("Smart Routing", example_smart_routing),
        ("Cost Optimization", example_cost_optimization),
        ("Model Comparison", example_compare_models)
    ]

    print("=" * 70)
    print("Multi-Model Agent Examples")
    print("=" * 70)
    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"{i}. {name}")

    print("\n" + "=" * 70 + "\n")

    # Run all examples (or comment out ones you don't want)
    for name, example_func in examples:
        try:
            await example_func()
            print("\n" + "=" * 70 + "\n")
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            break
        except Exception as e:
            print(f"\nExample failed: {e}")
            import traceback
            traceback.print_exc()
            print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    # Check for required API keys
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print("⚠️  No API keys found!")
        print("\nSet at least one:")
        print("  export ANTHROPIC_API_KEY='your-key'")
        print("  export OPENAI_API_KEY='your-key'")
        print("\nOr install Ollama for local models:")
        print("  https://ollama.ai\n")

    asyncio.run(main())
