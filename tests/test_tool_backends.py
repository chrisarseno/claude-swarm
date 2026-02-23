"""Tests for backend-specific tool formatters."""

import pytest

from swarm.tools.base import ToolDefinition, ToolResult
from swarm.tools.backends import (
    ParsedToolCall,
    OllamaToolFormatter,
    ClaudeToolFormatter,
    OpenAIToolFormatter,
    GenericToolFormatter,
    get_formatter_for_backend,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _noop(**kwargs) -> ToolResult:
    return ToolResult(success=True)


SAMPLE_TOOLS = [
    ToolDefinition(
        name="read_file",
        description="Read a file",
        parameters={
            "properties": {"path": {"type": "string", "description": "File path"}},
            "required": ["path"],
        },
        execute=_noop,
    ),
    ToolDefinition(
        name="write_file",
        description="Write a file",
        parameters={
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content"},
            },
            "required": ["path", "content"],
        },
        execute=_noop,
    ),
]


# =============================================================================
# ParsedToolCall
# =============================================================================


class TestParsedToolCall:
    def test_creation(self):
        tc = ParsedToolCall(name="read_file", arguments={"path": "x.py"})
        assert tc.name == "read_file"
        assert tc.arguments == {"path": "x.py"}
        assert tc.raw is None

    def test_with_raw(self):
        raw = {"function": {"name": "read_file"}}
        tc = ParsedToolCall(name="read_file", arguments={}, raw=raw)
        assert tc.raw is raw


# =============================================================================
# Ollama Formatter
# =============================================================================


class TestOllamaFormatter:
    @pytest.fixture
    def fmt(self):
        return OllamaToolFormatter()

    def test_format_tools(self, fmt):
        result = fmt.format_tools(SAMPLE_TOOLS)
        assert len(result) == 2
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "read_file"
        assert "properties" in result[0]["function"]["parameters"]

    def test_parse_tool_calls(self, fmt):
        response = {
            "message": {
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": {"path": "x.py"}}},
                ]
            }
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "x.py"}

    def test_parse_string_arguments(self, fmt):
        response = {
            "message": {
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": '{"path": "x.py"}'}},
                ]
            }
        }
        calls = fmt.parse_tool_calls(response)
        assert calls[0].arguments == {"path": "x.py"}

    def test_parse_invalid_json_arguments(self, fmt):
        response = {
            "message": {
                "tool_calls": [
                    {"function": {"name": "read_file", "arguments": "not json"}},
                ]
            }
        }
        calls = fmt.parse_tool_calls(response)
        assert calls[0].arguments == {}

    def test_parse_empty_response(self, fmt):
        assert fmt.parse_tool_calls({}) == []
        assert fmt.parse_tool_calls({"message": {}}) == []

    def test_parse_skips_empty_name(self, fmt):
        response = {"message": {"tool_calls": [{"function": {"name": "", "arguments": {}}}]}}
        assert fmt.parse_tool_calls(response) == []

    def test_format_tool_result(self, fmt):
        result = fmt.format_tool_result("read_file", "file contents")
        assert result["role"] == "tool"
        assert result["content"] == "file contents"


# =============================================================================
# Claude Formatter
# =============================================================================


class TestClaudeFormatter:
    @pytest.fixture
    def fmt(self):
        return ClaudeToolFormatter()

    def test_format_tools(self, fmt):
        result = fmt.format_tools(SAMPLE_TOOLS)
        assert len(result) == 2
        assert result[0]["name"] == "read_file"
        assert "input_schema" in result[0]

    def test_parse_tool_calls(self, fmt):
        response = {
            "content": [
                {"type": "text", "text": "I'll read the file."},
                {"type": "tool_use", "name": "read_file", "input": {"path": "x.py"}},
            ]
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "x.py"}

    def test_parse_no_tool_use(self, fmt):
        response = {"content": [{"type": "text", "text": "No tools needed."}]}
        assert fmt.parse_tool_calls(response) == []

    def test_parse_empty_content(self, fmt):
        assert fmt.parse_tool_calls({}) == []
        assert fmt.parse_tool_calls({"content": []}) == []

    def test_format_tool_result(self, fmt):
        result = fmt.format_tool_result("read_file", "output")
        assert result["type"] == "tool_result"
        assert result["content"] == "output"
        assert result["tool_use_id"] == ""  # Caller fills in


# =============================================================================
# OpenAI Formatter
# =============================================================================


