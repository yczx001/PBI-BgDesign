"""MCP client manager for connecting to external MCP servers."""
import json
from pathlib import Path


def load_mcp_config(path: str) -> dict:
    """Load MCP config from JSON file (dictionary format)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"mcpServers": {}}


class MCPClientManager:
    """Manage connections to MCP servers and aggregate their tools."""

    def __init__(self):
        self.connected_servers: dict[str, object] = {}
        self._tools: list[dict] = []

    def _infer_transport(self, config: dict) -> str:
        """Infer transport type from config fields."""
        if "command" in config:
            return "stdio"
        if "url" in config:
            return "sse"
        return "stdio"

    async def connect_all(self, config: dict):
        """Connect to all configured MCP servers."""
        servers = config.get("mcpServers", {})
        for name, server_config in servers.items():
            transport = self._infer_transport(server_config)
            try:
                # MCP SDK connection would go here
                # For now, store the config for later connection
                self.connected_servers[name] = {
                    "config": server_config,
                    "transport": transport,
                    "status": "configured",
                }
            except Exception:
                self.connected_servers[name] = {
                    "config": server_config,
                    "transport": transport,
                    "status": "error",
                }

    def get_tools(self) -> list[dict]:
        """Get aggregated tool definitions from all connected servers."""
        return self._tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Call a tool on a specific MCP server."""
        if server_name not in self.connected_servers:
            return f"Server '{server_name}' not connected."
        # MCP SDK tool call would go here
        return f"Tool '{tool_name}' called on '{server_name}' with {arguments}"
