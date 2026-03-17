"""Kiha Server — WebSocket Handler (Placeholder)."""

import logging
from typing import Protocol

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketMessageHandler(Protocol):
    """Interface for processing incoming WebSocket messages."""

    async def handle_message(self, client_id: str, message: str) -> str:
        """Process a message and return a response."""
        ...


class ConnectionManager:
    """Manage active WebSocket connections to mobile clients."""

    def __init__(self) -> None:
        self._active_connections: dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._active_connections[client_id] = websocket
        logger.error("Client connected: %s", client_id)

    def disconnect(self, client_id: str) -> None:
        """Remove a disconnected client."""
        self._active_connections.pop(client_id, None)
        logger.error("Client disconnected: %s", client_id)

    async def send_to_client(self, client_id: str, message: str) -> None:
        """Send a message to a specific connected client."""
        websocket = self._active_connections.get(client_id)
        if websocket:
            await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Send a message to all connected clients."""
        for ws in self._active_connections.values():
            await ws.send_text(message)

    @property
    def active_count(self) -> int:
        """Return the number of active connections."""
        return len(self._active_connections)
