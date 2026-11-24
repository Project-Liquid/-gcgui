import logging

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.hardware.serial_manager import SerialManager
from app.services.broadcast_manager import manager as broadcast_manager
from app.services.data_manager import data_manager, make_serial_status_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/serial", tags=["serial"])


def _publish_serial_status(serial_status: dict) -> None:
    """Broadcast a serial connection change to every connected browser."""
    broadcast_manager.broadcast(make_serial_status_message(**serial_status))


# One manager for the whole process. Later routes should reuse this object so
# they all talk to the same physical serial port. Incoming lines are handed to
# the shared data manager, which records and broadcasts them.
serial_manager = SerialManager(
    on_line=data_manager.handle_line,
    on_status=_publish_serial_status,
)


def serial_status_message() -> dict:
    """Return the current serial state as a WebSocket message."""
    return make_serial_status_message(**serial_manager.status())


class ConnectRequest(BaseModel):
    port: str = Field(min_length=1)
    baudrate: int = Field(default=115200, gt=0)
    timeout: float = Field(default=1.0, ge=0)


class ConnectResponse(BaseModel):
    connected: bool
    port: str
    baudrate: int


class SendRequest(BaseModel):
    data: str = Field(min_length=1)

    @field_validator("data")
    @classmethod
    def data_must_be_ascii(cls, value: str) -> str:
        try:
            value.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("data must contain only ASCII characters") from exc
        return value


@router.get("/ports")
def list_ports() -> list[str]:
    """
    list all the serial ports available on the server
    """
    return serial_manager.port_list()


@router.get("/status")
def get_status() -> bool:
    """
    see if the thing has an open connection or not
    """
    return serial_manager.is_open()


@router.get("/info")
def get_info() -> dict:
    """Return connection details for the frontend status display."""
    return serial_manager.status()


@router.post("/connect")
def connect(request: ConnectRequest) -> ConnectResponse:
    "attempts a connection to a port"
    connection = serial_manager.connect_serial(
        request.port, request.baudrate, request.timeout
    )
    if connection is None:
        logger.warning("Could not connect to serial port %s", request.port)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to {request.port}",
        )
    logger.info("Connected to serial port %s at %s baud", request.port, request.baudrate)
    return ConnectResponse(
        connected=True,
        port=request.port,
        baudrate=request.baudrate,
    )


@router.post("/disconnect")
def disconnect() -> bool:
    "attempts an immediate disconnect to a port"
    serial_manager.disconnect()
    return serial_manager.is_open()


@router.post("/send")
def send(request: SendRequest) -> int:
    "send a packet of string data. returns the number of bytes written"
    written = serial_manager.send(request.data)
    if written is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No serial port is connected",
        )
    return written


@router.post("/send_raw")
def send_raw(
    data: bytes = Body(..., media_type="application/octet-stream"),
) -> int:
    "send a packet of byte data. returns the number of bytes written"
    written = serial_manager.send_raw(data)
    if written is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No serial port is connected",
        )
    return written
