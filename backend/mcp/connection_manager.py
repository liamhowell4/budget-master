"""
MCP Connection State Manager

Manages active MCP server connections. Only one server can be connected at a time.
Tracks connection state and available tools.
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from .client import MCPClient


@dataclass
class ConnectionState:
    """Current connection state."""
    connected: bool
    server_id: Optional[str] = None
    server_name: Optional[str] = None
    tools: List[Dict[str, str]] = None
    client: Optional[MCPClient] = None

    def __post_init__(self):
        if self.tools is None:
            self.tools = []


class ConnectionManager:
    """
    Singleton manager for MCP server connections.

    Only one server can be connected at a time. Handles connection lifecycle
    and state tracking.
    """

    _instance: Optional['ConnectionManager'] = None
    _state: ConnectionState

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._state = ConnectionState(connected=False)
        return cls._instance

    @property
    def state(self) -> ConnectionState:
        """Get current connection state."""
        return self._state

    @property
    def is_connected(self) -> bool:
        """Check if a server is currently connected."""
        return self._state.connected

    @property
    def current_server_id(self) -> Optional[str]:
        """Get ID of currently connected server."""
        return self._state.server_id

    @property
    def current_tools(self) -> List[Dict[str, str]]:
        """Get tools available on current server."""
        return self._state.tools if self._state.tools else []

    async def connect(
        self,
        server_id: str,
        server_name: str,
        server_path: str
    ) -> tuple[bool, List[Dict[str, str]], Optional[str]]:
        """
        Connect to an MCP server.

        Args:
            server_id: ID of server to connect to
            server_name: Display name of server
            server_path: Path to server script

        Returns:
            Tuple of (success, tools_list, error_message)
            - success: True if connection successful
            - tools_list: List of available tools
            - error_message: Error message if failed, None otherwise
        """
        # Disconnect from current server if any
        if self.is_connected:
            await self.disconnect()

        try:
            # Create new MCP client
            client = MCPClient()

            # Connect to server
            await client.connect_to_server(server_path)

            # Get available tools
            response = await client.session.list_tools()
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
                tools=tools,
                client=client
            )

            print(f"✅ Connected to {server_name} ({len(tools)} tools available)")
            return True, tools, None

        except Exception as e:
            error_msg = f"Failed to connect to server: {str(e)}"
            print(f"❌ {error_msg}")
            return False, [], error_msg

    async def disconnect(self) -> bool:
        """
        Disconnect from current server.

        Returns:
            True if disconnected successfully
        """
        if not self.is_connected:
            return True

        try:
            # Clean up client
            if self._state.client:
                await self._state.client.cleanup()

            # Reset state
            self._state = ConnectionState(connected=False)
            print("✅ Disconnected from server")
            return True

        except Exception as e:
            print(f"❌ Error disconnecting: {e}")
            # Reset state anyway
            self._state = ConnectionState(connected=False)
            return False

    def get_client(self) -> Optional[MCPClient]:
        """
        Get the current MCP client.

        Returns:
            MCPClient if connected, None otherwise
        """
        if not self.is_connected:
            return None
        return self._state.client


# Global singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager singleton.

    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