class TestOpenAIFormatter:
    @pytest.fixture
    def fmt(self):
        return OpenAIToolFormatter()

    def test_format_tools(self, fmt):
        result = fmt.format_tools(SAMPLE_TOOLS)
        assert len(result) == 2
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "read_file"

    def test_parse_tool_calls(self, fmt):
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "read_file",
                                    "arguments": '{"path": "x.py"}',
                                }
                            }
                        ]
                    }
                }
            ]
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "x.py"}

    def test_parse_bad_json_arguments(self, fmt):
        response = {
            "choices": [
                {"message": {"tool_calls": [{"function": {"name": "read_file", "arguments": "bad"}}]}}
            ]
        }
        calls = fmt.parse_tool_calls(response)
        assert calls[0].arguments == {}

    def test_parse_empty(self, fmt):
        assert fmt.parse_tool_calls({}) == []
        assert fmt.parse_tool_calls({"choices": []}) == []

    def test_format_tool_result(self, fmt):
        result = fmt.format_tool_result("read_file", "data")
        assert result["role"] == "tool"
        assert result["content"] == "data"
        assert result["tool_call_id"] == ""


# =============================================================================
# Generic (XML) Formatter
# =============================================================================


class TestGenericFormatter:
    @pytest.fixture
    def fmt(self):
        return GenericToolFormatter()

    def test_format_tools_returns_string(self, fmt):
        result = fmt.format_tools(SAMPLE_TOOLS)
        assert isinstance(result, str)
        assert "read_file" in result
        assert "write_file" in result
        assert "<tool_call>" in result

    def test_format_tools_includes_params(self, fmt):
        result = fmt.format_tools(SAMPLE_TOOLS)
        assert "path" in result
        assert "(required)" in result

    def test_parse_tool_calls(self, fmt):
        response = {
            "message": {
                "content": (
                    'Let me read the file.\n'
                    '<tool_call>{"name": "read_file", "arguments": {"path": "x.py"}}</tool_call>'
                )
            }
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1
        assert calls[0].name == "read_file"
        assert calls[0].arguments == {"path": "x.py"}

    def test_parse_multiple_tool_calls(self, fmt):
        response = {
            "message": {
                "content": (
                    '<tool_call>{"name": "read_file", "arguments": {"path": "a.py"}}</tool_call>\n'
                    '<tool_call>{"name": "write_file", "arguments": {"path": "b.py", "content": "x"}}</tool_call>'
                )
            }
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 2
        assert calls[0].name == "read_file"
        assert calls[1].name == "write_file"

    def test_parse_bad_json_skipped(self, fmt):
        response = {
            "message": {"content": '<tool_call>not valid json</tool_call>'}
        }
        assert fmt.parse_tool_calls(response) == []

    def test_parse_empty_name_skipped(self, fmt):
        response = {
            "message": {"content": '<tool_call>{"name": "", "arguments": {}}</tool_call>'}
        }
        assert fmt.parse_tool_calls(response) == []

    def test_parse_from_response_key(self, fmt):
        response = {
            "response": '<tool_call>{"name": "read_file", "arguments": {"path": "x"}}</tool_call>'
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1

    def test_parse_message_as_string(self, fmt):
        response = {
            "message": '<tool_call>{"name": "read_file", "arguments": {"path": "x"}}</tool_call>'
        }
        calls = fmt.parse_tool_calls(response)
        assert len(calls) == 1

    def test_format_tool_result(self, fmt):
        result = fmt.format_tool_result("read_file", "contents")
        assert result["role"] == "user"
        assert '<tool_result name="read_file">' in result["content"]
        assert "contents" in result["content"]


# =============================================================================
# Factory
# =============================================================================


class TestFormatterFactory:
    def test_ollama(self):
        assert isinstance(get_formatter_for_backend("ollama"), OllamaToolFormatter)

    def test_claude(self):
        assert isinstance(get_formatter_for_backend("claude"), ClaudeToolFormatter)

    def test_openai(self):
        assert isinstance(get_formatter_for_backend("openai"), OpenAIToolFormatter)

    def test_generic(self):
        assert isinstance(get_formatter_for_backend("generic"), GenericToolFormatter)

    def test_unknown_falls_back_to_generic(self):
        assert isinstance(get_formatter_for_backend("unknown_backend"), GenericToolFormatter)

    def test_case_insensitive(self):
        assert isinstance(get_formatter_for_backend("OLLAMA"), OllamaToolFormatter)
        assert isinstance(get_formatter_for_backend("Claude"), ClaudeToolFormatter)
