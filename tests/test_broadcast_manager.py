"""Tests for backend/app/services/broadcast_manager.py."""

import asyncio
from datetime import UTC, datetime

from app.services.broadcast_manager import ConnectionManager
from app.services.data_manager import DataManager


class FakeWebSocket:
    def __init__(self, fail=False):
        self.sent = []
        self.fail = fail

    async def send_json(self, message):
        if self.fail:
            raise OSError("connection closed")
        self.sent.append(message)

    async def send_text(self, message):
        if self.fail:
            raise OSError("connection closed")
        self.sent.append(message)

    async def send_bytes(self, message):
        if self.fail:
            raise OSError("connection closed")
        self.sent.append(message)


def test_register_and_unregister_connection():
    manager = ConnectionManager()
    connection = FakeWebSocket()

    manager.register(connection)
    assert connection in manager.active_connections

    manager.unregister(connection)
    assert connection not in manager.active_connections


def test_unregister_missing_connection_is_safe():
    manager = ConnectionManager()

    manager.unregister(FakeWebSocket())

    assert manager.active_connections == set()


def test_send_personal_sends_text_and_bytes():
    manager = ConnectionManager()
    connection = FakeWebSocket()

    async def run():
        await manager.send_personal("hello", connection)
        await manager.send_personal(b"\x00\x01", connection)

    asyncio.run(run())

    assert connection.sent == ["hello", b"\x00\x01"]


def test_broadcast_without_connections_does_nothing():
    manager = ConnectionManager()

    async def run():
        manager.broadcast({"type": "serial_data", "data": "hello"})
        await manager.wait_for_pending()

    asyncio.run(run())

    assert manager.active_connections == set()
    assert manager._broadcast_tasks == set()


def test_broadcast_sends_to_all_connections():
    manager = ConnectionManager()
    first = FakeWebSocket()
    second = FakeWebSocket()
    manager.register(first)
    manager.register(second)
    message = {
        "type": "serial_data",
        "timestamp": "2026-01-01T12:00:00Z",
        "data": "hello",
    }

    async def run():
        manager.broadcast(message)
        await manager.wait_for_pending()

    asyncio.run(run())

    assert first.sent == [message]
    assert second.sent == [message]


def test_failed_broadcast_unregisters_connection():
    manager = ConnectionManager()
    connection = FakeWebSocket(fail=True)
    manager.register(connection)

    async def run():
        manager.broadcast({"type": "serial_data", "data": "hello"})
        await manager.wait_for_pending()

    asyncio.run(run())

    assert connection not in manager.active_connections


def test_data_manager_sends_message_through_broadcast_manager():
    manager = ConnectionManager()
    connection = FakeWebSocket()
    manager.register(connection)
    data_manager = DataManager(broadcast_manager=manager)
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    async def run():
        message = data_manager.handle_line("hello\r\n", timestamp)
        await manager.wait_for_pending()
        return message

    message = asyncio.run(run())

    assert connection.sent == [message]


def test_broadcast_from_worker_thread_reaches_clients():
    manager = ConnectionManager()
    connection = FakeWebSocket()
    message = {"type": "serial_data", "timestamp": "2026-01-01T12:00:00Z", "data": "hi"}

    async def run():
        manager.register(connection)
        await asyncio.to_thread(manager.broadcast, message)
        await manager.wait_for_pending()

    asyncio.run(run())

    assert connection.sent == [message]
