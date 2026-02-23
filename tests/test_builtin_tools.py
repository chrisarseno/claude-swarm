"""Tests for built-in filesystem and shell tools."""

import pytest
from pathlib import Path

from swarm.tools.builtin import (
    _read_file,
    _list_directory,
    _search_files,
    _write_file,
    _run_command,
    _get_file_info,
    _human_size,
    BUILTIN_TOOLS,
    register_builtin_tools,
)
from swarm.tools.base import ToolRegistry


# =============================================================================
# _human_size helper
# =============================================================================


class TestHumanSize:
    def test_bytes(self):
        assert _human_size(500) == "500.0 B"

    def test_kilobytes(self):
        assert _human_size(2048) == "2.0 KB"

    def test_megabytes(self):
        assert _human_size(5 * 1024 * 1024) == "5.0 MB"

    def test_gigabytes(self):
        assert _human_size(3 * 1024 ** 3) == "3.0 GB"

    def test_zero(self):
        assert _human_size(0) == "0.0 B"


# =============================================================================
# register_builtin_tools
# =============================================================================


class TestRegistration:
    def test_registers_all_6_tools(self):
        registry = register_builtin_tools()
        tools = registry.list_tools()
        assert len(tools) == 6
        names = {t.name for t in tools}
        assert names == {"read_file", "list_directory", "search_files", "write_file", "run_command", "get_file_info"}

    def test_uses_existing_registry(self):
        registry = ToolRegistry()
        returned = register_builtin_tools(registry)
        assert returned is registry
        assert len(registry.list_tools()) == 6

    def test_builtin_tools_list(self):
        assert len(BUILTIN_TOOLS) == 6


# =============================================================================
# _read_file
# =============================================================================


class TestReadFile:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, tmp_workspace):
        result = await _read_file(str(tmp_workspace / "hello.py"))
        assert result.success is True
        assert "print('hello')" in result.output
        assert result.metadata["lines"] == 1

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tmp_workspace):
        result = await _read_file(str(tmp_workspace / "nope.txt"))
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_directory_fails(self, tmp_workspace):
        result = await _read_file(str(tmp_workspace / "sub"))
        assert result.success is False
        assert "not a file" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_with_line_numbers(self, tmp_workspace):
        result = await _read_file(str(tmp_workspace / "data.txt"))
        assert result.success is True
        assert "1 |" in result.output
        assert "line1" in result.output

    @pytest.mark.asyncio
    async def test_truncation(self, tmp_workspace):
        big = tmp_workspace / "big.txt"
        big.write_text("\n".join(f"line {i}" for i in range(1000)), encoding="utf-8")
        result = await _read_file(str(big), max_lines=10)
        assert result.success is True
        assert result.metadata["truncated"] is True
        assert "truncated" in result.output


# =============================================================================
# _list_directory
# =============================================================================


class TestListDirectory:
    @pytest.mark.asyncio
    async def test_list_default(self, tmp_workspace):
        result = await _list_directory(str(tmp_workspace))
        assert result.success is True
        assert "hello.py" in result.output
        assert "data.txt" in result.output
        assert "sub" in result.output

    @pytest.mark.asyncio
    async def test_list_with_pattern(self, tmp_workspace):
        result = await _list_directory(str(tmp_workspace), pattern="*.py")
        assert result.success is True
        assert "hello.py" in result.output
        assert "data.txt" not in result.output

    @pytest.mark.asyncio
    async def test_list_nonexistent(self, tmp_workspace):
        result = await _list_directory(str(tmp_workspace / "nope"))
        assert result.success is False

    @pytest.mark.asyncio
    async def test_list_file_not_dir(self, tmp_workspace):
        result = await _list_directory(str(tmp_workspace / "hello.py"))
        assert result.success is False
        assert "not a directory" in result.error.lower()

    @pytest.mark.asyncio
    async def test_shows_file_sizes(self, tmp_workspace):
        result = await _list_directory(str(tmp_workspace))
        assert "bytes" in result.output


# =============================================================================
# _search_files
# =============================================================================


