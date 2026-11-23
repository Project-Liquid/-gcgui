"""Tests for backend/app/services/broadcast_manager.py."""

import asyncio
import json
from datetime import UTC, datetime

from app.services import broadcast_manager
from app.services.broadcast_manager import ConnectionManager
from app.services.data_manager import DataManager


class FakeConnection:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self.sent = []

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.messages:
            raise StopAsyncIteration
        return self.messages.pop(0)

    async def send(self, message):
        self.sent.append(message)


def test_register_and_unregister_connection():
    manager = ConnectionManager()
    connection = FakeConnection()

    manager.register(connection)
    assert connection in manager.active_connections

    manager.unregister(connection)
    assert connection not in manager.active_connections


def test_unregister_missing_connection_is_safe():
    manager = ConnectionManager()

    manager.unregister(FakeConnection())

    assert manager.active_connections == set()


def test_send_personal():
    manager = ConnectionManager()
    connection = FakeConnection()

    asyncio.run(manager.send_personal("hello", connection))

    assert connection.sent == ["hello"]


def test_broadcast_without_connections_does_nothing(monkeypatch):
    calls = []
    monkeypatch.setattr(
        broadcast_manager.websockets,
        "broadcast",
        lambda connections, message: calls.append((connections, message)),
    )
    manager = ConnectionManager()

    manager.broadcast("hello")

    assert calls == []


def test_broadcast_sends_string(monkeypatch):
    calls = []
    monkeypatch.setattr(
        broadcast_manager.websockets,
        "broadcast",
        lambda connections, message: calls.append((connections, message)),
    )
    manager = ConnectionManager()
    connection = FakeConnection()
    manager.register(connection)

    manager.broadcast("hello")

    assert calls[0][0] == {connection}
    assert calls[0][1] == "hello"


def test_broadcast_serializes_dict_as_json(monkeypatch):
    calls = []
    monkeypatch.setattr(
        broadcast_manager.websockets,
        "broadcast",
        lambda connections, message: calls.append(message),
    )
    manager = ConnectionManager()
    manager.register(FakeConnection())
    message = {
        "type": "serial_data",
        "timestamp": "2026-01-01T12:00:00Z",
        "data": "hello",
    }

    manager.broadcast(message)

    assert json.loads(calls[0]) == message


def test_data_manager_sends_json_through_broadcast_manager(monkeypatch):
    sent = []
    monkeypatch.setattr(
        broadcast_manager.websockets,
        "broadcast",
        lambda connections, message: sent.append(message),
    )
    manager = ConnectionManager()
    manager.register(FakeConnection())
    data_manager = DataManager(broadcast_manager=manager)
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    message = data_manager.handle_line("hello\r\n", timestamp)

    assert json.loads(sent[0]) == message


def test_handler_registers_broadcasts_and_unregisters(monkeypatch):
    calls = []
    monkeypatch.setattr(
        broadcast_manager.websockets,
        "broadcast",
        lambda connections, message: calls.append((set(connections), message)),
    )
    manager = ConnectionManager()
    monkeypatch.setattr(broadcast_manager, "manager", manager)
    connection = FakeConnection(messages=["one", "two"])

    asyncio.run(broadcast_manager.handler(connection))

    assert calls == [
        ({connection}, "User says: one"),
        ({connection}, "User says: two"),
    ]
    assert manager.active_connections == set()
