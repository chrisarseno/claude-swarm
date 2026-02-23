#!/usr/bin/env python3
"""CLI entry point for Claude Swarm.

This module provides the ``main()`` function referenced by the
``swarm`` console-script entry point defined in setup.py.

It re-exports the Typer application that lives in ``scripts/cli.py``
so that both ``python scripts/cli.py`` and the installed ``swarm``
command invoke the same logic.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from swarm.core.orchestrator import SwarmOrchestrator
from swarm.core.task_queue import TaskPriority
from swarm.utils.config import Config, load_config
from swarm.utils.logger import setup_logging

app = typer.Typer(help="Claude Swarm CLI - Orchestrate multiple Claude Code instances")
console = Console()

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_orchestrator: Optional[SwarmOrchestrator] = None


def get_orchestrator() -> SwarmOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if not _orchestrator:
        config_path = Path("config/swarm.yaml")
        config = load_config(config_path if config_path.exists() else None)
        setup_logging(level=config.logging.level)
        _orchestrator = SwarmOrchestrator(config)
    return _orchestrator


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def start(
    instances: int = typer.Option(1, "--instances", "-n", help="Initial number of instances"),
):
    """Start the Claude Swarm orchestrator."""
    console.print("[bold green]Starting Claude Swarm...[/bold green]")

    async def _start():
        orch = get_orchestrator()
        await orch.start(initial_instances=instances)
        console.print(f"[green]Started with {instances} instance(s)[/green]")
        console.print("\nSwarm is running. Press Ctrl+C to stop.")

        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping swarm...[/yellow]")
            await orch.stop()
            console.print("[green]Swarm stopped[/green]")

    asyncio.run(_start())


@app.command()
def status():
    """Show swarm status."""
    async def _status():
        orch = get_orchestrator()
        await orch.start(initial_instances=1)
        info = await orch.get_status()
        await orch.stop()

        console.print("\n[bold]Swarm Status[/bold]")
        console.print(f"Running: {info['running']}")
        console.print(f"Workers: {info['workers']}")

        console.print(f"\n[bold]Instances ({info['instances']['total_instances']})[/bold]")
        for status_name, count in info['instances']['by_status'].items():
            console.print(f"  {status_name}: {count}")

        console.print(f"\n[bold]Tasks ({info['tasks']['total_tasks']})[/bold]")
        for status_name, count in info['tasks']['by_status'].items():
            console.print(f"  {status_name}: {count}")

    asyncio.run(_status())


@app.command()
def spawn(
    count: int = typer.Option(1, "--count", "-n", help="Number of instances to spawn"),
    directory: Optional[Path] = typer.Option(None, "--dir", "-d", help="Working directory"),
):
    """Spawn new Claude Code instances."""
    async def _spawn():
        orch = get_orchestrator()
        await orch.start(initial_instances=0)

        with console.status(f"Spawning {count} instance(s)..."):
            spawned = await orch.instance_manager.spawn_multiple(count, directory)

        console.print(f"[green]Spawned {len(spawned)} instance(s)[/green]")

        table = Table(title="Spawned Instances")
        table.add_column("Instance ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Working Directory", style="yellow")

        for inst in spawned:
            info = inst.get_info()
            table.add_row(info['id'][:8], info['status'], info['working_directory'])

        console.print(table)
        await orch.stop()

    asyncio.run(_spawn())


@app.command()
def task(
    prompt: str = typer.Argument(..., help="The prompt to send to Claude"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Task name"),
    directory: Optional[Path] = typer.Option(None, "--dir", "-d", help="Working directory"),
    priority: str = typer.Option("normal", "--priority", "-p",
                                  help="Priority (low/normal/high/critical)"),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for task to complete"),
):
    """Submit a task to the queue."""
    async def _task():
        orch = get_orchestrator()
        await orch.start(initial_instances=1)

        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "critical": TaskPriority.CRITICAL,
        }

        task_id = await orch.submit_task(
            prompt=prompt,
            name=name,
            working_directory=directory,
            priority=priority_map.get(priority.lower(), TaskPriority.NORMAL),
        )

        console.print(f"[green]Task submitted: {task_id}[/green]")

        if wait:
            with console.status("Waiting for task to complete..."):
                while True:
                    task_info = await orch.get_task_status(task_id)
                    if task_info['status'] in ('completed', 'failed', 'cancelled'):
                        break
                    await asyncio.sleep(1)

            console.print(f"\n[bold]Task Result:[/bold]")
            console.print(f"Status: {task_info['status']}")
            if task_info.get('error'):
                console.print(f"[red]Error: {task_info['error']}[/red]")

        await orch.stop()

    asyncio.run(_task())


@app.command()
def tasks(
    status_filter: Optional[str] = typer.Option(None, "--status", "-s",
                                                  help="Filter by status"),
    limit: int = typer.Option(50, "--limit", "-l",
                               help="Maximum number of tasks to show"),
):
    """List tasks."""
    async def _list_tasks():
        orch = get_orchestrator()
        await orch.start(initial_instances=0)

        from swarm.core.task_queue import TaskStatus
        status_obj = TaskStatus(status_filter) if status_filter else None

        items = await orch.list_tasks(status_obj, limit)

        table = Table(title=f"Tasks ({len(items)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="yellow")
        table.add_column("Status", style="green")
        table.add_column("Priority", style="magenta")
        table.add_column("Created", style="blue")

        for t in items:
            table.add_row(
                t['id'][:8],
                t['name'][:30],
                t['status'],
                str(t['priority']),
                t['created_at'][:19],
            )

        console.print(table)
        await orch.stop()

    asyncio.run(_list_tasks())


@app.command()
def instances():
    """List all instances."""
    async def _list_instances():
        orch = get_orchestrator()
        await orch.start(initial_instances=0)

        items = await orch.list_instances()

        table = Table(title=f"Instances ({len(items)})")
        table.add_column("ID", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Tasks", style="yellow")
        table.add_column("Errors", style="red")
        table.add_column("Working Directory", style="blue")

        for inst in items:
            table.add_row(
                inst['id'][:8],
                inst['status'],
                str(inst['completed_tasks']),
                str(inst['error_count']),
                inst['working_directory'],
            )

        console.print(table)
        await orch.stop()

    asyncio.run(_list_instances())


@app.command()
def workflow(
    path: Path = typer.Argument(..., help="Path to workflow YAML file"),
):
    """Execute a workflow from a YAML file."""
    if not path.exists():
        console.print(f"[red]Error: Workflow file not found: {path}[/red]")
        raise typer.Exit(1)

    async def _workflow():
        orch = get_orchestrator()
        await orch.start(initial_instances=1)

        console.print(f"[bold]Executing workflow: {path.name}[/bold]")

        with console.status("Running workflow..."):
            result = await orch.execute_workflow(path)

        console.print(f"[green]Workflow submitted: {result['workflow_name']}[/green]")
        console.print(f"Tasks created: {len(result['task_ids'])}")

        for wf_name, task_id in result['task_mapping'].items():
            console.print(f"  - {wf_name}: {task_id[:8]}")

        await orch.stop()

    asyncio.run(_workflow())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Entry point for the ``swarm`` console script."""
    app()


if __name__ == "__main__":
    main()
