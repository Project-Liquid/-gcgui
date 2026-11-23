from fastapi import FastAPI

from app.api.routes.serial import router as serial_router
from app.api.websocket import router as websocket_router

app = FastAPI(title="GCGUI Web Server")
app.include_router(serial_router)
app.include_router(websocket_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
