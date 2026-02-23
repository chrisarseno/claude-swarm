"""Tests for tool base — ToolDefinition, ToolResult, ToolRegistry."""

import pytest

from swarm.tools.base import ToolDefinition, ToolResult, ToolRegistry


# =============================================================================
# ToolResult
# =============================================================================


class TestToolResult:
    def test_success_message(self):
        r = ToolResult(success=True, output="worked")
        assert r.to_message() == "worked"

    def test_error_message(self):
        r = ToolResult(success=False, error="broken")
        assert r.to_message() == "Error: broken"

    def test_defaults(self):
        r = ToolResult(success=True)
        assert r.output == ""
        assert r.error == ""
        assert r.metadata == {}

    def test_metadata(self):
        r = ToolResult(success=True, metadata={"lines": 10})
        assert r.metadata["lines"] == 10


# =============================================================================
# ToolDefinition
# =============================================================================


class TestToolDefinition:
    def test_json_schema(self, sample_tool):
        schema = sample_tool.to_json_schema()
        assert schema["type"] == "object"
        assert "text" in schema["properties"]
        assert "text" in schema["required"]

    def test_json_schema_empty_params(self, failing_tool):
        schema = failing_tool.to_json_schema()
        assert schema["properties"] == {}
        assert schema["required"] == []


# =============================================================================
# ToolRegistry
# =============================================================================


class TestToolRegistry:
    def test_register_and_get(self, tool_registry, sample_tool):
        tool_registry.register(sample_tool)
        assert tool_registry.get("echo") is sample_tool

    def test_get_unknown(self, tool_registry):
        assert tool_registry.get("nonexistent") is None

    def test_unregister(self, tool_registry, sample_tool):
        tool_registry.register(sample_tool)
        tool_registry.unregister("echo")
        assert tool_registry.get("echo") is None

    def test_unregister_unknown_no_error(self, tool_registry):
        tool_registry.unregister("nonexistent")  # should not raise

    def test_list_tools(self, tool_registry, sample_tool, failing_tool):
        tool_registry.register(sample_tool)
        tool_registry.register(failing_tool)
        tools = tool_registry.list_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"echo", "fail"}

    def test_get_schemas(self, tool_registry, sample_tool):
        tool_registry.register(sample_tool)
        schemas = tool_registry.get_schemas()
        assert len(schemas) == 1
        s = schemas[0]
        assert s["name"] == "echo"
        assert s["description"] == "Echoes text back"
        assert "properties" in s["parameters"]

    @pytest.mark.asyncio
    async def test_execute_success(self, tool_registry, sample_tool):
        tool_registry.register(sample_tool)
        result = await tool_registry.execute("echo", text="world")
        assert result.success is True
        assert result.output == "echo: world"

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self, tool_registry):
        result = await tool_registry.execute("nonexistent")
        assert result.success is False
        assert "Unknown tool" in result.error

    @pytest.mark.asyncio
    async def test_execute_exception_caught(self, tool_registry, failing_tool):
        tool_registry.register(failing_tool)
        result = await tool_registry.execute("fail")
        assert result.success is False
        assert "intentional test failure" in result.error

    def test_register_overwrites(self, tool_registry, sample_tool):
        tool_registry.register(sample_tool)
        new_tool = ToolDefinition(
            name="echo",
            description="New echo",
            parameters={"properties": {}, "required": []},
            execute=sample_tool.execute,
        )
        tool_registry.register(new_tool)
        assert tool_registry.get("echo").description == "New echo"
