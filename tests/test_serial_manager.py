"""Tests for backend/app/hardware/serial_manager.py.

These tests use mocks, so they do not need a real serial device attached.
"""

import threading
import time
from unittest.mock import MagicMock, call

import serial
from app.hardware import serial_manager
from app.hardware.serial_manager import SerialManager


class FakePort:
    def __init__(self, device):
        self.device = device


def make_manager(ser=None):
    """Create a manager whose underlying serial object is a mock."""
    manager = SerialManager()
    manager.ser = ser if ser is not None else MagicMock(is_open=False)
    return manager


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------


def test_list_ports_is_callable_on_class_and_instance(monkeypatch):
    ports = [FakePort("/dev/ttyUSB0")]
    monkeypatch.setattr(
        serial_manager.serial.tools.list_ports, "comports", lambda: ports
    )
    manager = make_manager()

    assert SerialManager.list_ports() == ports
    assert manager.list_ports() == ports


def test_port_list_returns_device_names(monkeypatch):
    ports = [FakePort("/dev/ttyUSB0"), FakePort("/dev/ttyACM0")]
    monkeypatch.setattr(
        serial_manager.serial.tools.list_ports, "comports", lambda: ports
    )

    assert make_manager().port_list() == ["/dev/ttyUSB0", "/dev/ttyACM0"]


def test_port_list_returns_empty_list_when_no_ports(monkeypatch):
    monkeypatch.setattr(serial_manager.serial.tools.list_ports, "comports", list)

    assert make_manager().port_list() == []


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_each_manager_owns_its_serial_port(monkeypatch):
    made = []

    def make_serial(*args, **kwargs):
        port = MagicMock(name=f"serial-{len(made)}")
        made.append(port)
        return port

    monkeypatch.setattr(serial_manager.serial, "Serial", make_serial)

    first = SerialManager()
    second = SerialManager()

    # The serial object must be per-instance, not shared through the class.
    assert "ser" not in vars(SerialManager)
    assert first.ser is made[0]
    assert second.ser is made[1]
    assert first.ser is not second.ser


# ---------------------------------------------------------------------------
# Connecting
# ---------------------------------------------------------------------------


def test_connect_serial_stores_and_returns_open_connection(monkeypatch):
    initial = MagicMock(is_open=False)
    connection = MagicMock(is_open=True)
    serial_ctor = MagicMock(side_effect=[initial, connection])
    monkeypatch.setattr(serial_manager.serial, "Serial", serial_ctor)

    manager = SerialManager()
    result = manager.connect_serial("/dev/ttyUSB0", baudrate=115200, timeout=2.5)

    assert result is connection
    assert manager.ser is connection
    assert manager.is_open() is True
    assert serial_ctor.call_args == call(
        port="/dev/ttyUSB0",
        baudrate=115200,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=2.5,
    )


def test_connect_serial_closes_previous_connection_before_reconnecting(monkeypatch):
    old = MagicMock(is_open=True)
    new = MagicMock(is_open=True)
    manager = make_manager(old)
    monkeypatch.setattr(serial_manager.serial, "Serial", MagicMock(return_value=new))

    assert manager.connect_serial("/dev/ttyUSB1") is new
    old.close.assert_called_once_with()
    assert manager.ser is new


def test_connect_serial_returns_none_and_reports_failure(monkeypatch, caplog):
    manager = make_manager()
    monkeypatch.setattr(
        serial_manager.serial,
        "Serial",
        MagicMock(side_effect=serial.SerialException("port is busy")),
    )

    assert manager.connect_serial("/dev/ttyUSB0") is None
    assert "Failed to connect to /dev/ttyUSB0" in caplog.text
    assert manager.is_open() is False


def test_connect_serial_returns_none_for_invalid_settings(monkeypatch, caplog):
    manager = make_manager()
    monkeypatch.setattr(
        serial_manager.serial,
        "Serial",
        MagicMock(side_effect=ValueError("Not a valid baudrate")),
    )

    assert manager.connect_serial("COM1", baudrate=-1) is None
    assert "Failed to connect to COM1" in caplog.text


def test_connect_serial_closes_connection_that_did_not_open(monkeypatch):
    initial = MagicMock(is_open=False)
    connection = MagicMock(is_open=False)
    serial_ctor = MagicMock(side_effect=[initial, connection])
    monkeypatch.setattr(serial_manager.serial, "Serial", serial_ctor)

    manager = SerialManager()

    assert manager.connect_serial("COM1") is None
    connection.close.assert_called_once_with()
    assert manager.ser is initial


# ---------------------------------------------------------------------------
# Disconnecting
# ---------------------------------------------------------------------------


def test_disconnect_closes_open_port():
    manager = make_manager()
    ser = MagicMock(is_open=True)
    ser.close.side_effect = lambda: setattr(ser, "is_open", False)
    manager.ser = ser

    manager.disconnect()

    ser.close.assert_called_once_with()
    assert manager.is_open() is False


def test_disconnect_does_nothing_when_port_is_closed():
    ser = MagicMock(is_open=False)
    manager = make_manager(ser)

    manager.disconnect()

    ser.close.assert_not_called()


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------


