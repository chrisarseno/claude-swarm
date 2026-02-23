"""
Backend-specific tool calling formatters.

Each formatter converts ToolDefinitions to/from the format expected by a
specific LLM API, and parses tool calls from model responses.
"""

import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import ToolDefinition, ToolRegistry


@dataclass
class ParsedToolCall:
    """A tool call parsed from a model response."""

    name: str
    arguments: Dict[str, Any]
    raw: Optional[Dict[str, Any]] = None  # original response chunk


class BaseToolFormatter(ABC):
    """Base class for backend-specific formatters."""

    @abstractmethod
    def format_tools(self, tools: List[ToolDefinition]) -> Any:
        """Convert tool definitions to backend-specific format."""

    @abstractmethod
    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ParsedToolCall]:
        """Extract tool calls from a model response."""

    @abstractmethod
    def format_tool_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        """Format a tool execution result for sending back to the model."""


class OllamaToolFormatter(BaseToolFormatter):
    """Formatter for Ollama /api/chat with native tool support."""

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.to_json_schema(),
                },
            })
        return formatted

    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ParsedToolCall]:
        """Parse tool_calls from Ollama /api/chat response."""
        calls = []
        message = response.get("message", {})
        tool_calls = message.get("tool_calls", [])
        for tc in tool_calls:
            func = tc.get("function", {})
            name = func.get("name", "")
            args = func.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            if name:
                calls.append(ParsedToolCall(name=name, arguments=args, raw=tc))
        return calls

    def format_tool_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        return {
            "role": "tool",
            "content": result,
        }


class ClaudeToolFormatter(BaseToolFormatter):
    """Formatter for Anthropic Claude API tool_use format."""

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        formatted = []
        for tool in tools:
            formatted.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.to_json_schema(),
            })
        return formatted

    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ParsedToolCall]:
        calls = []
        content = response.get("content", [])
        for block in content:
            if block.get("type") == "tool_use":
                calls.append(ParsedToolCall(
                    name=block["name"],
                    arguments=block.get("input", {}),
                    raw=block,
                ))
        return calls

    def format_tool_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": "",  # Caller must fill this in
            "content": result,
        }


class OpenAIToolFormatter(BaseToolFormatter):
    """Formatter for OpenAI function_calling format."""

    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        formatted = []
        for tool in tools:
            formatted.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.to_json_schema(),
                },
            })
        return formatted

    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ParsedToolCall]:
        calls = []
        choices = response.get("choices", [])
        for choice in choices:
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "")
                args_str = func.get("arguments", "{}")
                try:
                    args = json.loads(args_str)
                except json.JSONDecodeError:
                    args = {}
                if name:
                    calls.append(ParsedToolCall(name=name, arguments=args, raw=tc))
        return calls

    def format_tool_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": "",  # Caller must fill this in
            "content": result,
        }


class GenericToolFormatter(BaseToolFormatter):
    """
    Fallback formatter for models without native tool support.

    Injects tool descriptions into the system prompt and parses
    <tool_call> XML tags from model output.
    """

    TOOL_CALL_PATTERN = re.compile(
        r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
        re.DOTALL,
    )

    def format_tools(self, tools: List[ToolDefinition]) -> str:
        """Return a system prompt section describing available tools."""
        lines = [
            "You have access to the following tools. To use a tool, output a "
            "<tool_call> block with a JSON object containing 'name' and 'arguments'.",
            "",
            "Available tools:",
        ]
        for tool in tools:
            params = tool.to_json_schema()
            props = params.get("properties", {})
            required = params.get("required", [])
            param_desc = []
            for pname, pschema in props.items():
                req = " (required)" if pname in required else ""
                param_desc.append(f"    - {pname}: {pschema.get('description', '')}{req}")

            lines.append(f"\n  {tool.name}: {tool.description}")
            if param_desc:
                lines.append("  Parameters:")
                lines.extend(param_desc)

        lines.extend([
            "",
            "Example tool call:",
            '<tool_call>{"name": "read_file", "arguments": {"path": "src/main.py"}}</tool_call>',
            "",
            "After receiving tool results, continue your analysis. "
            "You may call multiple tools in sequence.",
        ])
        return "\n".join(lines)

    def parse_tool_calls(self, response: Dict[str, Any]) -> List[ParsedToolCall]:
        """Parse <tool_call> blocks from plain text response."""
        text = ""
        # Handle various response shapes
        message = response.get("message", {})
        if isinstance(message, dict):
            text = message.get("content", "")
        elif isinstance(message, str):
            text = message
        if not text:
            text = response.get("response", "")

        calls = []
        for match in self.TOOL_CALL_PATTERN.finditer(text):
            try:
                data = json.loads(match.group(1))
                name = data.get("name", "")
                args = data.get("arguments", {})
                if name:
                    calls.append(ParsedToolCall(name=name, arguments=args, raw=data))
            except json.JSONDecodeError:
                continue
        return calls

    def format_tool_result(self, tool_name: str, result: str) -> Dict[str, Any]:
        return {
            "role": "user",
            "content": f"<tool_result name=\"{tool_name}\">\n{result}\n</tool_result>",
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_FORMATTERS = {
    "ollama": OllamaToolFormatter,
    "claude": ClaudeToolFormatter,
    "openai": OpenAIToolFormatter,
    "generic": GenericToolFormatter,
}


def get_formatter_for_backend(backend: str) -> BaseToolFormatter:
    """Get the appropriate formatter for a backend name."""
    cls = _FORMATTERS.get(backend.lower(), GenericToolFormatter)
    return cls()
