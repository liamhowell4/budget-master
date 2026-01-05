"""
MCP Connection Manager - Manages connections to MCP servers.

This module provides a singleton connection manager that:
- Maintains connection state
- Handles server connection/disconnection
- Provides access to the active MCP client
"""

import os
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from .client import MCPClient


@dataclass
class ConnectionState:
    """Represents the current connection state."""
    connected: bool
    server_id: Optional[str] = None
    server_name: Optional[str] = None
    tools: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.tools is None:
            self.tools = []


class ConnectionManager:
    """
    Manages MCP server connections.
    
    Only one server can be connected at a time. Connecting to a new server
    will automatically disconnect from the current server.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self._state = ConnectionState(connected=False)
        self._client: Optional[MCPClient] = None
    
    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to a server."""
        return self._state.connected
    
    async def connect(
        self,
        server_id: str,
        server_name: str,
        server_path: str
    ) -> Tuple[bool, List[Dict[str, str]], Optional[str]]:
        """
        Connect to an MCP server.
        
        If already connected to another server, disconnects first.
        
        Args:
            server_id: Unique server identifier
            server_name: Human-readable server name
            server_path: Path to the server script
            
        Returns:
            Tuple of (success, tools, error_message)
            - success: True if connection succeeded
            - tools: List of available tools (empty on failure)
            - error_message: Error description (None on success)
        """
        try:
            # Disconnect from current server if connected
            if self.is_connected:
                print(f"🔄 Disconnecting from {self._state.server_id} before connecting to {server_id}")
                await self.disconnect()
            
            # Create new client
            print(f"🔄 Connecting to {server_name} ({server_id})...")
            self._client = MCPClient()
            
            # Connect to server
            await self._client.connect_to_server(server_path)
            
            # List available tools
            response = await self._client.session.list_tools()
            tools = [
                {
                    "name": tool.name,
                    "description": tool.description
                }
                for tool in response.tools
            ]
            
            # Update state
            self._state = ConnectionState(
                connected=True,
                server_id=server_id,
                server_name=server_name,
                tools=tools
            )
            
            print(f"✅ Connected to {server_name} with {len(tools)} tools")
            return True, tools, None
            
        except Exception as e:
            error_msg = f"Failed to connect to {server_name}: {str(e)}"
            print(f"❌ {error_msg}")
            
            # Ensure state is disconnected on failure
            self._state = ConnectionState(connected=False)
            self._client = None
            
            return False, [], error_msg
    
    async def disconnect(self) -> None:
        """
        Disconnect from current server.
        
        Cleans up client resources and resets connection state.
        """
        if self._client:
            try:
                print(f"🔄 Disconnecting from {self._state.server_id}...")
                await self._client.cleanup()
                print("✅ Disconnected successfully")
            except Exception as e:
                print(f"⚠️ Error during disconnect: {e}")
        
        # Reset state
        self._state = ConnectionState(connected=False)
        self._client = None
    
    def get_client(self) -> Optional[MCPClient]:
        """
        Get the active MCP client.
        
        Returns:
            MCPClient instance if connected, None otherwise
        """
        return self._client


# Singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the singleton connection manager instance.
    
    Returns:
        Global ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager

