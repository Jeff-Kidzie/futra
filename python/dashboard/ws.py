"""WebSocket connection manager with subscription-based broadcast."""
import asyncio
import json
import time
from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    """Manages WebSocket connections with subscription-based broadcast."""

    def __init__(self):
        # {websocket: {"user_id": int, "subscriptions": set[str], "last_heartbeat": float}}
        self._connections: Dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept a new WebSocket connection and register it."""
        await websocket.accept()
        self._connections[websocket] = {
            "user_id": user_id,
            "subscriptions": set(),
            "last_heartbeat": time.time(),
        }

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self._connections.pop(websocket, None)

    def subscribe(self, websocket: WebSocket, symbols: list[str]):
        """Update a client's symbol subscriptions."""
        if websocket in self._connections:
            self._connections[websocket]["subscriptions"] = set(symbols)

    async def broadcast(self, message_type: str, data: dict, symbols: list[str] = None):
        """Broadcast message to clients subscribed to any of the given symbols.
        If symbols is None, broadcast to all connected clients."""
        dead_connections = []
        message = json.dumps({"type": message_type, "data": data})
        for ws, info in list(self._connections.items()):
            if symbols is None or info["subscriptions"] & set(symbols):
                try:
                    await ws.send_text(message)
                except Exception:
                    dead_connections.append(ws)
        for ws in dead_connections:
            self.disconnect(ws)

    async def broadcast_to_all(self, message_type: str, data: dict):
        """Broadcast to ALL connected clients regardless of subscription."""
        await self.broadcast(message_type, data, symbols=None)

    async def handle_client_messages(self, websocket: WebSocket):
        """Process incoming client messages (subscribe, ping)."""
        try:
            while True:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
                if msg.get("type") == "subscribe":
                    self.subscribe(websocket, msg.get("symbols", []))
                elif msg.get("type") == "ping":
                    if websocket in self._connections:
                        self._connections[websocket]["last_heartbeat"] = time.time()
                    await websocket.send_text(json.dumps({"type": "pong", "data": {}}))
        except Exception:
            self.disconnect(websocket)

    async def heartbeat_check(self):
        """Remove connections that haven't sent a ping in 60 seconds."""
        now = time.time()
        dead = [
            ws for ws, info in self._connections.items()
            if now - info["last_heartbeat"] > 60
        ]
        for ws in dead:
            try:
                await ws.close(code=1000, reason="Heartbeat timeout")
            except Exception:
                pass
            self.disconnect(ws)

    @property
    def connected_count(self) -> int:
        """Number of currently connected clients."""
        return len(self._connections)

    @property
    def connections(self) -> dict:
        """Get a copy of current connections (for testing)."""
        return dict(self._connections)


# Singleton instance
manager = ConnectionManager()
