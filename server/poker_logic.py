__author__ = "Tamir Raz"

import random
import threading
import time
from itertools import combinations

from shared.protocol import encode, encrypt, MSG_POKER_UPDATE, MSG_POKER_RESULT

ANTE = 50
_RANK_NAMES = {
    10:"Royal Flush", 9:"Straight Flush", 8:"Four of a Kind",
     7:"Full House",  6:"Flush",          5:"Straight",
     4:"Three of a Kind", 3:"Two Pair",   2:"One Pair", 1:"High Card",
}


class PokerTable:
    def __init__(self, db=None):
        self.db = db
        self.players:        dict = {}
        self.player_hands:   dict = {}
        self.community_cards: list = []
        self.pot:            int  = 0
        self.deck:           list = []
        self.player_order:   list = []
        self.current_turn_index: int  = 0
        self.folded_players: set  = set()
        self.game_stage:     str  = "WAITING"
        self.game_in_progress: bool = False
        self._lock = threading.Lock()

    def _create_deck(self):
        suits  = ["Hearts", "Diamonds", "Clubs", "Spades"]
        values = [("2",2),("3",3),("4",4),("5",5),("6",6),("7",7),
                  ("8",8),("9",9),("10",10),("J",11),("Q",12),("K",13),("A",14)]
        self.deck = [{"value_str": v, "value_int": n, "suit": s}
                     for v, n in values for s in suits]
        random.shuffle(self.deck)

    def add_player(self, sock, username: str):
        with self._lock:
            self.players[sock] = username
            if not self.game_in_progress and len(self.players) >= 2:
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
            self.folded_players.add(username)
            if len(self.players) < 2:
                self.game_in_progress = False

    def _start_soon(self):
        time.sleep(4)
        with self._lock:
            if len(self.players) >= 2:
                self._start_game()

    def _start_game(self):
        self.game_in_progress   = True
        self.current_turn_index = 0
        self.game_stage         = "PREFLOP"
        self.pot                = 0
        self._create_deck()
        self.player_hands.clear()
        self.community_cards.clear()
        self.folded_players.clear()
        self.player_order = list(self.players.values())
        for username in self.player_order:
            self.player_hands[username] = [self.deck.pop(), self.deck.pop()]
            if self.db:
                self.db.UpdateBalance(username, -ANTE)
            self.pot += ANTE
        self._broadcast_state_locked()

    def handle_action(self, username: str, action: str, amount: int = 0):
        with self._lock:
            if not self.game_in_progress:
                return
            if self.current_turn_index >= len(self.player_order):
                return
            if self.player_order[self.current_turn_index] != username:
                return
            if action == "FOLD":
                self.folded_players.add(username)
            elif action in ("CALL", "RAISE") and amount > 0:
                if self.db:
                    self.db.UpdateBalance(username, -amount)
                self.pot += amount
            self._next_turn()

    def _next_turn(self):
        active = [u for u in self.player_order if u not in self.folded_players]
        if len(active) == 1:
            self._end_game(winner=active[0])
            return
        self.current_turn_index += 1
        while (self.current_turn_index < len(self.player_order) and
               self.player_order[self.current_turn_index] in self.folded_players):
            self.current_turn_index += 1
        if self.current_turn_index >= len(self.player_order):
            self._advance_stage()
        else:
            self._broadcast_state_locked()

    def _advance_stage(self):
        self.current_turn_index = 0
        while (self.current_turn_index < len(self.player_order) and
               self.player_order[self.current_turn_index] in self.folded_players):
            self.current_turn_index += 1
        if self.game_stage == "PREFLOP":
            self.game_stage = "FLOP"
            self.community_cards += [self.deck.pop(), self.deck.pop(), self.deck.pop()]
        elif self.game_stage == "FLOP":
            self.game_stage = "TURN"
            self.community_cards.append(self.deck.pop())
        elif self.game_stage == "TURN":
            self.game_stage = "RIVER"
            self.community_cards.append(self.deck.pop())
        elif self.game_stage == "RIVER":
            self._end_game()
            return
        self._broadcast_state_locked()

    @staticmethod
    def _eval5(hand: list) -> tuple[int, list]:
        vals  = sorted([c["value_int"] for c in hand], reverse=True)
        suits = [c["suit"] for c in hand]
        is_flush    = len(set(suits)) == 1
        is_straight = False
        if len(set(vals)) == 5:
            if all(vals[i]-vals[i+1]==1 for i in range(4)):
                is_straight = True
            elif vals == [14,5,4,3,2]:
                is_straight = True
                vals = [5,4,3,2,1]
        counts = {v: vals.count(v) for v in vals}
        groups = sorted([(c,v) for v,c in counts.items()], reverse=True)
        if is_straight and is_flush:
            return (10 if vals[0]==14 else 9, vals)
        if groups[0][0]==4:
            return (8, [groups[0][1], groups[1][1]])
        if groups[0][0]==3 and groups[1][0]==2:
            return (7, [groups[0][1], groups[1][1]])
        if is_flush:
            return (6, vals)
        if is_straight:
            return (5, vals)
        if groups[0][0]==3:
            return (4, [groups[0][1], groups[1][1], groups[2][1]])
        if groups[0][0]==2 and groups[1][0]==2:
            return (3, [groups[0][1], groups[1][1], groups[2][1]])
        if groups[0][0]==2:
            return (2, [groups[0][1], groups[1][1], groups[2][1], groups[3][1]])
        return (1, vals)

    def _best_hand(self, username: str) -> tuple[int, list, str]:
        all_cards = self.player_hands[username] + self.community_cards
        best_rank, best_tie, best_name = -1, [], "High Card"
        for combo in combinations(all_cards, 5):
            rank, tie = self._eval5(list(combo))
            if (rank, tie) > (best_rank, best_tie):
                best_rank, best_tie = rank, tie
                best_name = _RANK_NAMES.get(rank, "High Card")
        return best_rank, best_tie, best_name

    def _end_game(self, winner: str | None = None):
        if winner:
            reason = "Everyone else folded"
        else:
            active = [u for u in self.player_order if u not in self.folded_players]
            best_rank, best_tie, reason = -1, [], "High Card"
            winner = active[0] if active else (self.player_order[0] if self.player_order else "")
            for username in active:
                rank, tie, name = self._best_hand(username)
                if (rank, tie) > (best_rank, best_tie):
                    best_rank, best_tie, reason = rank, tie, name
                    winner = username
        if self.db and winner:
            self.db.UpdateBalance(winner, self.pot)
        self._broadcast_locked({
            "cmd": MSG_POKER_RESULT, "winner": winner, "reason": reason,
            "pot": self.pot, "all_hands": self.player_hands,
            "community": self.community_cards,
        })
        self.game_in_progress = False
        threading.Thread(target=self._restart_later, daemon=True).start()

    def _restart_later(self):
        time.sleep(8)
        with self._lock:
            if len(self.players) >= 2 and not self.game_in_progress:
                self._start_game()

    def _broadcast_state_locked(self):
        turn = (self.player_order[self.current_turn_index]
                if self.current_turn_index < len(self.player_order) else "")
        self._broadcast_locked({
            "cmd": MSG_POKER_UPDATE, "stage": self.game_stage,
            "community_cards": self.community_cards, "current_turn": turn,
            "folded": list(self.folded_players), "player_count": len(self.players),
            "pot": self.pot, "player_hands": self.player_hands,
        })

    def _broadcast_locked(self, msg: dict):
        data = encrypt(encode(msg)) + b"\n"
        for sock in list(self.players.keys()):
            try:
                sock.sendall(data)
            except Exception:
                pass