"""Keep track of connected browser WebSocket clients."""

import asyncio

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketDisconnected


class ConnectionManager:
    def __init__(self):
        # Store active connections in a set for O(1) lookups and removals
        self.active_connections: set[WebSocket] = set()
        # Keep references to broadcast tasks so they are not garbage collected
        self._broadcast_tasks: set[asyncio.Task] = set()

    def register(self, websocket: WebSocket) -> None:
        self.active_connections.add(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def unregister(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal(
        self, message: str | bytes | dict, websocket: WebSocket
    ) -> None:
        await self._send(message, websocket)

    def broadcast(self, message: str | bytes | dict) -> None:
        """Queue a message for every client without blocking the caller."""
        for websocket in list(self.active_connections):
            task = asyncio.create_task(self._send(message, websocket))
            self._broadcast_tasks.add(task)
            task.add_done_callback(self._broadcast_tasks.discard)

    async def wait_for_pending(self) -> None:
        """Wait for queued broadcasts to finish."""
        if self._broadcast_tasks:
            await asyncio.gather(*self._broadcast_tasks, return_exceptions=True)

    async def _send(self, message: str | bytes | dict, websocket: WebSocket) -> None:
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            elif isinstance(message, bytes):
                await websocket.send_bytes(message)
            else:
                await websocket.send_text(message)
        except WebSocketDisconnect, WebSocketDisconnected, OSError:
            self.unregister(websocket)


manager = ConnectionManager()
