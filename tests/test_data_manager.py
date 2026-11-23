"""Tests for backend/app/services/data_manager.py."""

from datetime import UTC, datetime, timedelta, timezone

from app.services.data_manager import DataManager, make_serial_data_message


class FakeRecorder:
    def __init__(self, recording=True):
        self.recording = recording
        self.lines = []

    def is_recording(self):
        return self.recording

    def record_line(self, line):
        self.lines.append(line)


class FakeBroadcaster:
    def __init__(self):
        self.messages = []

    def broadcast(self, message):
        self.messages.append(message)


def test_make_serial_data_message():
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    message = make_serial_data_message(
        "2172.562 R29 0000052C 00 00 FF FF FF FF FF FF", timestamp
    )

    assert message == {
        "type": "serial_data",
        "timestamp": "2026-01-01T12:00:00Z",
        "data": "2172.562 R29 0000052C 00 00 FF FF FF FF FF FF",
    }


def test_make_serial_data_message_treats_naive_timestamp_as_utc():
    message = make_serial_data_message("hello", datetime(2026, 1, 1, 12, 0))

    assert message["timestamp"] == "2026-01-01T12:00:00Z"


def test_make_serial_data_message_converts_timestamp_to_utc():
    plus_two = timezone(timedelta(hours=2))

    message = make_serial_data_message(
        "hello", datetime(2026, 1, 1, 14, 0, tzinfo=plus_two)
    )

    assert message["timestamp"] == "2026-01-01T12:00:00Z"


def test_handle_line_preserves_content_and_removes_line_ending():
    manager = DataManager()
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    message = manager.handle_line("  hello\tworld  \r\n", timestamp)

    assert message["data"] == "  hello\tworld  "


def test_handle_line_generates_utc_timestamp_by_default():
    message = DataManager().handle_line("hello")

    assert message["timestamp"].endswith("Z")
    parsed = datetime.fromisoformat(message["timestamp"])
    assert parsed.tzinfo is not None


def test_handle_line_records_line_when_recording_is_active():
    recorder = FakeRecorder(recording=True)
    manager = DataManager(recording_manager=recorder)

    manager.handle_line("hello\r\n")

    assert recorder.lines == ["hello"]


def test_handle_line_does_not_record_when_recording_is_inactive():
    recorder = FakeRecorder(recording=False)
    manager = DataManager(recording_manager=recorder)

    manager.handle_line("hello\r\n")

    assert recorder.lines == []


def test_handle_line_broadcasts_the_returned_message():
    broadcaster = FakeBroadcaster()
    manager = DataManager(broadcast_manager=broadcaster)
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    message = manager.handle_line("hello", timestamp)

    assert broadcaster.messages == [message]
    assert broadcaster.messages[0] is message


def test_handle_line_works_without_managers():
    manager = DataManager()
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    message = manager.handle_line("hello", timestamp)

    assert message == {
        "type": "serial_data",
        "timestamp": "2026-01-01T12:00:00Z",
        "data": "hello",
    }


def test_handle_line_broadcasts_each_line_separately():
    broadcaster = FakeBroadcaster()
    manager = DataManager(broadcast_manager=broadcaster)

    manager.handle_line("one\n")
    manager.handle_line("two\n")

    assert [message["data"] for message in broadcaster.messages] == ["one", "two"]
