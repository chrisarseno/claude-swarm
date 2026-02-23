"""Tests for the ReAct agent loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from swarm.tools.base import ToolDefinition, ToolResult, ToolRegistry
from swarm.tools.agent_loop import AgentLoop, AgentLoopResult, ToolCallEvent
from swarm.tools.backends import OllamaToolFormatter, GenericToolFormatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_registry_with_echo():
    """Create a registry with a simple echo tool."""

    async def _echo(text: str = "hello") -> ToolResult:
        return ToolResult(success=True, output=f"echo: {text}")

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="echo",
        description="Echo text",
        parameters={
            "properties": {"text": {"type": "string", "description": "Text"}},
            "required": ["text"],
        },
        execute=_echo,
    ))
    return registry


def ollama_response(content: str, tool_calls=None):
    """Build an Ollama-style response dict."""
    msg = {"content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"message": msg}


def ollama_tool_call(name: str, arguments: dict):
    """Build an Ollama tool call entry."""
    return {"function": {"name": name, "arguments": arguments}}


# =============================================================================
# Dataclasses
# =============================================================================


class TestToolCallEvent:
    def test_defaults(self):
        result = ToolResult(success=True, output="ok")
        event = ToolCallEvent(iteration=1, tool_name="echo", arguments={"text": "hi"}, result=result)
        assert event.duration_ms == 0.0
        assert event.tool_name == "echo"


class TestAgentLoopResult:
    def test_defaults(self):
        r = AgentLoopResult(response="done")
        assert r.tool_calls == []
        assert r.iterations == 0
        assert r.stopped_reason == ""


# =============================================================================
# _extract_text
# =============================================================================


class TestExtractText:
    @pytest.fixture
    def loop(self):
        return AgentLoop(
            tool_registry=ToolRegistry(),
            formatter=OllamaToolFormatter(),
            send_fn=AsyncMock(),
        )

    def test_ollama_format(self, loop):
        resp = {"message": {"content": "Hello from Ollama"}}
        assert loop._extract_text(resp) == "Hello from Ollama"

    def test_plain_response(self, loop):
        resp = {"response": "plain text"}
        assert loop._extract_text(resp) == "plain text"

    def test_openai_format(self, loop):
        resp = {"choices": [{"message": {"content": "openai text"}}]}
        assert loop._extract_text(resp) == "openai text"

    def test_claude_format(self, loop):
        resp = {"content": [{"type": "text", "text": "claude text"}]}
        assert loop._extract_text(resp) == "claude text"

    def test_claude_multiple_text_blocks(self, loop):
        resp = {"content": [
            {"type": "text", "text": "first"},
            {"type": "tool_use", "name": "x"},
            {"type": "text", "text": "second"},
        ]}
        assert loop._extract_text(resp) == "first\nsecond"

    def test_empty_response(self, loop):
        assert loop._extract_text({}) == ""

    def test_empty_message(self, loop):
        assert loop._extract_text({"message": {}}) == ""


# =============================================================================
# _build_assistant_message
# =============================================================================


class TestBuildAssistantMessage:
    @pytest.fixture
    def loop(self):
        return AgentLoop(
            tool_registry=ToolRegistry(),
            formatter=OllamaToolFormatter(),
            send_fn=AsyncMock(),
        )

    def test_ollama_with_tool_calls(self, loop):
        resp = {
            "message": {
                "content": "I'll use echo",
                "tool_calls": [{"function": {"name": "echo", "arguments": {}}}],
            }
        }
        msg = loop._build_assistant_message(resp, "I'll use echo")
        assert msg["role"] == "assistant"
        assert "tool_calls" in msg

    def test_generic_text_only(self, loop):
        resp = {"message": "plain text without tool_calls key"}
        msg = loop._build_assistant_message(resp, "the extracted text")
        assert msg["role"] == "assistant"
        assert msg["content"] == "the extracted text"


# =============================================================================
# run() — full loop
# =============================================================================


class TestAgentLoopRun:
    @pytest.mark.asyncio
    async def test_no_tool_calls_returns_immediately(self):
        """When LLM returns plain text, loop ends in 1 iteration."""
        send_fn = AsyncMock(return_value=ollama_response("Final answer"))
        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
        )

        result = await loop.run("What is 2+2?")
        assert result.response == "Final answer"
        assert result.iterations == 1
        assert result.tool_calls == []
        assert result.stopped_reason == "complete"

    @pytest.mark.asyncio
    async def test_single_tool_call(self):
        """LLM calls a tool once, then returns final answer."""
        call_count = 0

        async def send_fn(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ollama_response(
                    "I'll echo something",
                    tool_calls=[ollama_tool_call("echo", {"text": "world"})],
                )
            return ollama_response("The echo returned: echo: world")

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
        )

        result = await loop.run("Echo world for me")
        assert result.iterations == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "echo"
        assert result.tool_calls[0].result.output == "echo: world"
        assert result.stopped_reason == "complete"

    @pytest.mark.asyncio
    async def test_max_iterations_hit(self):
        """LLM keeps calling tools until max iterations."""

        async def send_fn(messages, tools):
            return ollama_response(
                "calling echo",
                tool_calls=[ollama_tool_call("echo", {"text": "again"})],
            )

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
            max_iterations=3,
        )

        result = await loop.run("Keep echoing")
        assert result.iterations == 3
        assert result.stopped_reason == "max_iterations"
        assert len(result.tool_calls) == 3

    @pytest.mark.asyncio
    async def test_system_prompt_included(self):
        """System prompt is prepended to messages."""
        captured_messages = []

        async def send_fn(messages, tools):
            captured_messages.extend(messages)
            return ollama_response("done")

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
            system_prompt="You are a helpful assistant.",
        )

        await loop.run("hello")
        assert captured_messages[0]["role"] == "system"
        assert "helpful assistant" in captured_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_generic_formatter_injects_tools_in_system(self):
        """GenericToolFormatter appends tool docs to system prompt."""
        captured_messages = []

        async def send_fn(messages, tools):
            captured_messages.extend(messages)
            return {"message": {"content": "done"}}

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=GenericToolFormatter(),
            send_fn=send_fn,
            system_prompt="Base system prompt.",
        )

        await loop.run("hello")
        system_msg = captured_messages[0]["content"]
        assert "Base system prompt" in system_msg
        assert "echo" in system_msg
        assert "<tool_call>" in system_msg

    @pytest.mark.asyncio
    async def test_on_tool_call_callback(self):
        """on_tool_call callback fires for each tool execution."""
        events = []
        call_count = 0

        async def send_fn(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ollama_response(
                    "calling",
                    tool_calls=[ollama_tool_call("echo", {"text": "hi"})],
                )
            return ollama_response("done")

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
            on_tool_call=lambda e: events.append(e),
        )

        await loop.run("test")
        assert len(events) == 1
        assert events[0].tool_name == "echo"

    @pytest.mark.asyncio
    async def test_on_tool_call_exception_ignored(self):
        """Exceptions in on_tool_call don't break the loop."""
        call_count = 0

        async def send_fn(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ollama_response(
                    "calling",
                    tool_calls=[ollama_tool_call("echo", {"text": "hi"})],
                )
            return ollama_response("done")

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
            on_tool_call=lambda e: (_ for _ in ()).throw(RuntimeError("oops")),
        )

        # Should not raise
        result = await loop.run("test")
        assert result.stopped_reason == "complete"

    @pytest.mark.asyncio
    async def test_duration_tracked(self):
        """Total duration is positive."""
        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=AsyncMock(return_value=ollama_response("done")),
        )
        result = await loop.run("test")
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_unknown_tool_handled(self):
        """If LLM calls a tool that doesn't exist, error result is returned."""
        call_count = 0

        async def send_fn(messages, tools):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return ollama_response(
                    "calling nonexistent",
                    tool_calls=[ollama_tool_call("nonexistent_tool", {})],
                )
            return ollama_response("done")

        loop = AgentLoop(
            tool_registry=make_registry_with_echo(),
            formatter=OllamaToolFormatter(),
            send_fn=send_fn,
        )

        result = await loop.run("test")
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].result.success is False
        assert "Unknown tool" in result.tool_calls[0].result.error
