"""
Local-First Claude Swarm Setup
Quick setup script for running entirely on local Ollama models
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from swarm.agents.ollama_manager import OllamaManager
from swarm.agents.ollama_registry import (
    print_model_catalog,
    recommend_model_for_task,
    get_model_profile
)


async def check_system():
    """Check system requirements"""
    print("\n" + "=" * 70)
    print("SYSTEM CHECK")
    print("=" * 70)

    # Check Ollama
    manager = OllamaManager()
    await manager.initialize()

    if not await manager.is_ollama_running():
        print("\n❌ Ollama is not running!")
        print("\nPlease install Ollama:")
        print("  macOS/Linux: curl -fsSL https://ollama.ai/install.sh | sh")
        print("  Windows: https://ollama.ai/download/windows")
        print("\nThen start Ollama and run this script again.")
        return None

    print("✓ Ollama is running")

    # Check installed models
    models = await manager.list_installed_models()
    print(f"✓ {len(models)} models currently installed")

    # Check VRAM (estimate)
    print("\n📊 Estimating available VRAM...")
    try:
        import subprocess
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            vram_mb = int(result.stdout.strip().split('\n')[0])
            vram_gb = vram_mb / 1024
            print(f"✓ ~{vram_gb:.1f}GB VRAM available (NVIDIA GPU)")
            return manager, int(vram_gb)
    except Exception:
        pass

    # Default assumption if can't detect
    print("⚠️  Could not detect VRAM, assuming 8GB")
    print("   Adjust in config/local-first.yaml if needed")
    return manager, 8


async def show_recommendations(max_vram: int):
    """Show model recommendations"""
    print("\n" + "=" * 70)
    print(f"RECOMMENDED MODELS FOR {max_vram}GB VRAM")
    print("=" * 70)

    use_cases = [
        ("Simple tasks (fast)", "simple coding task", True, False),
        ("General coding (balanced)", "general code generation", False, False),
        ("Complex tasks (quality)", "complex refactoring", False, True),
        ("SQL", "sql query optimization", False, False),
        ("Python", "python development", False, False),
    ]

    recommendations = {}

    for use_case, task, prefer_speed, prefer_quality in use_cases:
        print(f"\n{use_case}:")

        models = recommend_model_for_task(
            task_description=task,
            max_vram_gb=max_vram,
            prefer_speed=prefer_speed,
            prefer_quality=prefer_quality
        )

        if models:
            top_model = models[0]
            recommendations[use_case] = top_model
            print(f"  → {top_model.full_name}")
            print(f"    {top_model.description}")
            print(f"    VRAM: {top_model.vram_required.get(top_model.recommended_quant.value)}")
            print(f"    Speed: {'⚡' * top_model.speed_rating}/10")
            print(f"    Quality: {'⭐' * top_model.quality_rating}/10")

    return recommendations


async def interactive_setup(manager: OllamaManager, max_vram: int):
    """Interactive model selection and installation"""
    print("\n" + "=" * 70)
    print("INTERACTIVE SETUP")
    print("=" * 70)

    print("\nWhat would you like to do?")
    print("  1. Quick setup (recommended models)")
    print("  2. Custom setup (choose models)")
    print("  3. View full model catalog")
    print("  4. Skip setup")

    choice = input("\nChoice (1-4): ").strip()

    if choice == "1":
        # Quick setup
        print("\n📦 Setting up recommended models...")
        installed = await manager.setup_recommended_models(
            max_vram_gb=max_vram,
            count=5
        )
        print(f"\n✓ Installed {len(installed)} models")
        return installed

    elif choice == "2":
        # Custom setup
        print("\n📋 Available model categories:")
        categories = {
            "1": ("deepseek-coder:1.3b", "Tiny, very fast"),
            "2": ("deepseek-coder:6.7b", "Balanced, recommended"),
            "3": ("codellama:7b", "General purpose"),
            "4": ("sqlcoder:7b", "SQL specialist"),
            "5": ("wizardcoder-python:7b", "Python specialist"),
            "6": ("deepseek-coder:33b", "High quality (18GB)"),
            "7": ("codellama:13b", "Quality (7GB)"),
        }

        for key, (model, desc) in categories.items():
            print(f"  {key}. {model} - {desc}")

        selected = input("\nSelect models (comma-separated, e.g., 1,2,4): ").strip()
        selected_nums = [s.strip() for s in selected.split(",")]

        installed = []
        for num in selected_nums:
            if num in categories:
                model_name, _ = categories[num]
                print(f"\n📥 Installing {model_name}...")
                if await manager.ensure_model(model_name):
                    installed.append(model_name)
                    print(f"✓ {model_name} ready")
                else:
                    print(f"✗ Failed to install {model_name}")

        return installed

    elif choice == "3":
        # Show catalog
        print_model_catalog()
        return []

    else:
        # Skip
        print("\n⏭️  Skipping model installation")
        return []


async def create_agent_pool(manager: OllamaManager, max_vram: int):
    """Create specialized agent pool"""
    print("\n" + "=" * 70)
    print("CREATING AGENT POOL")
    print("=" * 70)

    choice = input("\nCreate specialized agent pool? (y/n): ").strip().lower()

    if choice == "y":
        pool = await manager.create_specialized_pool(max_vram_gb=max_vram)

        total_agents = sum(len(agents) for agents in pool.values())
        print(f"\n✓ Created {total_agents} specialized agents")

        return pool
    else:
        print("\n⏭️  Skipping agent pool creation")
        return None


async def run_tests(manager: OllamaManager):
    """Run test queries"""
    print("\n" + "=" * 70)
    print("TESTING")
    print("=" * 70)

    choice = input("\nRun test queries? (y/n): ").strip().lower()

    if choice != "y":
        print("\n⏭️  Skipping tests")
        return

    # Get available models
    models = await manager.list_installed_models()
    if not models:
        print("\n⚠️  No models installed, skipping tests")
        return

    # Use first available model
    test_model = models[0]["name"]
    print(f"\n🧪 Testing with {test_model}...")

    # Create agent
    agent = await manager.create_agent(test_model)
    if not agent:
        print("✗ Failed to create agent")
        return

    # Test queries
    tests = [
        "Write a Python function to reverse a string",
        "What is 2 + 2?",
        "Write a SQL query to find top 10 users"
    ]

    for i, test in enumerate(tests, 1):
        print(f"\n--- Test {i} ---")
        print(f"Query: {test}")

        result = await agent.execute(test)

        if result["success"]:
            output = result["output"][:200]
            print(f"Output: {output}...")
            print("✓ Success")
        else:
            print(f"✗ Error: {result['error']}")

    await agent.stop()


async def show_summary(manager: OllamaManager):
    """Show final summary"""
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)

    stats = await manager.get_model_stats()

    print(f"\n📊 Summary:")
    print(f"  Models installed: {stats['total_models']}")
    print(f"  Total size: {stats['total_size_gb']:.1f}GB")
    print(f"  Active agents: {stats['active_agents']}")

    print("\n📝 Installed models:")
    for model in stats["models"]:
        print(f"  - {model['name']} ({model['size_gb']}GB)")

    print("\n✨ You're all set!")
    print("\nNext steps:")
    print("  1. Edit config/local-first.yaml for your preferences")
    print("  2. Run example workflows: python examples/multi_model_example.py")
    print("  3. Start using: python examples/local_coding_demo.py")

    print("\n💰 Cost savings:")
    print("  API equivalent: ~$9-15/month")
    print("  Your cost: $0/month")
    print("  Yearly savings: ~$108-180")

    print("\n🔒 Privacy:")
    print("  All code stays on your machine")
    print("  No data sent to cloud")
    print("  Complete privacy")


async def main():
    """Main setup flow"""
    print("\n" + "=" * 70)
    print("CLAUDE SWARM - LOCAL-FIRST SETUP")
    print("=" * 70)
    print("\nSetup a complete AI coding swarm running entirely on your machine")
    print("Zero API costs, complete privacy, no rate limits!")

    try:
        # Check system
        result = await check_system()
        if not result:
            return
        manager, max_vram = result

        # Show recommendations
        await show_recommendations(max_vram)

        # Interactive setup
        installed = await interactive_setup(manager, max_vram)

        if not installed:
            print("\n⚠️  No models installed")
            choice = input("Would you like to see the full catalog? (y/n): ").strip().lower()
            if choice == "y":
                print_model_catalog()

        # Create agent pool
        pool = await create_agent_pool(manager, max_vram)

        # Run tests
        if installed:
            await run_tests(manager)

        # Show summary
        await show_summary(manager)

        # Cleanup
        await manager.cleanup()

        print("\n" + "=" * 70)
        print("\nHappy coding with FREE local AI! 🚀")
        print("\n" + "=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error during setup: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
