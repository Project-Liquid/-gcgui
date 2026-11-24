"""Keep track of connected browser WebSocket clients."""

import asyncio
import logging
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketDisconnected

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Broadcast messages to every connected browser.

    Serial data arrives on a reader thread, so ``broadcast`` may be called from
    outside the event-loop thread. The manager remembers the loop used by
    ``register`` and schedules sends on it safely from either thread.
    """

    def __init__(self):
        # Store active connections in a set for O(1) lookups and removals.
        self.active_connections: set[WebSocket] = set()
        # Keep references to broadcast tasks so they are not garbage collected.
        self._broadcast_tasks: set[asyncio.Task] = set()
        self._broadcast_futures: set[asyncio.Future] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def register(self, websocket: WebSocket) -> None:
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # Tests and command-line tools may register outside an event loop.
            pass
        self.active_connections.add(websocket)
        logger.info("Client connected. Total: %s", len(self.active_connections))

    def unregister(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info("Client disconnected. Total: %s", len(self.active_connections))

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Remember the application's event loop for cross-thread broadcasts."""
        self._loop = loop

    async def send_personal(
        self, message: str | bytes | dict, websocket: WebSocket
    ) -> None:
        await self._send(message, websocket)

    def broadcast(self, message: str | bytes | dict) -> None:
        """Queue a message for every client without blocking the caller."""
        connections = list(self.active_connections)
        if not connections:
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = self._loop

        if loop is None or loop.is_closed():
            logger.warning("Dropping broadcast: no running event loop")
            return

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        for websocket in connections:
            coroutine = self._send(message, websocket)
            if running_loop is loop:
                task = loop.create_task(coroutine)
                self._broadcast_tasks.add(task)
                task.add_done_callback(self._broadcast_tasks.discard)
            else:
                future = asyncio.run_coroutine_threadsafe(coroutine, loop)
                self._broadcast_futures.add(future)
                future.add_done_callback(self._broadcast_futures.discard)

    async def wait_for_pending(self) -> None:
        """Wait for queued broadcasts to finish."""
        tasks = list(self._broadcast_tasks)
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        futures = list(self._broadcast_futures)
        if futures:
            await asyncio.gather(
                *(asyncio.wrap_future(future) for future in futures),
                return_exceptions=True,
            )

    async def _send(self, message: Any, websocket: WebSocket) -> None:
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            elif isinstance(message, bytes):
                await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)
        except (WebSocketDisconnect, WebSocketDisconnected, OSError, RuntimeError):
            self.unregister(websocket)


manager = ConnectionManager()
