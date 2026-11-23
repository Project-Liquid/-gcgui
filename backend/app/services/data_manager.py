"""Route incoming serial lines to recording and browser clients."""

from datetime import UTC, datetime


def make_serial_data_message(
    line: str, timestamp: datetime | None = None
) -> dict[str, str]:
    """Build the stable ``serial_data`` message sent to browser clients."""
    if timestamp is None:
        timestamp = datetime.now(UTC)
    elif timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    else:
        timestamp = timestamp.astimezone(UTC)

    return {
        "type": "serial_data",
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "data": line,
    }


class DataManager:
    """Single distribution point for incoming serial lines.

    The optional managers are duck-typed. A recording manager must provide
    ``is_recording() -> bool`` and ``record_line(line)``. A broadcast manager
    must provide ``broadcast(message)``.

    The serial manager should hand every received line to ``handle_line``.
    That method preserves the line, sends it to the recording manager when a
    recording is active, and sends the formatted message to the broadcast
    manager for connected browser clients.
    """

    def __init__(self, recording_manager=None, broadcast_manager=None):
        self.recording_manager = recording_manager
        self.broadcast_manager = broadcast_manager

    def handle_line(
        self, line: str, timestamp: datetime | None = None
    ) -> dict[str, str]:
        """Process one incoming serial line and return its broadcast message.

        A trailing line ending is removed, matching the original Electron
        reader. The rest of the line is preserved exactly as received.
        """
        raw_line = line.rstrip("\r\n")
        message = make_serial_data_message(raw_line, timestamp)

        if self.recording_manager is not None and self.recording_manager.is_recording():
            self.recording_manager.record_line(raw_line)

        if self.broadcast_manager is not None:
            self.broadcast_manager.broadcast(message)

        return message
