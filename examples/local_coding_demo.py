"""
Local Coding Demo
Demonstrates various coding tasks using only local Ollama models
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.agents.ollama_manager import OllamaManager
from swarm.agents.ollama_agent import OllamaAgent


async def demo_code_generation():
    """Demo: Code generation with local models"""
    print("\n" + "=" * 70)
    print("DEMO 1: Code Generation")
    print("=" * 70)

    manager = OllamaManager()
    await manager.initialize()

    # Use DeepSeek Coder if available, otherwise use any available model
    models = await manager.list_installed_models()
    if not models:
        print("⚠️  No models installed. Run local_setup.py first.")
        return

    # Prefer DeepSeek Coder
    model_name = None
    for m in models:
        if "deepseek-coder" in m["name"]:
            model_name = m["name"]
            break

    if not model_name:
        model_name = models[0]["name"]

    print(f"Using model: {model_name}\n")

    agent = await manager.create_agent(model_name)

    tasks = [
        "Write a Python function to check if a number is prime",
        "Write a Python function to calculate factorial recursively",
        "Write a Python class for a simple Stack data structure"
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n--- Task {i}: {task} ---\n")

        result = await agent.execute(task)

        if result["success"]:
            print(result["output"])
            print("\n✓ Generated successfully")
        else:
            print(f"✗ Error: {result['error']}")

        print("\n" + "-" * 70)

    await agent.stop()
    await manager.cleanup()


async def demo_debugging():
    """Demo: Bug detection and fixing"""
    print("\n" + "=" * 70)
    print("DEMO 2: Debugging")
    print("=" * 70)

    manager = OllamaManager()
    await manager.initialize()

    # Try to use debugging specialist
    if await manager.is_model_installed("wizardcoder:7b"):
        model_name = "wizardcoder:7b"
    elif await manager.is_model_installed("deepseek-coder:6.7b"):
        model_name = "deepseek-coder:6.7b"
    else:
        models = await manager.list_installed_models()
        if not models:
            print("⚠️  No models installed.")
            return
        model_name = models[0]["name"]

    print(f"Using model: {model_name}\n")

    agent = await manager.create_agent(model_name)

    buggy_code = """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)

# This crashes when numbers is empty!
print(calculate_average([]))
"""

    print("Buggy code:")
    print(buggy_code)
    print("\nAsking AI to fix the bug...\n")

    result = await agent.execute(
        f"Find and fix the bug in this code:\n{buggy_code}"
    )

    if result["success"]:
        print("Fixed code:")
        print(result["output"])
        print("\n✓ Bug fixed!")
    else:
        print(f"✗ Error: {result['error']}")

    await agent.stop()
    await manager.cleanup()


async def demo_sql_specialist():
    """Demo: SQL generation with specialist model"""
    print("\n" + "=" * 70)
    print("DEMO 3: SQL Generation")
    print("=" * 70)

    manager = OllamaManager()
    await manager.initialize()

    # Try to use SQL specialist
    if await manager.is_model_installed("sqlcoder:7b"):
        model_name = "sqlcoder:7b"
        print("✓ Using SQL specialist model\n")
    else:
        models = await manager.list_installed_models()
        if not models:
            print("⚠️  No models installed.")
            return
        model_name = models[0]["name"]
        print(f"⚠️  SQL specialist not installed, using {model_name}\n")

    agent = await manager.create_agent(model_name)

    schema = """
