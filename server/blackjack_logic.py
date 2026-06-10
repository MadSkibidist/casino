__author__ = "Tamir Raz"

import random
import threading
import time

from shared.protocol import encode, encrypt, MSG_BJ_UPDATE, MSG_BJ_RESULT

class BlackjackTable:
    def __init__(self, db=None):
        self.db = db
        self.players:      dict = {}
        self.player_hands: dict = {}
        self.player_bets:  dict = {}
        self.dealer_hand:  list = []
        self.deck:         list = []
        self.player_order: list = []
        self.current_turn_index: int  = 0
        self.game_in_progress:   bool = False
        self._lock = threading.Lock()

    def _create_deck(self):
        suits  = ["H", "D", "C", "S"]
        values = ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]
        self.deck = [{"value": v, "suit": s} for v in values for s in suits] * 2
        random.shuffle(self.deck)

    def _pop(self) -> dict:
        return self.deck.pop() if self.deck else {"value": "A", "suit": "H"}

    @staticmethod
    def score(hand: list) -> int:
        total = 0
        aces  = 0
        for card in hand:
            v = card["value"]
            if v in ("J", "Q", "K"):
                total += 10
            elif v == "A":
                aces  += 1
                total += 11
            else:
                total += int(v)
        while total > 21 and aces:
            total -= 10
            aces  -= 1
        return total

    def add_player(self, sock, username: str, bet: int = 100):
        with self._lock:
            self.players[sock]         = username
            self.player_bets[username] = max(10, min(bet, 5000))
            print(f"[BJ] {username} joined (bet={self.player_bets[username]})")
            if not self.game_in_progress:
                threading.Thread(target=self._start_soon, daemon=True).start()
            else:
                self._broadcast_state_locked()

    def remove_player(self, sock):
        with self._lock:
            username = self.players.pop(sock, None)
            if not username:
                return
            self.player_order = [u for u in self.player_order if u != username]
            self.player_hands.pop(username, None)
            self.player_bets.pop(username, None)
            if not self.players:
                self.game_in_progress = False

    def _start_soon(self):
        time.sleep(3)
        with self._lock:
            self._start_round()

    def _start_round(self):
        if not self.players:
            return
        self.game_in_progress   = True
        self.current_turn_index = 0
        self._create_deck()
        self.player_hands.clear()
        self.dealer_hand  = [self._pop(), self._pop()]
        self.player_order = list(self.players.values())
        for u in self.player_order:
            self.player_hands[u] = [self._pop(), self._pop()]
        self._broadcast_state_locked()

    def handle_action(self, username: str, action: str):
        with self._lock:
            if not self.game_in_progress:
                return
            if self.current_turn_index >= len(self.player_order):
                return
            if self.player_order[self.current_turn_index] != username:
                return
            if action == "HIT":
                self.player_hands[username].append(self._pop())
                if self.score(self.player_hands[username]) >= 21:
                    self._next_turn()
                else:
                    self._broadcast_state_locked()
            elif action == "STAND":
                self._next_turn()

    def _next_turn(self):
        self.current_turn_index += 1
        if self.current_turn_index >= len(self.player_order):
            threading.Thread(target=self._dealer_turn, daemon=True).start()
        else:
            self._broadcast_state_locked()

    def _dealer_turn(self):
        time.sleep(1)
        with self._lock:
            while self.score(self.dealer_hand) < 17:
                self.dealer_hand.append(self._pop())
            self._end_round()

    def _end_round(self):
        dealer_sc = self.score(self.dealer_hand)
        results   = {}
        for username in self.player_order:
            hand = self.player_hands.get(username)
            if not hand:
                continue
            user_sc = self.score(hand)
            bet     = self.player_bets.get(username, 100)
            if user_sc > 21:
                status, delta = "LOSE (Bust)",       -bet
            elif dealer_sc > 21:
                status, delta = "WIN (Dealer Bust)", +bet
            elif user_sc > dealer_sc:
                status, delta = "WIN",               +bet
            elif user_sc < dealer_sc:
                status, delta = "LOSE",              -bet
            else:
                status, delta = "PUSH (Tie)",         0
            entry = {"hand": hand, "score": user_sc, "status": status, "delta": delta}
            if self.db:
                entry["balance"] = self.db.UpdateBalance(username, delta)
            results[username] = entry
        self._broadcast_locked({
            "cmd": MSG_BJ_RESULT, "dealer_hand": self.dealer_hand,
            "dealer_score": dealer_sc, "results": results,
        })
        self.game_in_progress = False
        threading.Thread(target=self._delayed_restart, daemon=True).start()

    def _delayed_restart(self):
        time.sleep(6)
        with self._lock:
            if self.players and not self.game_in_progress:
                self._start_round()

    def _broadcast_state_locked(self):
        turn = (self.player_order[self.current_turn_index]
                if self.current_turn_index < len(self.player_order) else "")
        visible_dealer = [self.dealer_hand[0]] if self.dealer_hand else []
        self._broadcast_locked({
            "cmd": MSG_BJ_UPDATE, "player_hands": self.player_hands,
            "dealer_hand": visible_dealer, "current_turn": turn,
            "bets": self.player_bets,
        })

    def _broadcast_locked(self, msg: dict):
        data = encrypt(encode(msg)) + b"\n"
        for sock in list(self.players.keys()):
            try:
                sock.sendall(data)
            except Exception:
                pass