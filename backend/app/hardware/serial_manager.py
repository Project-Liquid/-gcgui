# import string

import serial
import serial.tools.list_ports


class SerialManager:
    def __init__(self):
        self.ser = serial.Serial()

    @staticmethod
    def list_ports():
        """
        list all the ports available
        """
        return serial.tools.list_ports.comports()

    def port_list(self) -> list[str]:
        """
        give a device's list of ports as strings
        """
        ports = serial.tools.list_ports.comports()
        ans = []
        for port in ports:
            ans.append(port.device)
        return ans

    def connect_serial(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        """
        performs an attempt to connect to serial
        """
        # close any existing connection so the same port is not opened twice
        self.disconnect()
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
                # print(f"Connected to {ser.port} at {ser.baudrate} baud.")
                self.ser = ser
                return ser
            ser.close()
        except (serial.SerialException, ValueError) as e:
            print(f"Failed to connect to {port}: {e}")
            return None

    def is_open(self) -> bool:
        "returns if serial port is open"
        return self.ser.is_open

    def disconnect(self) -> None:
        "disconnects if the serial port is open"
        if self.is_open():
            self.ser.close()

    def send(self, data: str) -> int | None:
        "send a string of data as ascii"
        if self.is_open():
            return self.ser.write(data.encode("ascii"))

    def send_raw(self, data: bytes) -> int | None:
        "send the raw-ass data"
        if self.is_open():
            return self.ser.write(data)

    def read(self) -> bytes | None:
        "read from serial lol xd. returns the raw bytes or nothing"
        if self.is_open():
            return self.ser.read_all()

    def fread(self) -> str | None:
        "perform a formatted read. returns the string or nothing"
        if self.is_open():
            try:
                return self.ser.read_all().decode("ascii")
            except UnicodeDecodeError:
                return None
