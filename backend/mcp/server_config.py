"""
MCP Server Configuration

Defines available MCP servers that can be connected to via the API.
Each server must implement the MCP protocol via stdio.
"""

import os
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""
    id: str
    name: str
    path: str
    description: Optional[str] = None


def get_available_servers() -> List[MCPServerConfig]:
    """
    Get list of all available MCP servers.

    Returns:
        List of MCPServerConfig objects
    """
    # Base path for MCP servers
    mcp_dir = os.path.dirname(__file__)

    return [
        MCPServerConfig(
            id="expense-tracker",
            name="Expense Tracker",
            path=os.path.join(mcp_dir, "expense_server.py"),
            description="Track expenses, manage budgets, and handle recurring bills. Supports creating, updating, deleting, and querying expenses."
        ),
        # Future servers can be added here:
        # MCPServerConfig(
        #     id="weather",
        #     name="Weather Service",
        #     path="/path/to/weather_server.py",
        #     description="Get weather information for any location"
        # ),
    ]


def get_server_by_id(server_id: str) -> Optional[MCPServerConfig]:
    """
    Get server configuration by ID.

    Args:
        server_id: Server ID to look up

    Returns:
        MCPServerConfig if found, None otherwise
    """
    servers = get_available_servers()
    for server in servers:
        if server.id == server_id:
            return server
    return None
