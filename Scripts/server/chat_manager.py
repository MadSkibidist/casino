import threading


class ChatManager:
    MAX_HISTORY = 30

    def __init__(self):
        self._history: list[dict] = []
        self._lock = threading.Lock()

    def add_message(self, username: str, text: str):
        with self._lock:
            self._history.append({"username": username, "text": text})
            if len(self._history) > self.MAX_HISTORY:
                self._history.pop(0)

    def get_history(self) -> list[dict]:
        with self._lock:
            return list(self._history)