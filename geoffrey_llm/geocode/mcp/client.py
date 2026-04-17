"""MCP client implementation for geocode.

Simplified MCP client using the official MCP SDK.
"""

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional

from geoffrey_llm.geocode.tools.base import Tool, ToolInput, ToolResult


@dataclass
class MCPTool:
    """Represents a tool from an MCP server."""
    name: str  # e.g., "mcp__filesystem__read_file"
    original_name: str  # e.g., "read_file"
    server_name: str  # e.g., "filesystem"
    description: str
    input_schema: dict


class MCPClient:
    """
    MCP client for connecting to MCP servers.

    Supports stdio transport for local servers.
    """

    def __init__(self, server_name: str, config: dict):
        self.server_name = server_name
        self.config = config
        self._process: Optional[asyncio.subprocess.Process] = None
        self._request_id = 0
        self._pending_requests: dict[str, asyncio.Future] = {}

    async def connect(self) -> None:
        """Connect to the MCP server."""
        command = self.config.get("command")
        args = self.config.get("args", [])
        env = self.config.get("env", {})

        if not command:
            raise ValueError(f"MCP server {self.server_name}: missing command")

        # Merge env with current env
        full_env = {**asyncio.get_event_loop().run_in_executor(None, lambda: dict(__import__("os").environ))()}
        full_env.update(env)

        # Start the process
        self._process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )

        # Initialize the MCP protocol
        await self._send_init()

    async def _send_init(self) -> None:
        """Send initialization request to MCP server."""
        init_request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {
                    "name": "geocode",
                    "version": "0.1.0",
                },
            },
        }

        await self._send_jsonrpc(init_request)

        # Read response
        response = await self._read_jsonrpc()
        if response.get("error"):
            raise Exception(f"MCP init error: {response['error']}")

    async def _send_jsonrpc(self, message: dict) -> None:
        """Send a JSON-RPC message."""
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP client not connected")

        content = json.dumps(message)
        length = len(content.encode("utf-8"))

        # Write with content-length header (MCP stdio protocol)
        self._process.stdin.write(f"Content-Length: {length}\r\n".encode("utf-8"))
        self._process.stdin.write(b"\r\n")
        self._process.stdin.write(content.encode("utf-8"))
        await self._process.stdin.drain()

    async def _read_jsonrpc(self) -> dict:
        """Read a JSON-RPC message."""
        if not self._process or not self._process.stdout:
            raise RuntimeError("MCP client not connected")

        # Read header
        headers = {}
        while True:
            line = await self._process.stdout.readline()
            line = line.decode("utf-8").strip()
            if not line:
                break
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Read content
        content_length = int(headers.get("Content-Length", 0))
        if content_length > 0:
            content = await self._process.stdout.read(content_length)
            return json.loads(content.decode("utf-8"))

        return {}

    def _next_id(self) -> str:
        """Get next request ID."""
        self._request_id += 1
        return str(self._request_id)

    async def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server."""
        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        }

        await self._send_jsonrpc(request)
        response = await self._read_jsonrpc()

        if response.get("error"):
            raise Exception(f"MCP list tools error: {response['error']}")

        tools = []
        result = response.get("result", {})
        tool_definitions = result.get("tools", [])

        for tool_def in tool_definitions:
            name = tool_def.get("name", "")
            tools.append(MCPTool(
                name=f"mcp__{self.server_name}__{name}",
                original_name=name,
                server_name=self.server_name,
                description=tool_def.get("description", ""),
                input_schema=tool_def.get("inputSchema", {}),
            ))

        return tools

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the MCP server."""
        # Remove the mcp__ prefix to get original name
        parts = tool_name.split("__")
        if len(parts) >= 3:
            original_name = parts[2]
        else:
            original_name = tool_name

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {
                "name": original_name,
                "arguments": arguments,
            },
        }

        await self._send_jsonrpc(request)
        response = await self._read_jsonrpc()

        if response.get("error"):
            return {"success": False, "error": str(response["error"])}

        result = response.get("result", {})
        return {"success": True, "content": result.get("content", [])}

    async def disconnect(self) -> None:
        """Disconnect from the MCP server."""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None


class MCPServerRegistry:
    """
    Registry for managing multiple MCP server connections.
    """

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            home = Path.home()
            geoffrey_dir = home / ".geoffrey"
            config_path = geoffrey_dir / "mcp.json"

        self.config_path = Path(config_path)
        self._clients: dict[str, MCPClient] = {}
        self._tools: list[MCPTool] = []

    def load_config(self) -> dict:
        """Load MCP configuration from JSON file."""
        if not self.config_path.exists():
            return {"mcpServers": {}}

        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    async def initialize(self) -> None:
        """Initialize all configured MCP servers."""
        config = self.load_config()
        servers = config.get("mcpServers", {})

        for server_name, server_config in servers.items():
            try:
                client = MCPClient(server_name, server_config)
                await client.connect()

                # Get tools from server
                tools = await client.list_tools()
                self._clients[server_name] = client
                self._tools.extend(tools)

            except Exception as e:
                print(f"Warning: Failed to connect to MCP server {server_name}: {e}")

    async def disconnect_all(self) -> None:
        """Disconnect all MCP servers."""
        for client in self._clients.values():
            await client.disconnect()
        self._clients.clear()
        self._tools.clear()

    def list_tools(self) -> list[MCPTool]:
        """List all available tools from all servers."""
        return self._tools.copy()

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call a tool on the appropriate MCP server."""
        # Parse server name from tool name
        parts = tool_name.split("__")
        if len(parts) >= 3:
            server_name = parts[1]
        else:
            return {"success": False, "error": f"Invalid MCP tool name: {tool_name}"}

        client = self._clients.get(server_name)
        if not client:
            return {"success": False, "error": f"Unknown MCP server: {server_name}"}

        return await client.call_tool(tool_name, arguments)

    def get_mcp_tool(self, tool_name: str) -> Optional[MCPTool]:
        """Get an MCP tool by name."""
        for tool in self._tools:
            if tool.name == tool_name:
                return tool
        return None
