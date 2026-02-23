"""Shared test fixtures for claude-swarm."""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from swarm.tools.base import ToolDefinition, ToolResult, ToolRegistry
from swarm.tools.builtin import register_builtin_tools


@pytest.fixture
def tool_registry():
    """Empty tool registry."""
    return ToolRegistry()


@pytest.fixture
def builtin_registry():
    """Tool registry with all built-in tools registered."""
    return register_builtin_tools()


@pytest.fixture
def sample_tool():
    """A simple async tool for testing."""

    async def _echo(text: str = "hello") -> ToolResult:
        return ToolResult(success=True, output=f"echo: {text}")

    return ToolDefinition(
        name="echo",
        description="Echoes text back",
        parameters={
            "properties": {
                "text": {"type": "string", "description": "Text to echo"},
            },
            "required": ["text"],
        },
        execute=_echo,
    )


@pytest.fixture
def failing_tool():
    """A tool that always raises."""

    async def _fail(**kwargs) -> ToolResult:
        raise ValueError("intentional test failure")

    return ToolDefinition(
        name="fail",
        description="Always fails",
        parameters={"properties": {}, "required": []},
        execute=_fail,
    )


@pytest.fixture
def tmp_workspace(tmp_path):
    """Temporary directory with some test files."""
    (tmp_path / "hello.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "data.txt").write_text("line1\nline2\nline3\n", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.py").write_text("x = 42\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def mock_model_profile():
    """Factory for mock ModelProfile objects."""

    def _make(
        name="test-model",
        quality_rating=7,
        speed_rating=8,
        context_window=32768,
        task_tags=None,
        tool_calling_quality="good",
        supports_tool_calling=True,
    ):
        profile = MagicMock()
        profile.name = name
        profile.quality_rating = quality_rating
        profile.speed_rating = speed_rating
        profile.context_window = context_window
        profile.task_tags = task_tags or ["code", "debugging"]
        profile.tool_calling_quality = tool_calling_quality
        profile.supports_tool_calling = supports_tool_calling
        return profile

    return _make
