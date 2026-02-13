#!/usr/bin/env python3
"""Test script for the Claude Swarm MCP server."""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


async def test_mcp_server():
    """Test the MCP server by sending messages."""
    print("Testing Claude Swarm MCP Server...\n")

    # Start the MCP server
    server_path = Path(__file__).parent / "mcp_server.py"
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(server_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def send_message(message: dict) -> dict:
        """Send a message to the server and get response."""
        process.stdin.write((json.dumps(message) + "\n").encode())
        await process.stdin.drain()

        response_line = await process.stdout.readline()
        return json.loads(response_line.decode())

    try:
        # Test 1: Initialize
        print("1. Testing initialize...")
        response = await send_message({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        print(f"   ✓ Server initialized: {response['serverInfo']['name']}")
        print(f"   Protocol version: {response['protocolVersion']}")

        # Test 2: List tools
        print("\n2. Testing tools/list...")
        response = await send_message({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        })
        tools = response["tools"]
        print(f"   ✓ Found {len(tools)} tools:")
        for tool in tools:
            print(f"     - {tool['name']}: {tool['description'][:60]}...")

        # Test 3: Get status
        print("\n3. Testing swarm_get_status...")
        response = await send_message({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "swarm_get_status",
                "arguments": {}
            }
        })

        if response.get("content"):
            result = json.loads(response["content"][0]["text"])
            print(f"   ✓ Swarm status retrieved:")
            print(f"     Running: {result.get('running', False)}")
            print(f"     Workers: {result.get('workers', 0)}")
            print(f"     Instances: {result.get('instances', {}).get('total_instances', 0)}")

        # Test 4: List instances
        print("\n4. Testing swarm_list_instances...")
        response = await send_message({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "swarm_list_instances",
                "arguments": {}
            }
        })

        if response.get("content"):
            result = json.loads(response["content"][0]["text"])
            print(f"   ✓ Instances: {result.get('count', 0)}")

        print("\n✅ All tests passed!")
        print("\nThe MCP server is working correctly.")
        print("You can now use it in Claude Code sessions!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        process.terminate()
        await process.wait()


if __name__ == "__main__":
    print("=" * 60)
    print("Claude Swarm MCP Server Test")
    print("=" * 60)
    print()

    try:
        asyncio.run(test_mcp_server())
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
