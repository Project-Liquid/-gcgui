"""Tests for backend/app/api/routes/serial.py."""

from app.api.routes import serial
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_list_ports_endpoint(monkeypatch):
    monkeypatch.setattr(
        serial.serial_manager, "port_list", lambda: ["/dev/ttyUSB0", "COM3"]
    )

    response = client.get("/api/serial/ports")

    assert response.status_code == 200
    assert response.json() == ["/dev/ttyUSB0", "COM3"]


def test_status_endpoint_reports_open(monkeypatch):
    monkeypatch.setattr(serial.serial_manager, "is_open", lambda: True)

    response = client.get("/api/serial/status")

    assert response.status_code == 200
    assert response.json() is True


def test_connect_endpoint(monkeypatch):
    calls = []

    def fake_connect(port, baudrate, timeout):
        calls.append((port, baudrate, timeout))
        return object()

    monkeypatch.setattr(serial.serial_manager, "connect_serial", fake_connect)

    response = client.post(
        "/api/serial/connect",
        json={"port": "/dev/ttyUSB0", "baudrate": 115200, "timeout": 0.5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "connected": True,
        "port": "/dev/ttyUSB0",
        "baudrate": 115200,
    }
    assert calls == [("/dev/ttyUSB0", 115200, 0.5)]


def test_connect_uses_defaults(monkeypatch):
    calls = []

    def fake_connect(port, baudrate, timeout):
        calls.append((port, baudrate, timeout))
        return object()

    monkeypatch.setattr(serial.serial_manager, "connect_serial", fake_connect)

    response = client.post("/api/serial/connect", json={"port": "COM1"})

    assert response.status_code == 200
    assert calls == [("COM1", 115200, 1.0)]


def test_connect_returns_503_on_failure(monkeypatch):
    monkeypatch.setattr(serial.serial_manager, "connect_serial", lambda *args: None)

    response = client.post("/api/serial/connect", json={"port": "/dev/nope"})

    assert response.status_code == 503
    assert response.json() == {"detail": "Failed to connect to /dev/nope"}


def test_connect_rejects_invalid_body(monkeypatch):
    def fail(*args):
        raise AssertionError("connect_serial should not be called")

    monkeypatch.setattr(serial.serial_manager, "connect_serial", fail)

    response = client.post(
        "/api/serial/connect",
        json={"port": "", "baudrate": 0, "timeout": -1},
    )

    assert response.status_code == 422


def test_disconnect_endpoint(monkeypatch):
    calls = []
    monkeypatch.setattr(serial.serial_manager, "disconnect", lambda: calls.append(True))
    monkeypatch.setattr(serial.serial_manager, "is_open", lambda: False)

    response = client.post("/api/serial/disconnect")

    assert response.status_code == 200
    assert response.json() is False
    assert calls == [True]


def test_send_endpoint(monkeypatch):
    calls = []

    def fake_send(data):
        calls.append(data)
        return len(data)

    monkeypatch.setattr(serial.serial_manager, "send", fake_send)

    response = client.post("/api/serial/send", json={"data": "hello"})

    assert response.status_code == 200
    assert response.json() == 5
    assert calls == ["hello"]


def test_send_returns_409_when_not_connected(monkeypatch):
    monkeypatch.setattr(serial.serial_manager, "send", lambda data: None)

    response = client.post("/api/serial/send", json={"data": "hello"})

    assert response.status_code == 409
    assert response.json() == {"detail": "No serial port is connected"}


def test_send_rejects_empty_data(monkeypatch):
    def fail(*args):
        raise AssertionError("send should not be called")

    monkeypatch.setattr(serial.serial_manager, "send", fail)

    response = client.post("/api/serial/send", json={"data": ""})

    assert response.status_code == 422


def test_send_rejects_non_ascii_data(monkeypatch):
    def fail(*args):
        raise AssertionError("send should not be called")

    monkeypatch.setattr(serial.serial_manager, "send", fail)

    response = client.post("/api/serial/send", json={"data": "café"})

    assert response.status_code == 422


def test_send_raw_endpoint(monkeypatch):
    calls = []

    def fake_send_raw(data):
        calls.append(data)
        return len(data)

    monkeypatch.setattr(serial.serial_manager, "send_raw", fake_send_raw)

    response = client.post(
        "/api/serial/send_raw",
        content=b"\x00\x01\x02",
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 200
    assert response.json() == 3
    assert calls == [b"\x00\x01\x02"]


def test_send_raw_returns_409_when_not_connected(monkeypatch):
    monkeypatch.setattr(serial.serial_manager, "send_raw", lambda data: None)

    response = client.post(
        "/api/serial/send_raw",
        content=b"\x00",
        headers={"content-type": "application/octet-stream"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "No serial port is connected"}
