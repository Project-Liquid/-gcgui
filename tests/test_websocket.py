"""Tests for backend/app/api/websocket.py."""

from app.main import app
from app.services.broadcast_manager import manager
from fastapi.testclient import TestClient

client = TestClient(app)


def test_websocket_sends_hello_message():
    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()

    assert message == {"type": "hello", "message": "WebSocket connected"}


def test_websocket_answers_ping():
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_text("ping")

        message = websocket.receive_json()

    assert message == {"type": "pong"}


def test_websocket_unregisters_on_disconnect():
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        assert len(manager.active_connections) == 1

    assert manager.active_connections == set()
