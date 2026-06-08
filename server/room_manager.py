__author__ = "Tamir Raz"

import threading
import random


class RoomManager:
    MAX_PLAYERS = 20

    def __init__(self):
        self._players: dict = {}
        self._lock = threading.Lock()

    def add_player(self, sock, username: str,
                   char_id: int, balance: int = 5000) -> bool:
        with self._lock:
            if len(self._players) >= self.MAX_PLAYERS:
                return False
            self._players[sock] = {
                "username": username,
                "char_id":  char_id,
                "x":        random.randint(200, 600),
                "y":        random.randint(300, 450),
                "balance":  balance,
            }
            return True

    def remove_player(self, sock) -> str | None:
        with self._lock:
            data = self._players.pop(sock, None)
            return data["username"] if data else None

    def update_position(self, sock, x: int, y: int):
        with self._lock:
            if sock in self._players:
                self._players[sock]["x"] = x
                self._players[sock]["y"] = y

    def update_balance(self, username: str, balance: int):
        with self._lock:
            for data in self._players.values():
                if data["username"] == username:
                    data["balance"] = balance
                    break

    def update_char(self, sock, char_id: int):
        with self._lock:
            if sock in self._players:
                self._players[sock]["char_id"] = char_id

    def get_room_state(self) -> list:
        with self._lock:
            return list(self._players.values())

    def get_all_sockets(self) -> list:
        with self._lock:
            return list(self._players.keys())