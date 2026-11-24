"""WebSocket endpoint for live browser updates."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.routes.serial import serial_status_message
from app.services.broadcast_manager import manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Keep one browser connected and registered for serial broadcasts."""
    await websocket.accept()
    manager.register(websocket)
    await manager.send_personal(
        {"type": "hello", "message": "WebSocket connected"}, websocket
    )
    await manager.send_personal(serial_status_message(), websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message.strip() == "ping":
                await manager.send_personal({"type": "pong"}, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.unregister(websocket)
