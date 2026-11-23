import asyncio
import json

import websockets


class ConnectionManager:
    def __init__(self):
        # Store active connections in a set for O(1) lookups and removals
        self.active_connections: set[websockets.ServerConnection] = set()

    def register(self, websocket):
        self.active_connections.add(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def unregister(self, websocket):
        self.active_connections.discard(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def send_personal(self, message: str, websocket):
        await websocket.send(message)

    def broadcast(self, message: str | bytes | dict) -> None:
        if self.active_connections:
            if isinstance(message, dict):
                message = json.dumps(message)
            # websockets.broadcast efficiently sends to all connections concurrently
            websockets.broadcast(self.active_connections, message)


manager = ConnectionManager()


async def handler(websocket):
    manager.register(websocket)
    try:
        async for message in websocket:
            manager.broadcast(f"User says: {message}")
    finally:
        manager.unregister(websocket)


async def main():
    async with websockets.serve(handler, "localhost", 8765):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())
