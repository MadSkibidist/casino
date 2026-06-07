import socket
from shared.protocol import encode, decode


class Network:
    def __init__(self):
        self._sock   = None
        self._buffer = b""

    def connect(self, host: str = "localhost", port: int = 5555):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5)
        self._sock.connect((host, port))
        self._sock.settimeout(None)  # back to blocking after connect

    def send(self, msg: dict):
        if self._sock:
            self._sock.sendall(encode(msg))

    def recv(self) -> dict | None:
        while b"\n" not in self._buffer:
            try:
                chunk = self._sock.recv(8192)
                if not chunk:
                    return None
                self._buffer += chunk
            except Exception:
                return None
        line, self._buffer = self._buffer.split(b"\n", 1)
        return decode(line)

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass