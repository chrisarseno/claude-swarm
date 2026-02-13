"""
Model-agnostic ReAct agent loop with tool calling.

Gives ANY LLM the ability to autonomously use tools by running a
think -> act -> observe loop until the model produces a final answer
or hits the iteration limit.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .base import ToolRegistry, ToolResult
from .backends import BaseToolFormatter, ParsedToolCall


@dataclass
class ToolCallEvent:
    """Record of a single tool call during the agent loop."""

    iteration: int
    tool_name: str
    arguments: Dict[str, Any]
    result: ToolResult
    duration_ms: float = 0.0


@dataclass
class AgentLoopResult:
    """Final result of an agent loop run."""

    response: str
    tool_calls: List[ToolCallEvent] = field(default_factory=list)
    iterations: int = 0
    total_duration_ms: float = 0.0
    stopped_reason: str = ""  # "complete", "max_iterations", "error"


class AgentLoop:
    """
    ReAct-style agent loop that works with any LLM backend.

    Flow:
        1. Send user message + tool definitions to LLM
        2. Parse response for tool calls
        3. If tool calls found: execute tools, append results, go to step 1
        4. If no tool calls: return final response

    The `send_fn` callback handles the actual LLM API call, making this
    class backend-agnostic.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        formatter: BaseToolFormatter,
        send_fn: Callable,
        max_iterations: int = 10,
        system_prompt: str = "",
        on_tool_call: Optional[Callable[[ToolCallEvent], Any]] = None,
        on_token: Optional[Callable[[str], Any]] = None,
    ):
        """
        Args:
            tool_registry: Registry of available tools.
            formatter: Backend-specific tool formatter.
            send_fn: Async callable(messages, tools) -> response_dict.
                      Must return a dict with at minimum a 'message' key.
            max_iterations: Maximum tool-call iterations.
            system_prompt: System prompt to prepend.
            on_tool_call: Callback when a tool is called.
            on_token: Callback for streaming tokens.
        """
        self.tool_registry = tool_registry
        self.formatter = formatter
        self.send_fn = send_fn
        self.max_iterations = max_iterations
        self.system_prompt = system_prompt
        self.on_tool_call = on_tool_call
        self.on_token = on_token

    async def run(self, user_message: str) -> AgentLoopResult:
        """Execute the agent loop for a user message."""
        start_time = time.time()
        tool_call_events: List[ToolCallEvent] = []

        # Format tools for the backend
        tools = self.tool_registry.list_tools()
        formatted_tools = self.formatter.format_tools(tools)

        # Build initial messages
        messages: List[Dict[str, Any]] = []
        if self.system_prompt:
            # For GenericToolFormatter, inject tool descriptions into system prompt
            system_content = self.system_prompt
            if isinstance(formatted_tools, str):
                # Generic formatter returns tool docs as a string
                system_content = system_content + "\n\n" + formatted_tools
                formatted_tools = None  # Don't pass tools separately
            messages.append({"role": "system", "content": system_content})

        messages.append({"role": "user", "content": user_message})

        final_response = ""
        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Call the LLM
            response = await self.send_fn(messages, formatted_tools)

            # Extract text content from response
            text_content = self._extract_text(response)

            # Parse for tool calls
            tool_calls = self.formatter.parse_tool_calls(response)

            if not tool_calls:
                # No tool calls — model is done
                final_response = text_content
                break

            # Execute each tool call
            # Append assistant message with tool calls to conversation
            assistant_msg = self._build_assistant_message(response, text_content)
            messages.append(assistant_msg)

            for tc in tool_calls:
                t0 = time.time()
                result = await self.tool_registry.execute(tc.name, **tc.arguments)
                duration = (time.time() - t0) * 1000

                event = ToolCallEvent(
                    iteration=iteration,
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=result,
                    duration_ms=duration,
                )
                tool_call_events.append(event)

                if self.on_tool_call:
                    try:
                        self.on_tool_call(event)
                    except Exception:
                        pass

                # Append tool result to messages
                tool_msg = self.formatter.format_tool_result(
                    tc.name, result.to_message()
                )
                messages.append(tool_msg)

        else:
            # Hit max iterations
            final_response = text_content if text_content else "(Agent reached maximum iterations)"

        total_duration = (time.time() - start_time) * 1000
        stopped_reason = "complete" if iteration < self.max_iterations else "max_iterations"

        return AgentLoopResult(
            response=final_response,
            tool_calls=tool_call_events,
            iterations=iteration,
            total_duration_ms=total_duration,
            stopped_reason=stopped_reason,
        )

    def _extract_text(self, response: Dict[str, Any]) -> str:
        """Extract text content from various response formats."""
        # Ollama /api/chat format
        message = response.get("message", {})
        if isinstance(message, dict):
            content = message.get("content", "")
            if content:
                return content

        # Plain text response (/api/generate)
        if "response" in response:
            return response["response"]

        # OpenAI format
        choices = response.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            return msg.get("content", "")

        # Claude format
        content_blocks = response.get("content", [])
        if isinstance(content_blocks, list):
            texts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
            return "\n".join(texts)

        return ""

    def _build_assistant_message(
        self, response: Dict[str, Any], text_content: str
    ) -> Dict[str, Any]:
        """Build the assistant message to append to conversation history."""
        # For Ollama, pass through the original message
        message = response.get("message", {})
        if isinstance(message, dict) and "tool_calls" in message:
            return {"role": "assistant", **message}

        # For generic (XML-based tool calls), include the raw text
        return {"role": "assistant", "content": text_content}
