"""Tests for WebSocket connection manager and endpoint."""
import json
import pytest
from fastapi.testclient import TestClient
from python.dashboard.ws import ConnectionManager


@pytest.fixture
def ws_manager():
    """Fresh ConnectionManager for isolated tests."""
    mgr = ConnectionManager()
    yield mgr
    # Clean up all connections
    for ws in list(mgr._connections.keys()):
        mgr.disconnect(ws)


class TestConnectionManager:
    """Unit tests for ConnectionManager."""

    def test_connect_and_disconnect(self, ws_manager):
        """Connections are tracked and can be removed."""
        # Mock websocket
        class MockWebSocket:
            async def accept(self):
                pass
            async def send_text(self, text):
                pass

        ws = MockWebSocket()
        assert ws_manager.connected_count == 0

        # Use asyncio to run connect
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.connect(ws, 1))
        assert ws_manager.connected_count == 1

        ws_manager.disconnect(ws)
        assert ws_manager.connected_count == 0

    def test_subscribe_updates_symbols(self, ws_manager):
        """Subscribe adds symbols to client's subscription set."""
        class MockWebSocket:
            async def accept(self):
                pass
            async def send_text(self, text):
                pass

        ws = MockWebSocket()
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.connect(ws, 1))

        ws_manager.subscribe(ws, ["EURUSD", "GBPUSD"])
        info = ws_manager._connections[ws]
        assert info["subscriptions"] == {"EURUSD", "GBPUSD"}

        loop.close()

    def test_broadcast_to_subscribed(self, ws_manager):
        """Only subscribed clients receive broadcast."""
        messages_received = []

        class MockWebSocket:
            def __init__(self, name):
                self.name = name

            async def accept(self):
                pass

            async def send_text(self, text):
                messages_received.append((self.name, text))

        ws1 = MockWebSocket("ws1")
        ws2 = MockWebSocket("ws2")

        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.connect(ws1, 1))
        loop.run_until_complete(ws_manager.connect(ws2, 2))

        ws_manager.subscribe(ws1, ["EURUSD"])
        ws_manager.subscribe(ws2, ["GBPUSD"])

        loop.run_until_complete(
            ws_manager.broadcast("test", {"msg": "hello"}, symbols=["EURUSD"])
        )

        # Only ws1 should receive
        assert len(messages_received) == 1
        assert messages_received[0][0] == "ws1"
        data = json.loads(messages_received[0][1])
        assert data["type"] == "test"

        loop.close()

    def test_broadcast_to_all(self, ws_manager):
        """Broadcast to all reaches all clients regardless of subscription."""
        messages_received = []

        class MockWebSocket:
            def __init__(self, name):
                self.name = name

            async def accept(self):
                pass

            async def send_text(self, text):
                messages_received.append((self.name, text))

        ws1 = MockWebSocket("ws1")
        ws2 = MockWebSocket("ws2")

        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.connect(ws1, 1))
        loop.run_until_complete(ws_manager.connect(ws2, 2))

        ws_manager.subscribe(ws1, ["EURUSD"])

        loop.run_until_complete(
            ws_manager.broadcast_to_all("alert", {"severity": "critical"})
        )

        assert len(messages_received) == 2
        loop.close()

    def test_heartbeat_cleanup(self, ws_manager):
        """Connections without recent heartbeat are cleaned up."""
        class MockWebSocket:
            def __init__(self):
                self.closed = False
                self.close_code = None

            async def accept(self):
                pass

            async def send_text(self, text):
                pass

            async def close(self, code=1000, reason=""):
                self.closed = True
                self.close_code = code

        ws = MockWebSocket()
        import asyncio
        loop = asyncio.new_event_loop()
        loop.run_until_complete(ws_manager.connect(ws, 1))

        # Set last_heartbeat far in the past
        ws_manager._connections[ws]["last_heartbeat"] = 0

        loop.run_until_complete(ws_manager.heartbeat_check())
        assert ws_manager.connected_count == 0
        loop.close()


class TestWebSocketEndpoint:
    """Integration tests for /ws WebSocket endpoint."""

    def test_connect_with_valid_token(self, client, auth_headers):
        """Test 1: WebSocket connects with valid token."""
        token = auth_headers["Authorization"].split(" ")[1]
        with client.websocket_connect(f"/ws?token={token}") as ws:
            assert ws  # Connection established

    def test_connect_without_token(self, client):
        """Test 2: WebSocket without token is rejected."""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws"):
                pass

    def test_connect_with_invalid_token(self, client):
        """Test 3: WebSocket with invalid token is rejected."""
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=invalid_token_123"):
                pass

    def test_client_sends_ping_receives_pong(self, client, auth_headers):
        """Test 6: Client sends ping, server responds with pong."""
        token = auth_headers["Authorization"].split(" ")[1]
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_text(json.dumps({"type": "ping", "data": {}}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"

    def test_client_subscribes(self, client, auth_headers):
        """Test 4: Client sends subscribe message."""
        token = auth_headers["Authorization"].split(" ")[1]
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_text(json.dumps({
                "type": "subscribe",
                "symbols": ["EURUSD", "GBPUSD"],
            }))
            # Subscription should be accepted (no error response)
            # Send ping to verify connection still alive
            ws.send_text(json.dumps({"type": "ping", "data": {}}))
            response = ws.receive_text()
            data = json.loads(response)
            assert data["type"] == "pong"

    def test_disconnect_cleans_up(self, client, auth_headers):
        """Test 7: Client disconnect removes from pool."""
        token = auth_headers["Authorization"].split(" ")[1]
        with client.websocket_connect(f"/ws?token={token}") as ws:
            ws.send_text(json.dumps({"type": "ping", "data": {}}))
            ws.receive_text()  # pong

        # After context exit, connection is closed
        # Reconnect should work (proves cleanup happened)
        with client.websocket_connect(f"/ws?token={token}") as ws2:
            ws2.send_text(json.dumps({"type": "ping", "data": {}}))
            response = ws2.receive_text()
            assert json.loads(response)["type"] == "pong"
