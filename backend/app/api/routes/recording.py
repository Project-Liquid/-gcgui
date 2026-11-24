from fastapi import APIRouter, Body, HTTPException, status
# from pydantic import BaseModel, Field, field_validator

from app.services.recording_manager import recorder

router = APIRouter(prefix="/api/recording", tags=["recording"])

r = recorder()

@router.get("/start")
def begin_recording():
    r.start()

@router.post("/stop")
def end_recording():
    r.stop()

@router.get("/status")
def recording_status():
    return r.active()

@router.get("/list")
def recording_list():
    return r.list()
