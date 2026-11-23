# import string

import serial
import serial.tools.list_ports


class SerialManager:
    ser = serial.Serial()

    def list_ports():
        """
        list all the ports available
        """
        return serial.tools.list_ports

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
                return ser
        except serial.SerialException as e:
            print(f"Failed to connect to {port}: {e}")
            return e

    def is_open(self) -> bool:
        "returns if serial port is open"
        return self.ser.is_open

    def disconnect(self) -> int | None:
        "disconnects or returns status"
        if self.is_open():
            return self.ser.close()

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
        return self.ser.read_all()

    def fread(self) -> str | None:
        "perform a formatted read. returns the string or nothing"
        return self.ser.read_all().decode("ascii")