def test_send_writes_ascii_bytes():
    ser = MagicMock(is_open=True)
    ser.write.return_value = 5
    manager = make_manager(ser)

    assert manager.send("hello") == 5
    ser.write.assert_called_once_with(b"hello")


def test_send_returns_none_when_port_is_closed():
    ser = MagicMock(is_open=False)
    manager = make_manager(ser)

    assert manager.send("hello") is None
    ser.write.assert_not_called()


def test_send_raw_writes_bytes():
    ser = MagicMock(is_open=True)
    ser.write.return_value = 3
    manager = make_manager(ser)

    assert manager.send_raw(b"\x00\x01\x02") == 3
    ser.write.assert_called_once_with(b"\x00\x01\x02")


def test_send_raw_returns_none_when_port_is_closed():
    ser = MagicMock(is_open=False)
    manager = make_manager(ser)

    assert manager.send_raw(b"\x00") is None
    ser.write.assert_not_called()


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def test_read_returns_raw_bytes_when_open():
    ser = MagicMock(is_open=True)
    ser.read_all.return_value = b"\x00\x01\xff"
    manager = make_manager(ser)

    assert manager.read() == b"\x00\x01\xff"
    ser.read_all.assert_called_once_with()


def test_read_returns_none_when_port_is_closed():
    ser = MagicMock(is_open=False)
    manager = make_manager(ser)

    assert manager.read() is None
    ser.read_all.assert_not_called()


def test_fread_decodes_ascii_when_open():
    ser = MagicMock(is_open=True)
    ser.read_all.return_value = b"2172.562 R29\r\n"
    manager = make_manager(ser)

    assert manager.fread() == "2172.562 R29\r\n"


def test_fread_returns_none_for_non_ascii_data():
    ser = MagicMock(is_open=True)
    ser.read_all.return_value = b"\xff\xfe"
    manager = make_manager(ser)

    assert manager.fread() is None


def test_fread_returns_none_when_port_is_closed():
    ser = MagicMock(is_open=False)
    manager = make_manager(ser)

    assert manager.fread() is None
    ser.read_all.assert_not_called()


# ---------------------------------------------------------------------------
# Background reader and status callbacks
# ---------------------------------------------------------------------------


class ReadablePort:
    """Small stand-in for a pyserial port that yields queued lines."""

    def __init__(self, lines=None, error=None):
        self.lines = list(lines or [])
        self.error = error
        self.is_open = True
        self._closed = threading.Event()

    def readline(self):
        while self.is_open:
            if self.error is not None:
                raise self.error
            if self.lines:
                return self.lines.pop(0)
            self._closed.wait(0.005)
        return b""

    def close(self):
        self.is_open = False
        self._closed.set()


def wait_until(predicate, timeout=2.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return False


def test_reader_passes_each_line_to_callback(monkeypatch):
    port = ReadablePort([b"first\n", b"second\r\n"])
    lines = []
    received = threading.Event()

    def on_line(line):
        lines.append(line)
        if len(lines) == 2:
            received.set()

    manager = SerialManager(on_line=on_line)
    monkeypatch.setattr(serial_manager.serial, "Serial", MagicMock(return_value=port))

    assert manager.connect_serial("/dev/fake") is port
    assert received.wait(2.0)
    manager.disconnect()

    assert lines == ["first\n", "second\r\n"]


def test_reader_reports_disconnect_on_read_error(monkeypatch):
    port = ReadablePort(error=serial.SerialException("device unplugged"))
    statuses = []

    manager = SerialManager(on_line=lambda line: None, on_status=statuses.append)
    monkeypatch.setattr(serial_manager.serial, "Serial", MagicMock(return_value=port))

    assert manager.connect_serial("/dev/fake") is port
    assert wait_until(lambda: len(statuses) >= 2)

    assert statuses[0]["connected"] is True
    assert statuses[-1]["connected"] is False
    assert "device unplugged" in statuses[-1]["error"]
    assert manager.is_open() is False


def test_connect_ignores_duplicate_request_for_same_open_port(monkeypatch):
    port = ReadablePort()
    constructor = MagicMock(return_value=port)
    manager = SerialManager()
    monkeypatch.setattr(serial_manager.serial, "Serial", constructor)

    first = manager.connect_serial("/dev/fake", baudrate=115200)
    second = manager.connect_serial("/dev/fake", baudrate=115200)

    assert first is port
    assert second is port
    assert constructor.call_count == 1
    manager.disconnect()


def test_status_callback_receives_details(monkeypatch):
    port = ReadablePort()
    statuses = []

    manager = SerialManager(on_status=statuses.append)
    monkeypatch.setattr(serial_manager.serial, "Serial", MagicMock(return_value=port))

    manager.connect_serial("/dev/fake", baudrate=9600)
    manager.disconnect()

    assert statuses[0] == {
        "connected": True,
        "port": "/dev/fake",
        "baud_rate": 9600,
        "error": None,
    }
    assert statuses[-1]["connected"] is False
