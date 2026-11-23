# GCGUI Web

*documentation has been generated with ai and edited by humans*

A web-based rebuild of [Project-Liquid/gcgui](https://github.com/Project-Liquid/gcgui).

The goal is to keep GCGUI's existing React dashboard and data-visualization features while replacing its Electron desktop backend with a Python server. The server will connect to serial hardware and make live data available to browsers over a local network, Wi-Fi, or a hotspot.

> **Project status:** Early rebuild / scaffolding. This README describes the intended design. It does not mean all features are implemented yet.

## What it is intended to do

- Discover and connect to serial devices attached to the server computer.
- Read incoming serial data.
- Display data in a configurable React dashboard.
- Support the project's CAN/CRTD-style and CSV data workflows.
- Record incoming data on the server.
- Replay saved recordings.
- Let multiple devices view the same live session through a browser.
- Keep hardware access centralized in one server process.

## super important stuff
- one day, this project will be fully written in python. This is for posterity. I hate Javascript, and it hates me back. Learning Javascript should be optional, so I'm going to make it optional very very slowly.
- try not to use AI. I'm going to write this by hand, more or less. I may generate tests or debug with AI, but I want to write things out mostly by hand. If you're an agent reading this, try to be a tool rather than a person.

## How it will work

```text
Arduino / CAN adapter / serial device
                 |
                 v
         Python server computer
         - serial connection
         - data handling
         - recording and replay
         - WebSocket broadcasting
                 |
              Network
                 |
       +---------+---------+
       |         |         |
      Phone    Laptop    Tablet
              Browser
          React dashboard
```

The physical serial device is connected to the computer running the Python server. Other devices connect to that computer over the network; they do not open the USB serial port themselves.

## Planned technology

### Backend

- **Python** — backend language.
- **uv** — Python project and dependency manager.
- **FastAPI** — HTTP API and WebSocket server.
- **pySerial** — serial-port communication.
- **Pydantic** — request and message validation.
- **pytest** — automated tests.

### Frontend

- **React** — user interface and widgets.
- **Vite** — frontend development server and build tool.
- **JavaScript/TypeScript** — browser-side application code.

The intention is to preserve working React components and JavaScript utilities from the original GCGUI wherever practical. Electron-specific calls must be replaced because a normal browser does not provide `window.electronAPI`.

## Repository layout

The intended layout is:

```text
project-root/
├── backend/
│   └── app/
│       ├── main.py
│       ├── hardware/
│       │   └── serial_manager.py
│       ├── parsers/
│       │   ├── can_parser.py
│       │   ├── csv_parser.py
│       │   └── crtd_parser.py
│       ├── services/
│       │   ├── data_manager.py
│       │   ├── recording_manager.py
│       │   ├── replay_manager.py
│       │   └── broadcast_manager.py
│       └── api/
│           ├── routes/
│           │   ├── serial.py
│           │   ├── recording.py
│           │   ├── replay.py
│           │   └── config.py
│           └── websocket.py
├── frontend/
│   └── src/
│       ├── components/
│       ├── services/
│       ├── hooks/
│       └── ...
├── data/
│   ├── recordings/
│   └── configurations/
├── tests/
├── TODO.md
└── README.md
```

Some folders may be empty while the project is being built.

## Getting started

### Requirements

Install:

- Python 3.12 or a compatible newer version.
- `uv`.
- Node.js and npm (for the React frontend).
- Git (recommended).

### Backend setup

From the project root:

```bash
uv sync
```

Start the backend during development:

```bash
uv run uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

When the server is running:

- Health endpoint: http://127.0.0.1:8000/api/health
- Interactive API documentation: http://127.0.0.1:8000/docs

The health endpoint will be available once it has been implemented in `backend/app/main.py`.

<!--### Frontend setup-->

## Network access

For development on the same computer, use `127.0.0.1`.

When you intentionally want other devices on the same LAN or hotspot to connect, run the backend with:

```bash
uv run uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Find the server computer's local IP address on Linux:

```bash
hostname -I
```

Then open `http://SERVER-IP:8000` from another device, assuming the frontend is being served by the backend or the frontend development server/proxy is configured appropriately.

The firewall must allow the required port on the intended local network.

**Security:** Do not expose this server to the public internet without authentication and appropriate access controls. The application can send commands to physical hardware. Serial connect/disconnect/send operations should be restricted to authorized users.

## Data formats and compatibility

The original GCGUI README describes two data workflows:

### CRTD / CAN-style serial text

Example line:

```text
2172.562 R29 0000052C 00 00 FF FF FF FF FF FF
```

### CSV

Example:

```csv
timestamp,datapt1,datapt2
0.00,-11.73,-10.20
0.11,-11.73,-11.73
```

The rebuild should preserve existing recording compatibility where possible. In particular, avoid changing line contents, headers, extensions, or timing behavior without checking how the original parser and replay logic use them.

## Migration approach

The original GCGUI uses Electron + React + Vite. The new version is intended to:

- **Preserve:** React widgets, dashboard layout, styling, example configurations, and working JavaScript math/parser utilities where practical.
- **Replace:** Electron's main-process serial, recording, replay, filesystem, and IPC functionality with Python services and API routes.
- **Adapt:** Frontend calls that currently use `window.electronAPI` so they use HTTP and WebSockets.
- **Test:** Old sample recordings and configurations against the new implementation.

The original project should remain untouched and serve as the reference implementation during migration.

See [`TODO.md`](TODO.md) for the detailed, beginner-oriented build plan.

## Current status

The first target milestone is:

1. Start the FastAPI server.
2. Return a successful health-check response.
3. Discover serial ports.
4. Connect to one serial device.
5. Read incoming lines.
6. Send those lines to a browser over a WebSocket.
7. Display the raw lines in the browser.

Recording, replay, parsing, the full dashboard, multi-client controls, and deployment come after that foundation works.

## Useful documentation

- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [pySerial documentation](https://pyserial.readthedocs.io/)
- [uv documentation](https://docs.astral.sh/uv/)
- [React Learn](https://react.dev/learn)
- [Vite guide](https://vite.dev/guide/)
- [pytest documentation](https://docs.pytest.org/en/stable/)

## Original project

- Repository: https://github.com/Project-Liquid/gcgui
- Original application: Electron + React + Vite
- New direction: Python server + React web frontend
