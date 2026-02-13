#!/usr/bin/env python3
"""Example: Using Claude Swarm from Python code."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from swarm.core.orchestrator import SwarmOrchestrator
from swarm.core.task_queue import TaskPriority
from swarm.utils.config import Config


async def example_basic_usage():
    """Example: Basic task submission and monitoring."""
    print("=== Basic Usage Example ===\n")

    # Create orchestrator with default config
    config = Config()
    orchestrator = SwarmOrchestrator(config)

    # Start with 2 instances
    await orchestrator.start(initial_instances=2)
    print("✓ Started orchestrator with 2 instances\n")

    # Submit some tasks
    task_ids = []

    task_id_1 = await orchestrator.submit_task(
        name="Code Review",
        prompt="Review the authentication module for security issues",
        priority=TaskPriority.HIGH
    )
    task_ids.append(task_id_1)
    print(f"✓ Submitted task 1: {task_id_1[:8]}...")

    task_id_2 = await orchestrator.submit_task(
        name="Performance Analysis",
        prompt="Analyze database queries for N+1 issues",
        priority=TaskPriority.NORMAL
    )
    task_ids.append(task_id_2)
    print(f"✓ Submitted task 2: {task_id_2[:8]}...")

    # Monitor until complete
    print("\nWaiting for tasks to complete...")
    completed = 0
    while completed < len(task_ids):
        await asyncio.sleep(2)

        status = await orchestrator.get_status()
        completed = status['tasks']['by_status'].get('completed', 0)
        running = status['tasks']['by_status'].get('running', 0)

        print(f"  Status: {running} running, {completed} completed")

    # Get results
    print("\nTask Results:")
    for task_id in task_ids:
        task_info = await orchestrator.get_task_status(task_id)
        print(f"\n  Task: {task_info['name']}")
        print(f"  Status: {task_info['status']}")
        if task_info.get('duration_seconds'):
            print(f"  Duration: {task_info['duration_seconds']:.1f}s")

    await orchestrator.stop()
    print("\n✓ Orchestrator stopped")


async def example_batch_processing():
    """Example: Batch task processing."""
    print("\n=== Batch Processing Example ===\n")

    config = Config()
    orchestrator = SwarmOrchestrator(config)

    await orchestrator.start(initial_instances=3)
    print("✓ Started orchestrator with 3 instances\n")

    # Submit batch of tasks
    prompts = [
        "Review error handling in API endpoints",
        "Check for SQL injection vulnerabilities",
        "Analyze memory usage patterns",
        "Review logging practices",
        "Check input validation"
    ]

    print(f"Submitting {len(prompts)} tasks...")
    task_ids = await orchestrator.submit_batch(prompts)
    print(f"✓ Submitted {len(task_ids)} tasks\n")

    # Monitor progress
    while True:
        status = await orchestrator.get_status()
        tasks_status = status['tasks']['by_status']

        if tasks_status.get('completed', 0) + tasks_status.get('failed', 0) == len(task_ids):
            break

        print(f"Progress: {tasks_status.get('completed', 0)}/{len(task_ids)} completed")
        await asyncio.sleep(3)

    print(f"\n✓ All tasks completed")

    await orchestrator.stop()


async def example_with_dependencies():
    """Example: Tasks with dependencies."""
    print("\n=== Task Dependencies Example ===\n")

    config = Config()
    orchestrator = SwarmOrchestrator(config)

    await orchestrator.start(initial_instances=2)
    print("✓ Started orchestrator\n")

    # Task 1: Setup
    task1_id = await orchestrator.submit_task(
        name="Setup Test Environment",
        prompt="Create a test database and seed it with sample data"
    )
    print(f"✓ Submitted Task 1 (Setup): {task1_id[:8]}...")

    # Task 2: Depends on Task 1
    task2_id = await orchestrator.submit_task(
        name="Run Tests",
        prompt="Run all integration tests against the test database",
        depends_on=[task1_id]
    )
    print(f"✓ Submitted Task 2 (Tests): {task2_id[:8]}... [depends on Task 1]")

    # Task 3: Also depends on Task 1
    task3_id = await orchestrator.submit_task(
        name="Performance Test",
        prompt="Run performance benchmarks on the test database",
        depends_on=[task1_id]
    )
    print(f"✓ Submitted Task 3 (Performance): {task3_id[:8]}... [depends on Task 1]")

    # Task 4: Depends on Tasks 2 and 3
    task4_id = await orchestrator.submit_task(
        name="Generate Report",
        prompt="Generate a comprehensive test report including results and performance metrics",
        depends_on=[task2_id, task3_id]
    )
    print(f"✓ Submitted Task 4 (Report): {task4_id[:8]}... [depends on Tasks 2 & 3]")

    print("\nExecution order:")
    print("  1. Task 1 (Setup) runs first")
    print("  2. Tasks 2 & 3 run in parallel after Task 1")
    print("  3. Task 4 runs after both Tasks 2 & 3 complete")

    # Monitor
    all_tasks = [task1_id, task2_id, task3_id, task4_id]
    print("\nMonitoring execution...")

    while True:
        all_done = True
        for task_id in all_tasks:
            task_info = await orchestrator.get_task_status(task_id)
            if task_info['status'] not in ['completed', 'failed']:
                all_done = False
                break

        if all_done:
            break

        await asyncio.sleep(2)

    print("\n✓ All tasks with dependencies completed")

    await orchestrator.stop()


async def example_scaling():
    """Example: Dynamic instance scaling."""
    print("\n=== Dynamic Scaling Example ===\n")

    config = Config()
    orchestrator = SwarmOrchestrator(config)

    # Start with 1 instance
    await orchestrator.start(initial_instances=1)
    print("✓ Started with 1 instance\n")

    # Submit many tasks
    print("Submitting 20 tasks...")
    task_ids = await orchestrator.submit_batch([
        f"Task {i}: Analyze module X"
        for i in range(20)
    ])
    print(f"✓ Submitted {len(task_ids)} tasks\n")

    # Scale up to handle the load
    print("Scaling up to 5 instances...")
    await orchestrator.scale_instances(5)
    instances = await orchestrator.list_instances()
    print(f"✓ Now running {len(instances)} instances\n")

    # Wait for half to complete
    while True:
        status = await orchestrator.get_status()
        completed = status['tasks']['by_status'].get('completed', 0)
        if completed >= len(task_ids) // 2:
            break
        await asyncio.sleep(2)

    # Scale down
    print(f"Half done. Scaling down to 2 instances...")
    await orchestrator.scale_instances(2)
    instances = await orchestrator.list_instances()
    print(f"✓ Now running {len(instances)} instances\n")

    # Wait for all to complete
    while True:
        status = await orchestrator.get_status()
        completed = status['tasks']['by_status'].get('completed', 0)
        if completed == len(task_ids):
            break
        print(f"Progress: {completed}/{len(task_ids)}")
        await asyncio.sleep(3)

    print(f"\n✓ All tasks completed")

    await orchestrator.stop()


async def main():
    """Run all examples."""
    try:
        # Run examples
        await example_basic_usage()
        await asyncio.sleep(1)

        await example_batch_processing()
        await asyncio.sleep(1)

        await example_with_dependencies()
        await asyncio.sleep(1)

        await example_scaling()

        print("\n" + "="*50)
        print("All examples completed successfully! 🎉")
        print("="*50)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run specific example or all
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        if example_name == "basic":
            asyncio.run(example_basic_usage())
        elif example_name == "batch":
            asyncio.run(example_batch_processing())
        elif example_name == "dependencies":
            asyncio.run(example_with_dependencies())
        elif example_name == "scaling":
            asyncio.run(example_scaling())
        else:
            print(f"Unknown example: {example_name}")
            print("Available: basic, batch, dependencies, scaling")
    else:
        asyncio.run(main())
