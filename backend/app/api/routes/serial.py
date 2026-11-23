from fastapi import APIRouter
import serial

from app.hardware.serial_manager import SerialManager

router = APIRouter(prefix="/api/serial", tags=["serial"])

# One manager for the whole process. Later routes should reuse this object so
# they all talk to the same physical serial port.
serial_manager = SerialManager()


@router.get("/ports")
def list_ports() -> list[str]:
    """
    list all the serial ports available on the server
    """
    return serial_manager.port_list()

@router.get("/status")
def get_status() -> bool :
    """
    see if the thing has an open connection or not
    """
    return serial_manager.is_open()

@router.post("/connect")
def connect(port: str, baudrate: int, timeout: float):
    "attempts a connection to a port"
    serial_manager.connect_serial(port, baudrate, timeout)

@router.post("/disconnect")
def disconnect():
    "attempts an immediate disconnect to a port"
    serial_manager.disconnect()

@router.post("/send")
def send(data: str) -> int | None:
    "send a packet of string data. returns status as int or None"
    return serial_manager.send(data)

@router.post("/send_raw")
def send_raw(data:bytes) -> int | None:
    "send a packet of byte data. returns status as int or None"
    return serial_manager.send_raw(data)