Tables:
- users (id, name, email, created_at)
- orders (id, user_id, product, price, order_date)
- products (id, name, category, stock)
"""

    queries = [
        "Find top 10 users by total order value",
        "Get products with low stock (< 10)",
        "Count orders per month in 2024"
    ]

    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: {query} ---\n")

        prompt = f"Schema:\n{schema}\n\nGenerate SQL for: {query}"
        result = await agent.execute(prompt)

        if result["success"]:
            print(result["output"])
            print("\n✓ Generated")
        else:
            print(f"✗ Error: {result['error']}")

    await agent.stop()
    await manager.cleanup()


async def demo_python_specialist():
    """Demo: Python-specific tasks with specialist"""
    print("\n" + "=" * 70)
    print("DEMO 4: Python Specialist")
    print("=" * 70)

    manager = OllamaManager()
    await manager.initialize()

    # Try Python specialist
    if await manager.is_model_installed("wizardcoder-python:7b"):
        model_name = "wizardcoder-python:7b"
        print("✓ Using Python specialist model\n")
    else:
        models = await manager.list_installed_models()
        if not models:
            print("⚠️  No models installed.")
            return
        model_name = models[0]["name"]
        print(f"⚠️  Python specialist not installed, using {model_name}\n")

    agent = await manager.create_agent(model_name)

    tasks = [
        "Write a Python decorator to measure function execution time",
        "Write a context manager for database connections",
        "Write a generator function to read large files in chunks"
    ]

    for i, task in enumerate(tasks, 1):
        print(f"\n--- Task {i}: {task} ---\n")

        result = await agent.execute(task)

        if result["success"]:
            print(result["output"])
            print("\n✓ Generated")
        else:
            print(f"✗ Error: {result['error']}")

        print("\n" + "-" * 70)

    await agent.stop()
    await manager.cleanup()


async def demo_comparison():
    """Demo: Compare different models on same task"""
    print("\n" + "=" * 70)
    print("DEMO 5: Model Comparison")
    print("=" * 70)

    manager = OllamaManager()
    await manager.initialize()

    models = await manager.list_installed_models()
    if len(models) < 2:
        print("⚠️  Need at least 2 models installed for comparison")
        return

    # Take up to 3 models
    test_models = [m["name"] for m in models[:3]]
    print(f"Comparing {len(test_models)} models:\n")
    for m in test_models:
        print(f"  - {m}")

    prompt = "Write a Python function to calculate fibonacci numbers"
    print(f"\nTask: {prompt}\n")
    print("-" * 70)

    results = await manager.compare_models(test_models, prompt)

    # Show comparison
    print("\n" + "=" * 70)
    print("COMPARISON RESULTS")
    print("=" * 70)

    print(f"\n{'Model':<30} {'Time (s)':<12} {'Speed (tok/s)':<15}")
    print("-" * 70)

    for r in results:
        if r.get("success"):
            print(
                f"{r['model']:<30} "
                f"{r['duration_seconds']:<12.2f} "
                f"{r['tokens_per_second']:<15.2f}"
            )
        else:
            print(f"{r['model']:<30} Failed")

    await manager.cleanup()


async def main():
    """Run all demos"""
    demos = [
        ("Code Generation", demo_code_generation),
        ("Debugging", demo_debugging),
        ("SQL Specialist", demo_sql_specialist),
        ("Python Specialist", demo_python_specialist),
        ("Model Comparison", demo_comparison)
    ]

    print("\n" + "=" * 70)
    print("LOCAL CODING DEMOS")
    print("=" * 70)
    print("\nDemonstrating various coding tasks using FREE local models")
    print("All code stays on your machine - complete privacy!")

    print("\n\nAvailable demos:")
    for i, (name, _) in enumerate(demos, 1):
        print(f"  {i}. {name}")
    print("  0. Run all demos")

    choice = input("\nSelect demo (0-5): ").strip()

    if choice == "0":
        # Run all
        for name, demo_func in demos:
            try:
                await demo_func()
                input("\nPress Enter to continue to next demo...")
            except Exception as e:
                print(f"\n❌ Demo failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        # Run selected
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(demos):
                name, demo_func = demos[idx]
                await demo_func()
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid choice")
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            import traceback
            traceback.print_exc()

    print("\n\n" + "=" * 70)
    print("DEMOS COMPLETE")
    print("=" * 70)
    print("\n✨ All of this ran 100% locally with zero API costs!")
    print("🔒 Your code never left your machine")
    print("💰 Estimated API cost saved: $0.10-0.50")
    print("\nFor production use, set up workflows with:")
    print("  python -m swarm.cli run workflow.yaml")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo cancelled by user")