class TestSearchFiles:
    @pytest.mark.asyncio
    async def test_search_finds_match(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace), pattern="print")
        assert result.success is True
        assert "hello.py" in result.output
        assert result.metadata["matches"] >= 1

    @pytest.mark.asyncio
    async def test_search_no_matches(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace), pattern="ZZZZNOTFOUND")
        assert result.success is True
        assert "No matches found" in result.output

    @pytest.mark.asyncio
    async def test_search_with_file_glob(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace), pattern="42", file_glob="*.py")
        assert result.success is True
        assert "nested.py" in result.output

    @pytest.mark.asyncio
    async def test_search_invalid_regex(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace), pattern="[invalid")
        assert result.success is False
        assert "regex" in result.error.lower()

    @pytest.mark.asyncio
    async def test_search_nonexistent_path(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace / "nope"), pattern="x")
        assert result.success is False

    @pytest.mark.asyncio
    async def test_search_single_file(self, tmp_workspace):
        result = await _search_files(str(tmp_workspace / "hello.py"), pattern="print")
        assert result.success is True
        assert result.metadata["matches"] >= 1


# =============================================================================
# _write_file
# =============================================================================


class TestWriteFile:
    @pytest.mark.asyncio
    async def test_write_new_file(self, tmp_workspace):
        target = tmp_workspace / "new.txt"
        result = await _write_file(str(target), "hello world")
        assert result.success is True
        assert target.read_text() == "hello world"

    @pytest.mark.asyncio
    async def test_write_creates_parents(self, tmp_workspace):
        target = tmp_workspace / "deep" / "nested" / "file.txt"
        result = await _write_file(str(target), "content")
        assert result.success is True
        assert target.exists()
        assert target.read_text() == "content"

    @pytest.mark.asyncio
    async def test_write_overwrites(self, tmp_workspace):
        target = tmp_workspace / "hello.py"
        result = await _write_file(str(target), "new content")
        assert result.success is True
        assert target.read_text() == "new content"

    @pytest.mark.asyncio
    async def test_write_metadata(self, tmp_workspace):
        target = tmp_workspace / "meta.txt"
        result = await _write_file(str(target), "abc")
        assert result.metadata["bytes"] == 3


# =============================================================================
# _run_command
# =============================================================================


class TestRunCommand:
    @pytest.mark.asyncio
    async def test_echo(self, tmp_workspace):
        result = await _run_command("echo hello", cwd=str(tmp_workspace))
        assert result.success is True
        assert "hello" in result.output

    @pytest.mark.asyncio
    async def test_return_code(self, tmp_workspace):
        result = await _run_command("python -c \"import sys; sys.exit(1)\"", cwd=str(tmp_workspace))
        assert result.success is False
        assert result.metadata["return_code"] == 1

    @pytest.mark.asyncio
    async def test_blocked_command(self, tmp_workspace):
        result = await _run_command("rm -rf /", cwd=str(tmp_workspace))
        assert result.success is False
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_blocked_mkfs(self, tmp_workspace):
        result = await _run_command("mkfs.ext4 /dev/sda1", cwd=str(tmp_workspace))
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_cwd(self, tmp_workspace):
        result = await _run_command("echo hi", cwd=str(tmp_workspace / "nope"))
        assert result.success is False

    @pytest.mark.asyncio
    async def test_timeout(self, tmp_workspace):
        result = await _run_command("python -c \"import time; time.sleep(10)\"", cwd=str(tmp_workspace), timeout=1)
        assert result.success is False
        assert "timed out" in result.error.lower()


# =============================================================================
# _get_file_info
# =============================================================================


class TestGetFileInfo:
    @pytest.mark.asyncio
    async def test_file_info(self, tmp_workspace):
        result = await _get_file_info(str(tmp_workspace / "hello.py"))
        assert result.success is True
        assert result.metadata["type"] == "file"
        assert result.metadata["extension"] == ".py"
        assert "size_human" in result.metadata

    @pytest.mark.asyncio
    async def test_directory_info(self, tmp_workspace):
        result = await _get_file_info(str(tmp_workspace / "sub"))
        assert result.success is True
        assert result.metadata["type"] == "directory"

    @pytest.mark.asyncio
    async def test_nonexistent(self, tmp_workspace):
        result = await _get_file_info(str(tmp_workspace / "nope"))
        assert result.success is False
        assert "not found" in result.error.lower()
