import socket
from shared.protocol import encode, decode, encrypt, decrypt


class Network:
    def __init__(self):
        self._sock   = None
        self._buffer = b""

    def connect(self, host: str = "localhost", port: int = 5555):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5)
        self._sock.connect((host, port))
        self._sock.settimeout(None)

    def send(self, msg: dict):
        if self._sock:
            self._sock.sendall(encrypt(encode(msg)) + b"\n")

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
        if not line:
            return None
        try:
            return decode(decrypt(line))
        except Exception as e:
            print(f"[NETWORK] decrypt error: {e}")
            return None  # דלג על הודעה פגומה ותמשיך

    def close(self):
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass