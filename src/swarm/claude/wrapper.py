"""Wrapper for Claude Code CLI and Ollama instances."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Any
import psutil

from ..utils.logger import get_logger

logger = get_logger(__name__)


class InstanceStatus(Enum):
    """Status of an instance."""
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPED = "stopped"
    ERROR = "error"


def _prune_context(
    messages: list[dict],
    keep_recent: int = 6,
    max_result_chars: int = 800,
) -> list[dict]:
    """Truncate old tool-result messages to keep context size manageable.

    Preserves the system message, the first user message, and the last
    ``keep_recent`` messages verbatim.  Everything in between has its
    ``content`` field trimmed to ``max_result_chars``.
    """
    if len(messages) <= keep_recent + 2:
        return messages  # nothing to prune

    protected_tail = len(messages) - keep_recent
    pruned = []
    for i, msg in enumerate(messages):
        if i == 0 or i >= protected_tail:
            pruned.append(msg)
            continue
        # For tool-result / assistant messages in the middle: truncate
        content = msg.get("content", "")
        if isinstance(content, str) and len(content) > max_result_chars:
            trimmed = content[:max_result_chars] + "\n... [truncated]"
            pruned.append({**msg, "content": trimmed})
        else:
            pruned.append(msg)
    return pruned


@dataclass
class ClaudeCommand:
    """Represents a command to send to an instance."""
    prompt: str
    working_directory: Optional[Path] = None
    timeout: int = 300
    callback: Optional[Callable[[str], None]] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaudeInstance:
    """Manages a single worker instance.

    Supports two backends:
    - "claude": Spawns `claude -p` subprocesses per task
    - "ollama": Calls Ollama HTTP API with a local model
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: InstanceStatus = InstanceStatus.IDLE
    working_directory: Path = field(default_factory=lambda: Path.cwd())
    backend: str = "claude"
    claude_command: str = "claude"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "devstral:24b"
    backend_name: str = "local"
    _process: Optional[asyncio.subprocess.Process] = field(default=None, repr=False)
    _http_session: Any = field(default=None, repr=False)
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    current_task: Optional[str] = None
    output_buffer: list[str] = field(default_factory=list)
    error_count: int = 0
    completed_tasks: int = 0

    async def start(self, claude_command: str = "claude") -> bool:
        """Validate that the configured backend is accessible."""
        try:
            self.status = InstanceStatus.STARTING
            self.claude_command = claude_command
            logger.info("starting_instance", instance_id=self.id,
                        backend=self.backend, cwd=str(self.working_directory))

            if self.backend == "ollama":
                return await self._start_ollama()
            else:
                return await self._start_claude()

        except Exception as e:
            self.status = InstanceStatus.ERROR
            logger.error("failed_to_start_instance", instance_id=self.id, error=str(e))
            return False

    async def _start_claude(self) -> bool:
        """Verify claude CLI is accessible."""
        proc = await asyncio.create_subprocess_exec(
            self.claude_command, "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.working_directory
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode != 0:
            err_msg = stderr.decode('utf-8', errors='ignore').strip()
            logger.error("claude_version_check_failed", instance_id=self.id, error=err_msg)
            self.status = InstanceStatus.ERROR
            return False

        version = stdout.decode('utf-8', errors='ignore').strip()
        logger.info("instance_started", instance_id=self.id,
                     backend="claude", version=version)
        self.status = InstanceStatus.IDLE
        return True

    async def _start_ollama(self) -> bool:
        """Verify Ollama is running and model is available."""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error("ollama_not_accessible", instance_id=self.id)
                        self.status = InstanceStatus.ERROR
                        return False
                    data = await resp.json()
                    model_names = [m["name"] for m in data.get("models", [])]
                    if self.ollama_model not in model_names and f"{self.ollama_model}:latest" not in model_names:
                        # Check partial match
                        found = any(m.startswith(self.ollama_model.split(":")[0]) for m in model_names)
                        if not found:
                            logger.error("ollama_model_not_found", instance_id=self.id,
                                         model=self.ollama_model, available=model_names)
                            self.status = InstanceStatus.ERROR
                            return False

            logger.info("instance_started", instance_id=self.id,
                         backend="ollama", model=self.ollama_model)
            self.status = InstanceStatus.IDLE
            return True
        except Exception as e:
            logger.error("ollama_connection_failed", instance_id=self.id, error=str(e))
            self.status = InstanceStatus.ERROR
            return False

    async def execute(self, command: ClaudeCommand) -> dict[str, Any]:
        """Execute a command using the configured backend."""
        if self.status not in (InstanceStatus.IDLE, InstanceStatus.BUSY):
            raise RuntimeError(f"Instance {self.id} is not available (status: {self.status})")

        if self.backend == "ollama":
            return await self._execute_ollama(command)
        else:
            return await self._execute_claude(command)

    async def _get_http_session(self):
        """Get or create a reusable aiohttp session for this instance."""
        import aiohttp
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def _execute_ollama(self, command: ClaudeCommand) -> dict[str, Any]:
        """Execute a command via Ollama /api/chat with agent loop + tool calling."""
        import aiohttp

        try:
            self.status = InstanceStatus.BUSY
            self.current_task = command.prompt[:100]
            self.last_activity = datetime.now()
            self.stream_buffer = ""
            self.tool_calls_log: list[dict[str, Any]] = []

            cwd = command.working_directory or self.working_directory
            logger.info("executing_ollama", instance_id=self.id,
                         model=self.ollama_model, prompt=command.prompt[:100],
                         backend=self.backend_name)

            task_id = command.metadata.get("task_id", "")

            # Get stream bus for broadcasting
            stream_bus = None
            try:
                from ..api.server import stream_bus as _bus
                stream_bus = _bus
            except ImportError:
                pass

            # --- Build tool registry & agent loop ---
            from ..tools.base import ToolRegistry
            from ..tools.builtin import register_builtin_tools
            from ..tools.backends import OllamaToolFormatter, GenericToolFormatter
            from ..tools.agent_loop import AgentLoop

            registry = register_builtin_tools()

            # Detect if this model supports native tool calling
            supports_native = self._model_supports_tools()
            formatter = OllamaToolFormatter() if supports_native else GenericToolFormatter()

            system_prompt = (
                "You are an expert software engineer with access to tools for reading files, "
                "searching code, listing directories, and running commands.\n\n"
                "IMPORTANT RULES:\n"
                "1. ALWAYS use your tools to investigate before answering. Never guess at file "
                "contents or code structure — use read_file, list_directory, and search_files.\n"
                "2. Start by using list_directory to understand the project structure.\n"
                "3. Use read_file to examine specific files. Use search_files to find patterns.\n"
                "4. Be specific: cite file paths, line numbers, and quote code directly.\n"
                "5. Be thorough but concise in your final answer.\n\n"
                f"Working directory: {cwd}\n"
                "You MUST use tools to explore the codebase. Do NOT ask the user to provide "
                "code — read it yourself with the tools available to you."
            )

            # Enrich prompt with file contents for context
            full_prompt = command.prompt
            full_prompt = await self._enrich_prompt_with_files(full_prompt, cwd)

            # Tool call callback for streaming
            def on_tool_call(event):
                entry = {
                    "tool": event.tool_name,
                    "args": event.arguments,
                    "success": event.result.success,
                    "duration_ms": round(event.duration_ms, 1),
                }
                self.tool_calls_log.append(entry)
                if stream_bus:
                    asyncio.ensure_future(stream_bus.publish({
                        "type": "tool_call",
                        "instance_id": self.id,
                        "task_id": task_id,
                        **entry,
                    }))

            # Reuse HTTP session for all iterations (big perf win)
            session = await self._get_http_session()
            usage = {}

            async def send_fn(messages, tools):
                nonlocal usage

                # ── Context pruning ──
                # Truncate old tool results to keep context manageable.
                # Keep the system + first user message + last 6 messages intact;
                # for everything in between, cap tool result content.
                pruned = _prune_context(messages, keep_recent=6, max_result_chars=800)

                payload = {
                    "model": self.ollama_model,
                    "messages": pruned,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 4096,
                        "num_ctx": 16384,
                    },
                }
                if tools and supports_native:
                    payload["tools"] = tools

                timeout = aiohttp.ClientTimeout(total=command.timeout)
                async with session.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload,
                    timeout=timeout,
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"Ollama API error {resp.status}: {error_text[:200]}")

                    data = await resp.json()

                    # Extract usage stats
                    usage = {
                        "input_tokens": data.get("prompt_eval_count", 0),
                        "output_tokens": data.get("eval_count", 0),
                        "total_duration_ms": data.get("total_duration", 0) / 1_000_000,
                    }

                    # Stream partial output to UI
                    content = data.get("message", {}).get("content", "")
                    if content:
                        self.stream_buffer = content
                        if stream_bus:
                            await stream_bus.publish({
                                "type": "token",
                                "instance_id": self.id,
                                "task_id": task_id,
                                "token": content,
                                "partial": content,
                            })

                    return data

            agent = AgentLoop(
                tool_registry=registry,
                formatter=formatter,
                send_fn=send_fn,
                max_iterations=10,
                system_prompt=system_prompt,
                on_tool_call=on_tool_call,
            )

            result = await agent.run(full_prompt)
            output = result.response

            # Store in output buffer
            if output:
                for line in output.splitlines():
                    self.output_buffer.append(line)
                if len(self.output_buffer) > 5000:
                    self.output_buffer = self.output_buffer[-2000:]

            self.status = InstanceStatus.IDLE
            self.current_task = None
            self.stream_buffer = ""
            self.completed_tasks += 1
            self.last_activity = datetime.now()

            logger.info("ollama_completed", instance_id=self.id,
                         output_len=len(output), usage=usage,
                         tool_calls=len(result.tool_calls),
                         iterations=result.iterations,
                         backend=self.backend_name)

            # Broadcast completion event
            if stream_bus:
                await stream_bus.publish({
                    "type": "task_done",
                    "task_id": task_id,
                    "instance_id": self.id,
                    "status": "completed",
                })

            return {
                "instance_id": self.id,
                "prompt": command.prompt,
                "output": output,
                "status": "completed",
                "backend": "ollama",
                "backend_name": self.backend_name,
                "model": self.ollama_model,
                "usage": usage,
                "tool_calls": self.tool_calls_log,
                "iterations": result.iterations,
                "metadata": command.metadata,
            }

        except asyncio.TimeoutError:
            logger.warning("ollama_timeout", instance_id=self.id, timeout=command.timeout)
            self.status = InstanceStatus.IDLE
            self.current_task = None
            self.stream_buffer = ""
            self.error_count += 1
            return {
                "instance_id": self.id,
                "prompt": command.prompt,
                "output": "",
                "status": "error",
                "error": f"Timed out after {command.timeout}s",
                "metadata": command.metadata,
            }
        except Exception as e:
            self.status = InstanceStatus.IDLE
            self.current_task = None
            self.stream_buffer = ""
            self.error_count += 1
            logger.error("ollama_failed", instance_id=self.id, error=str(e))
            return {
                "instance_id": self.id,
                "prompt": command.prompt,
                "output": "",
                "status": "error",
                "error": str(e),
                "metadata": command.metadata,
            }

    def _model_supports_tools(self) -> bool:
        """Check if the configured Ollama model supports native tool calling."""
        model_lower = self.ollama_model.lower()
        # Models known to support Ollama's native tool calling
        tool_capable = [
            "qwen2.5", "qwen2:", "devstral", "mistral-nemo",
            "llama3.1", "llama3.2", "llama3.3",
            "command-r", "firefunction", "hermes",
        ]
        return any(name in model_lower for name in tool_capable)

    async def _execute_claude(self, command: ClaudeCommand) -> dict[str, Any]:
        """Execute a command by spawning `claude -p` subprocess."""
        try:
            self.status = InstanceStatus.BUSY
            self.current_task = command.prompt[:100]
            self.last_activity = datetime.now()

            cwd = command.working_directory or self.working_directory
            logger.info("executing_claude", instance_id=self.id,
                         prompt=command.prompt[:100], cwd=str(cwd))

            args = [self.claude_command, "-p", command.prompt, "--output-format", "json"]

            self._process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    self._process.communicate(),
                    timeout=command.timeout
                )
            except asyncio.TimeoutError:
                logger.warning("command_timeout", instance_id=self.id, timeout=command.timeout)
                self._process.kill()
                await self._process.wait()
                self.status = InstanceStatus.IDLE
                self.current_task = None
                self.error_count += 1
                return {
                    "instance_id": self.id,
                    "prompt": command.prompt,
                    "output": "",
                    "status": "error",
                    "error": f"Timed out after {command.timeout}s",
                    "metadata": command.metadata
                }

            stdout_text = stdout_bytes.decode('utf-8', errors='ignore').strip()
            stderr_text = stderr_bytes.decode('utf-8', errors='ignore').strip()

            if stdout_text:
                for line in stdout_text.splitlines():
                    self.output_buffer.append(line)
                    if command.callback:
                        command.callback(line)
                if len(self.output_buffer) > 5000:
                    self.output_buffer = self.output_buffer[-2000:]

            success = self._process.returncode == 0

            self.status = InstanceStatus.IDLE
            self.current_task = None
            self._process = None
            self.last_activity = datetime.now()

            if success:
                self.completed_tasks += 1
                output = stdout_text
                try:
                    parsed = json.loads(stdout_text)
                    if isinstance(parsed, dict) and "result" in parsed:
                        output = parsed["result"]
                    elif isinstance(parsed, dict) and "response" in parsed:
                        output = parsed["response"]
                except (json.JSONDecodeError, TypeError):
                    pass

                return {
                    "instance_id": self.id,
                    "prompt": command.prompt,
                    "output": output,
                    "status": "completed",
                    "backend": "claude",
                    "metadata": command.metadata
                }
            else:
                self.error_count += 1
                error_msg = stderr_text or "Process failed"
                logger.error("command_failed", instance_id=self.id, error=error_msg[:200])
                return {
                    "instance_id": self.id,
                    "prompt": command.prompt,
                    "output": stdout_text,
                    "status": "error",
                    "error": error_msg,
                    "metadata": command.metadata
                }

        except Exception as e:
            self.status = InstanceStatus.ERROR
            self.error_count += 1
            self._process = None
            logger.error("command_failed", instance_id=self.id, error=str(e))
            return {
                "instance_id": self.id,
                "prompt": command.prompt,
                "output": "",
                "status": "error",
                "error": str(e),
                "metadata": command.metadata
            }

    async def _enrich_prompt_with_files(self, prompt: str, cwd: Path) -> str:
        """Detect file paths in the prompt and append their contents.

        Scans for patterns like src/foo/bar.py or paths ending in common
        extensions.  Reads up to 3 files, max 500 lines each, to keep
        the context within Ollama's window.
        """
        import re
        import os

        # Match things that look like file paths (with / or \ separators)
        path_pattern = re.compile(
            r'(?:^|\s)((?:[\w./\\-]+/)?[\w.-]+\.(?:py|js|ts|yaml|yml|json|toml|cfg|md|txt|html|css|sql|sh|bat))\b',
            re.IGNORECASE,
        )

        matches = path_pattern.findall(prompt)
        if not matches:
            return prompt

        files_added = 0
        extra = []
        seen = set()

        for rel_path in matches:
            if files_added >= 3:
                break
            rel_path = rel_path.strip()
            if rel_path in seen:
                continue
            seen.add(rel_path)

            # Try resolving relative to workspace
            full_path = cwd / rel_path
            if not full_path.exists():
                # Also try from project root variations
                for prefix in [cwd / "src", cwd]:
                    candidate = prefix / rel_path
                    if candidate.exists():
                        full_path = candidate
                        break

            if full_path.exists() and full_path.is_file():
                try:
                    text = full_path.read_text(encoding="utf-8", errors="replace")
                    lines = text.splitlines()
                    if len(lines) > 500:
                        lines = lines[:500]
                        text = "\n".join(lines) + "\n\n... (truncated at 500 lines)"
                    else:
                        text = "\n".join(lines)

                    extra.append(
                        f"\n\n--- FILE: {rel_path} ({len(lines)} lines) ---\n"
                        f"```\n{text}\n```"
                    )
                    files_added += 1
                    logger.info("enriched_prompt_with_file", file=rel_path, lines=len(lines))
                except Exception as e:
                    logger.warning("failed_to_read_file", file=rel_path, error=str(e))

        if extra:
            return prompt + "\n\nHere are the file contents for your review:" + "".join(extra)
        return prompt

    async def stop(self) -> None:
        """Stop the instance and kill any running subprocess."""
        try:
            logger.info("stopping_instance", instance_id=self.id)
            if self._process and self._process.returncode is None:
                self._process.kill()
                await self._process.wait()
            self._process = None
            # Close reusable HTTP session
            if self._http_session and not self._http_session.closed:
                await self._http_session.close()
                self._http_session = None
            self.status = InstanceStatus.STOPPED
            logger.info("instance_stopped", instance_id=self.id)
        except Exception as e:
            logger.error("failed_to_stop_instance", instance_id=self.id, error=str(e))

    def get_info(self) -> dict[str, Any]:
        """Get instance information."""
        info = {
            "id": self.id,
            "status": self.status.value,
            "backend": self.backend,
            "backend_name": self.backend_name,
            "model": self.ollama_model if self.backend == "ollama" else "claude",
            "working_directory": str(self.working_directory),
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "current_task": self.current_task,
            "completed_tasks": self.completed_tasks,
            "error_count": self.error_count,
        }

        if self._process and self._process.pid:
            try:
                proc = psutil.Process(self._process.pid)
                info["pid"] = self._process.pid
                info["memory_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
                info["cpu_percent"] = proc.cpu_percent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return info

    def get_recent_output(self, lines: int = 50) -> list[str]:
        """Get recent output from this instance."""
        return self.output_buffer[-lines:] if self.output_buffer else []
