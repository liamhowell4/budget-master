"""
MCP Server Configuration - Defines available MCP servers.

This module provides server discovery and configuration for the MCP Chat Frontend.
Servers are defined as static configurations that can be connected to.
"""

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuration for an MCP server."""
    id: str
    name: str
    path: str
    description: str


def get_available_servers() -> List[ServerConfig]:
    """
    Get list of all available MCP servers.
    
    Returns:
        List of ServerConfig objects representing connectable servers.
    """
    # Get the absolute path to the expense server
    backend_dir = Path(__file__).parent.parent
    expense_server_path = str(backend_dir / "mcp" / "expense_server.py")
    
    servers = [
        ServerConfig(
            id="expense-server",
            name="Expense Server",
            path=expense_server_path,
            description="Personal expense tracking with budget management, recurring expenses, and receipt parsing"
        ),
    ]
    
    return servers


def get_server_by_id(server_id: str) -> Optional[ServerConfig]:
    """
    Get server configuration by ID.
    
    Args:
        server_id: Unique server identifier
        
    Returns:
        ServerConfig object if found, None otherwise
    """
    servers = get_available_servers()
    for server in servers:
        if server.id == server_id:
            return server
    return None

