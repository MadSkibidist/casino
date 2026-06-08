import random
import threading
import time

from shared.protocol import encode, MSG_ROULETTE_TICK, MSG_ROULETTE_RESULT

RED_NUMBERS = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


class RouletteTable:
    ROUND_DURATION = 20

    def __init__(self, db=None):
        self.db = db
        self.players:     dict = {}
        self.bets:        dict = {}
        self.time_left:   int  = self.ROUND_DURATION
        self.is_spinning: bool = False
        self.winning_number: int | None = None
        self._lock = threading.Lock()
        threading.Thread(target=self._game_loop, daemon=True).start()

    def add_player(self, sock, username: str):
        with self._lock:
            self.players[sock] = username
            try:
                sock.sendall(encode({
                    "cmd": MSG_ROULETTE_TICK, "time_left": self.time_left,
                    "spinning": self.is_spinning, "winning": self.winning_number,
                }))
            except Exception:
                pass

    def remove_player(self, sock):
        with self._lock:
            username = self.players.pop(sock, None)
            if username:
                self.bets.pop(username, None)

    def place_bet(self, username: str, amount: int,
                  bet_type: str, bet_value=None) -> tuple[bool, str]:
        with self._lock:
            if self.is_spinning or self.time_left <= 0:
                return False, "Bets are closed!"
            if amount < 10:
                return False, "Minimum bet is 10 chips."
            self.bets[username] = {"amount": amount, "type": bet_type, "value": bet_value}
            return True, f"Bet of {amount} chips placed!"

    def _game_loop(self):
        while True:
            time.sleep(1)
            with self._lock:
                if not self.players:
                    self.time_left = self.ROUND_DURATION
                    continue
                if self.is_spinning:
                    continue
                if self.time_left > 0:
                    self.time_left -= 1
                    self._broadcast_locked({
                        "cmd": MSG_ROULETTE_TICK, "time_left": self.time_left,
                        "spinning": False, "winning": None,
                    })
                else:
                    self.is_spinning = True
                    threading.Thread(target=self._spin_wheel, daemon=True).start()

    def _spin_wheel(self):
        for _ in range(4):
            time.sleep(0.7)
            with self._lock:
                self._broadcast_locked({
                    "cmd": MSG_ROULETTE_TICK, "time_left": 0,
                    "spinning": True, "winning": None,
                })
        winning_number = random.randint(0, 36)
        if   winning_number == 0:                winning_color = "GREEN"
        elif winning_number in RED_NUMBERS:      winning_color = "RED"
        else:                                    winning_color = "BLACK"
        with self._lock:
            self.winning_number = winning_number
            results = {}
            for username, bet in self.bets.items():
                amount, b_type, b_val = bet["amount"], bet["type"], bet["value"]
                won, payout = False, 0
                if b_type == "COLOR" and str(b_val) == winning_color:
                    won, payout = True, amount * 2
                elif b_type == "NUMBER" and int(b_val) == winning_number:
                    won, payout = True, amount * 35
                elif b_type == "DOZEN":
                    d = int(b_val)
                    if ((d==1 and 1<=winning_number<=12) or
                        (d==2 and 13<=winning_number<=24) or
                        (d==3 and 25<=winning_number<=36)):
                        won, payout = True, amount * 3
                elif b_type == "HALF":
                    if ((b_val=="LOW"  and 1<=winning_number<=18) or
                        (b_val=="HIGH" and 19<=winning_number<=36)):
                        won, payout = True, amount * 2
                delta = (payout - amount) if won else -amount
                entry = {"won": won, "payout": payout, "delta": delta}
                if self.db:
                    entry["balance"] = self.db.UpdateBalance(username, delta)
                results[username] = entry
            self._broadcast_locked({
                "cmd": MSG_ROULETTE_RESULT, "number": winning_number,
                "color": winning_color, "player_results": results,
            })
            self.bets.clear()
            self.time_left      = self.ROUND_DURATION
            self.is_spinning    = False
            self.winning_number = None

    def _broadcast_locked(self, msg: dict):
        data = encode(msg)
        for sock in list(self.players.keys()):
            try:
                sock.sendall(data)
            except Exception:
                pass