from fastapi import FastAPI

app = FastAPI(title="GCGUI Web Server")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
