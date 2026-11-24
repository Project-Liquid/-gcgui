"""Serial-port access for the GCGUI server.

The manager owns the only physical serial connection. When an ``on_line``
callback is supplied, a background thread reads newline-delimited data and
hands each line to that callback (normally the DataManager).
"""

import logging
import threading
from collections.abc import Callable

import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)

LineCallback = Callable[[str], None]
StatusCallback = Callable[[dict], None]


class SerialManager:
    def __init__(
        self,
        on_line: LineCallback | None = None,
        on_status: StatusCallback | None = None,
    ):
        self.ser = serial.Serial()
        self.on_line = on_line
        self.on_status = on_status
        self._lock = threading.RLock()
        self._reader_thread: threading.Thread | None = None
        self._reader_stop: threading.Event | None = None
        self._port: str | None = None
        self._baudrate: int = 115200
        self._last_error: str | None = None
        self._last_status: tuple | None = None

    @staticmethod
    def list_ports():
        """List all the ports available."""
        return serial.tools.list_ports.comports()

    def port_list(self) -> list[str]:
        """Give a device's list of ports as strings."""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    @property
    def port(self) -> str | None:
        return self._port

    @property
    def baudrate(self) -> int:
        return self._baudrate

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def status(self) -> dict:
        """Return the current connection state as a plain dictionary."""
        return {
            "connected": self.is_open(),
            "port": self._port,
            "baud_rate": self._baudrate,
            "error": self._last_error,
        }

    def connect_serial(
        self, port: str, baudrate: int = 9600, timeout: float = 1.0
    ):
        """Attempt to connect to a serial port."""
        with self._lock:
            # Ignore duplicate connect requests (React StrictMode, repeated
            # port selections) instead of reopening a port that is already up.
            if (
                self.is_open()
                and self._port == port
                and self._baudrate == baudrate
            ):
                return self.ser

        # Close any existing connection before opening a new one.
        self.disconnect()

        with self._lock:
            self._port = port
            self._baudrate = baudrate
            self._last_error = None

            try:
                ser = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=timeout,
                )
                if ser.is_open:
                    self.ser = ser
                    # Publish the connected state before the reader thread can
                    # fail and publish a disconnected state.
                    self._notify_status()
                    self._start_reader(ser)
                    return ser
                ser.close()
            except (serial.SerialException, ValueError) as error:
                self._last_error = str(error)
                logger.error("Failed to connect to %s: %s", port, error)
                self._notify_status()
                return None

        return None

    def is_open(self) -> bool:
        """Return whether the serial port is open."""
        return bool(self.ser.is_open)

    def disconnect(self) -> None:
        """Disconnect if the serial port is open."""
        with self._lock:
            was_open = self.is_open()
            self._stop_reader()
            if self.is_open():
                try:
                    self.ser.close()
                except (serial.SerialException, OSError) as error:
                    logger.error("Failed to close serial port: %s", error)
            if was_open:
                self._notify_status()

    def send(self, data: str) -> int | None:
        """Send a string of data as ASCII."""
        return self._write(data.encode("ascii"))

    def send_raw(self, data: bytes) -> int | None:
        """Send raw bytes."""
        return self._write(data)

    def read(self) -> bytes | None:
        """Read whatever bytes are available."""
        with self._lock:
            if self.is_open():
                try:
                    return self.ser.read_all()
                except (serial.SerialException, OSError) as error:
                    self._handle_io_error(error)
            return None

    def fread(self) -> str | None:
        """Perform a formatted read. Returns the string or nothing."""
        data = self.read()
        if data is None:
            return None
        try:
            return data.decode("ascii")
        except UnicodeDecodeError:
            return None

    def _write(self, data: bytes) -> int | None:
        with self._lock:
            if not self.is_open():
                return None
            try:
                return self.ser.write(data)
            except (serial.SerialException, OSError) as error:
                self._handle_io_error(error)
                return None

    def _handle_io_error(self, error: Exception) -> None:
        self._last_error = str(error)
        logger.error("Serial I/O error on %s: %s", self._port, error)
        try:
            self.ser.close()
        except (serial.SerialException, OSError):
            pass
        self._stop_reader()
        self._notify_status()

    def _start_reader(self, ser) -> None:
        if self.on_line is None:
            return

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._read_loop,
            args=(ser, stop_event),
            name="gcgui-serial-reader",
            daemon=True,
        )
        self._reader_stop = stop_event
        self._reader_thread = thread
        thread.start()

    def _stop_reader(self) -> None:
        thread = self._reader_thread
        if thread is None:
            return

        if self._reader_stop is not None:
            self._reader_stop.set()

        if thread is not threading.current_thread():
            thread.join(timeout=2.0)

        self._reader_thread = None
        self._reader_stop = None

    def _read_loop(self, ser, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            if self.ser is not ser:
                return

            try:
                raw = ser.readline()
            except (serial.SerialException, OSError) as error:
                self._reader_failed(ser, error)
                return

            if stop_event.is_set():
                return
            if not raw:
                continue

            line = raw.decode("utf-8", errors="replace")
            if not line or self.on_line is None:
                continue

            try:
                self.on_line(line)
            except Exception:
                logger.exception("Unhandled error while processing serial data")

    def _reader_failed(self, ser, error: Exception) -> None:
        if self.ser is not ser:
            return

        self._last_error = str(error)
        logger.error("Serial reader stopped: %s", error)
        try:
            ser.close()
        except (serial.SerialException, OSError):
            pass
        self._notify_status()

    def _notify_status(self) -> None:
        callback = self.on_status
        if callback is None:
            return

        status = self.status()
        signature = tuple(status.values())
        if signature == self._last_status:
            return

        self._last_status = signature
        try:
            callback(status)
        except Exception:
            logger.exception("Unhandled error while publishing serial status")
