from fastapi import FastAPI

from app.api.routes.serial import router as serial_router

app = FastAPI(title="GCGUI Web Server")
app.include_router(serial_router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
