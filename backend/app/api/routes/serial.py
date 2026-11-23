from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.hardware.serial_manager import SerialManager

router = APIRouter(prefix="/api/serial", tags=["serial"])

# One manager for the whole process. Later routes should reuse this object so
# they all talk to the same physical serial port.
serial_manager = SerialManager()


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


@router.post("/connect")
def connect(request: ConnectRequest) -> ConnectResponse:
    "attempts a connection to a port"
    connection = serial_manager.connect_serial(
        request.port, request.baudrate, request.timeout
    )
    if connection is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to {request.port}",
        )
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
