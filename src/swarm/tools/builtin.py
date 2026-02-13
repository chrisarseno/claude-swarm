"""
Built-in tools that give LLMs the ability to interact with the filesystem and shell.
"""

import asyncio
import glob as glob_mod
import os
import re
import stat
from pathlib import Path
from typing import Optional

from .base import ToolDefinition, ToolResult, ToolRegistry


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

async def _read_file(path: str, max_lines: int = 500) -> ToolResult:
    """Read file contents."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, error=f"File not found: {path}")
        if not p.is_file():
            return ToolResult(success=False, error=f"Not a file: {path}")

        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        truncated = len(lines) > max_lines
        if truncated:
            lines = lines[:max_lines]
        numbered = [f"{i + 1:>5} | {line}" for i, line in enumerate(lines)]
        output = "\n".join(numbered)
        if truncated:
            output += f"\n\n... (truncated at {max_lines} lines, {len(lines)} total)"
        return ToolResult(
            success=True,
            output=output,
            metadata={"path": str(p), "lines": len(lines), "truncated": truncated},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _list_directory(path: str = ".", pattern: str = "*") -> ToolResult:
    """List directory contents with optional glob pattern."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, error=f"Directory not found: {path}")
        if not p.is_dir():
            return ToolResult(success=False, error=f"Not a directory: {path}")

        entries = sorted(p.glob(pattern))
        lines = []
        for entry in entries[:200]:
            kind = "DIR " if entry.is_dir() else "FILE"
            size = ""
            if entry.is_file():
                try:
                    size = f" ({entry.stat().st_size:,} bytes)"
                except OSError:
                    pass
            lines.append(f"  {kind}  {entry.name}{size}")

        total = len(entries)
        header = f"Directory: {p}\n{total} entries"
        if total > 200:
            header += " (showing first 200)"
        output = header + "\n" + "\n".join(lines)
        return ToolResult(success=True, output=output, metadata={"path": str(p), "count": total})
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _search_files(path: str = ".", pattern: str = "", file_glob: str = "*") -> ToolResult:
    """Search file contents for a regex pattern."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        regex = re.compile(pattern, re.IGNORECASE)
        matches = []
        files_searched = 0

        target_files = []
        if p.is_file():
            target_files = [p]
        else:
            target_files = list(p.rglob(file_glob))

        for fp in target_files[:500]:
            if not fp.is_file():
                continue
            # Skip binary / large files
            try:
                size = fp.stat().st_size
            except OSError:
                continue
            if size > 1_000_000:
                continue
            files_searched += 1
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if regex.search(line):
                    rel = fp.relative_to(p) if fp != p else fp.name
                    matches.append(f"  {rel}:{i}  {line.strip()}")
                    if len(matches) >= 100:
                        break
            if len(matches) >= 100:
                break

        header = f"Searched {files_searched} files for /{pattern}/"
        if not matches:
            return ToolResult(success=True, output=header + "\nNo matches found.")
        output = header + f"\n{len(matches)} matches:\n" + "\n".join(matches)
        return ToolResult(success=True, output=output, metadata={"matches": len(matches)})
    except re.error as e:
        return ToolResult(success=False, error=f"Invalid regex: {e}")
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _write_file(path: str, content: str) -> ToolResult:
    """Write or create a file."""
    try:
        p = Path(path).resolve()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return ToolResult(
            success=True,
            output=f"Wrote {len(content)} bytes to {p}",
            metadata={"path": str(p), "bytes": len(content)},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _run_command(command: str, cwd: str = ".", timeout: int = 30) -> ToolResult:
    """Execute a shell command with timeout."""
    try:
        cwd_path = Path(cwd).resolve()
        if not cwd_path.is_dir():
            return ToolResult(success=False, error=f"Working directory not found: {cwd}")

        # Basic safety: block destructive patterns
        blocked = ["rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb"]
        cmd_lower = command.lower()
        for pattern in blocked:
            if pattern in cmd_lower:
                return ToolResult(success=False, error=f"Blocked dangerous command pattern: {pattern}")

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd_path,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return ToolResult(success=False, error=f"Command timed out after {timeout}s")

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        # Truncate massive output
        if len(stdout_text) > 20_000:
            stdout_text = stdout_text[:20_000] + "\n... (truncated)"

        output = stdout_text
        if stderr_text:
            output += f"\n\nSTDERR:\n{stderr_text}" if output else f"STDERR:\n{stderr_text}"

        return ToolResult(
            success=proc.returncode == 0,
            output=output or "(no output)",
            error=stderr_text if proc.returncode != 0 else "",
            metadata={"return_code": proc.returncode},
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


async def _get_file_info(path: str) -> ToolResult:
    """Get file/directory metadata."""
    try:
        p = Path(path).resolve()
        if not p.exists():
            return ToolResult(success=False, error=f"Path not found: {path}")

        st = p.stat()
        from datetime import datetime

        info = {
            "path": str(p),
            "name": p.name,
            "type": "directory" if p.is_dir() else "file",
            "size_bytes": st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(st.st_ctime).isoformat(),
        }
        if p.is_file():
            info["extension"] = p.suffix
            info["size_human"] = _human_size(st.st_size)

        lines = [f"  {k}: {v}" for k, v in info.items()]
        return ToolResult(success=True, output="\n".join(lines), metadata=info)
    except Exception as e:
        return ToolResult(success=False, error=str(e))


def _human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

READ_FILE = ToolDefinition(
    name="read_file",
    description="Read the contents of a file. Returns numbered lines.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to the file to read"},
            "max_lines": {"type": "integer", "description": "Maximum lines to read (default 500)", "default": 500},
        },
        "required": ["path"],
    },
    execute=_read_file,
)

LIST_DIRECTORY = ToolDefinition(
    name="list_directory",
    description="List files and directories. Supports glob patterns.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Directory path (default '.')", "default": "."},
            "pattern": {"type": "string", "description": "Glob pattern filter (default '*')", "default": "*"},
        },
        "required": [],
    },
    execute=_list_directory,
)

SEARCH_FILES = ToolDefinition(
    name="search_files",
    description="Search file contents using a regex pattern. Like grep -rn.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Root directory to search (default '.')", "default": "."},
            "pattern": {"type": "string", "description": "Regex pattern to search for"},
            "file_glob": {"type": "string", "description": "Glob to filter files (e.g. '*.py')", "default": "*"},
        },
        "required": ["pattern"],
    },
    execute=_search_files,
)

WRITE_FILE = ToolDefinition(
    name="write_file",
    description="Write content to a file. Creates parent directories if needed.",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to write to"},
            "content": {"type": "string", "description": "Content to write"},
        },
        "required": ["path", "content"],
    },
    execute=_write_file,
)

RUN_COMMAND = ToolDefinition(
    name="run_command",
    description="Execute a shell command and return its output.",
    parameters={
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "cwd": {"type": "string", "description": "Working directory (default '.')", "default": "."},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)", "default": 30},
        },
        "required": ["command"],
    },
    execute=_run_command,
)

GET_FILE_INFO = ToolDefinition(
    name="get_file_info",
    description="Get metadata about a file or directory (size, dates, type).",
    parameters={
        "properties": {
            "path": {"type": "string", "description": "Path to inspect"},
        },
        "required": ["path"],
    },
    execute=_get_file_info,
)

# All built-in tools
BUILTIN_TOOLS = [READ_FILE, LIST_DIRECTORY, SEARCH_FILES, WRITE_FILE, RUN_COMMAND, GET_FILE_INFO]


def register_builtin_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """Register all built-in tools into a registry."""
    if registry is None:
        registry = ToolRegistry()
    for tool in BUILTIN_TOOLS:
        registry.register(tool)
    return registry
