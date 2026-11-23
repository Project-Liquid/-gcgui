"""Tests for backend/app/api/routes/serial.py."""

from app.api.routes import serial
from app.main import app
from fastapi.testclient import TestClient


def test_list_ports_endpoint(monkeypatch):
    monkeypatch.setattr(
        serial.serial_manager, "port_list", lambda: ["/dev/ttyUSB0", "COM3"]
    )

    client = TestClient(app)
    response = client.get("/api/serial/ports")

    assert response.status_code == 200
    assert response.json() == ["/dev/ttyUSB0", "COM3"]
