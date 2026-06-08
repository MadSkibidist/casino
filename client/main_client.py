__author__ = "Tamir Raz"

import pygame
import sys
import threading
import time

from client.characters      import CharacterDrawer
from client.chat_ui         import ChatInputBox, ChatBubble
from client.card_drawer     import CardDrawer
from client.roulette_window import RouletteWindow
from client.poker_window    import PokerWindow
from client.network         import Network
from shared.protocol import (MSG_BJ_UPDATE, MSG_BJ_RESULT,
                             MSG_ROULETTE_TICK, MSG_ROULETTE_RESULT,
                             MSG_POKER_UPDATE, MSG_POKER_RESULT)

W, H    = 900, 620
GOLD    = (212, 175,  55)
GREEN   = (10,   80,  40)
CRIMSON = (130,  15,  35)
WHITE   = (255, 255, 255)
DARK    = (22,   22,  34)


class CasinoClient:
    def __init__(self):

        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Casino Project")
        self.clock  = pygame.time.Clock()

        self.f_sm  = pygame.font.SysFont("Arial", 14)
        self.f_med = pygame.font.SysFont("Arial", 18)
        self.f_lg  = pygame.font.SysFont("Arial", 26, bold=True)
        self.f_hdr = pygame.font.SysFont("Arial", 20, bold=True)

        # State machine
        # CONNECTING → AUTH → LOBBY → BLACKJACK / ROULETTE / POKER / TICTACTOE
        self.state = "CONNECTING"

        # Connection state
        self.net            = None
        self.connect_error  = ""
        self.connect_done   = False

        # Game data (populated after auth)
        self.username = ""
        self.char_id  = 0
        self.balance  = 5000
        self.my_x     = 400
        self.my_y     = 380

        self._lock         = threading.Lock()
        self.other_players = []
        self.chat_history  = []
        self.chat_bubbles  = {}

        # Blackjack
        self.bj_player_hands = {}
        self.bj_dealer_hand = []
        self.bj_current_turn = ""
        self.bj_game_result = None
        self.bj_bets = {}
        self.bj_bet_input = 100
        self.bj_final_hands = {}  # keeps hands visible after round ends
        self.bj_final_dealer_hand = []  # keeps full dealer hand visible after round ends

        # Roulette
        self.roulette_win         = RouletteWindow(W, H)
        self.roulette_pending_bet = None

        # Poker
        self.poker_win = PokerWindow(W, H)

        # TicTacToe
        self.ttt_game_id  = ""
        self.ttt_role     = ""
        self.ttt_opponent = ""
        self.ttt_board    = [""] * 9
        self.ttt_turn     = ""
        self.ttt_winner   = None
        self.ttt_grid     = [
            pygame.Rect(250 + (i % 3) * 100, 160 + (i // 3) * 100, 95, 95)
            for i in range(9)
        ]

        self.lobby_tables = {
            "BLACKJACK": pygame.Rect(55,  200, 170, 90),
            "ROULETTE":  pygame.Rect(275, 200, 170, 90),
            "POKER":     pygame.Rect(495, 200, 170, 90),
        }

        self.chat_box  = ChatInputBox(18, H - 52, W - 230, 40, "ENTER to chat...")
        self.error_msg = ""
        self.error_tmr = 0

        # Auth window (created lazily after connection)
        self._auth_win = None

        # Dots animation for connecting screen
        self._dot_frame = 0

    # Connect in background
    def _connect_thread(self):
        """Runs in daemon thread Connects to server without blocking the UI."""
        try:
            net = Network()
            net.connect("localhost", 5555)
            with self._lock:
                self.net = net
                self.connect_done = True
                self.connect_error = ""
        except Exception as e:
            with self._lock:
                self.connect_done = True
                self.connect_error = str(e)

    # Auth
    def _start_auth(self):
        """Called once the connection is established."""
        from client.auth_window import AuthWindow
        self._auth_win = AuthWindow(self.net)
        self.state = "AUTH"

    # Receive loop (background thread, started after auth)
    def _recv_loop(self):
        while True:
            msg = self.net.recv()
            if msg is None:
                break
            cmd = msg.get("cmd", "")
            with self._lock:
                if cmd == "ROOM_STATE":
                    self.other_players = [
                        p for p in msg.get("players", [])
                        if p["username"] != self.username
                    ]

                elif cmd == "CHAT":
                    sender = msg.get("username", "?")
                    text   = msg.get("text", "")
                    self.chat_history.append(f"{sender}: {text}")
                    if len(self.chat_history) > 40:
                        self.chat_history.pop(0)
                    self.chat_bubbles[sender] = ChatBubble(text)

                elif cmd == "CHAT_HISTORY":
                    for h in msg.get("history", []):
                        self.chat_history.append(
                            f"{h['username']}: {h['text']}")
                elif cmd == "CHAT_ACK":
                    self.chat_history.append(f"You: {msg.get('text', '')}")

                elif cmd in ("CHAT_ERROR", "BET_ACK"):
                    self.error_msg = msg.get("msg", "")
                    self.error_tmr = 180

                elif cmd == "RECEIVE_MSG":
                    self.chat_history.append(
                        f"[PM] {msg.get('sender','?')}: {msg.get('text','')}")
                elif cmd == "JOIN_SUCCESS":
                    self.state = msg.get("table", self.state)

                elif cmd == "BACK_TO_LOBBY":
                    self.state   = "LOBBY"
                    self.balance = msg.get("balance", self.balance)
                    if msg.get("msg"):
                        self.error_msg = msg.get("msg")
                        self.error_tmr = 300
                    self.bj_game_result       = None
                    self.roulette_pending_bet = None
                    self.poker_win.winner_timer = 0
                    self.poker_win.all_hands    = {}


                elif cmd == MSG_BJ_UPDATE:

                    self.bj_player_hands = msg.get("player_hands", {})

                    self.bj_dealer_hand = msg.get("dealer_hand", [])

                    self.bj_current_turn = msg.get("current_turn", "")

                    self.bj_bets = msg.get("bets", {})

                    self.bj_game_result = None

                    self.bj_final_hands = {}

                    self.bj_final_dealer_hand = []

                elif cmd == MSG_BJ_RESULT:
                    self.bj_dealer_hand = msg.get("dealer_hand", [])
                    self.bj_final_dealer_hand = msg.get("dealer_hand", [])
                    self.bj_game_result = msg.get("results", {})

                    for user, res in self.bj_game_result.items():
                        self.bj_final_hands[user] = res.get("hand", [])
                    my_res = self.bj_game_result.get(self.username, {})
                    if "balance" in my_res:
                        self.balance = my_res["balance"]

                elif cmd == MSG_ROULETTE_TICK:
                    self.roulette_win.time_left = msg.get("time_left", 20)
                    if msg.get("spinning"):
                        if not self.roulette_win.spinning:
                            self.roulette_win.start_spinning()
                    else:
                        self.roulette_win.spinning   = False
                        self.roulette_win.spin_speed = 0.0

                elif cmd == MSG_ROULETTE_RESULT:
                    self.roulette_win.stop_spinning(
                        msg.get("number", 0), msg.get("color", "BLACK"))
                    my_r = msg.get("player_results", {}).get(self.username)
                    if my_r:
                        self.balance = my_r.get("balance", self.balance)
                        won = my_r.get("won", False)
                        pay = my_r.get("payout", 0)
                        self.roulette_win.show_result(
                            f"WIN  +{pay}" if won else "LOSE", won)
                    self.roulette_pending_bet = None

                elif cmd == MSG_POKER_UPDATE:
                    self.poker_win.update_state(msg, self.username)

                elif cmd == MSG_POKER_RESULT:
                    self.poker_win.show_result(msg, self.username)
                    if msg.get("winner") == self.username:
                        self.balance += msg.get("pot", 0)

                elif cmd == "GAME_INVITE":
                    self.net.send({"cmd": "GAME_ACCEPT",
                                   "host": msg.get("from", "")})

                elif cmd == "START_GAME":
                    self.ttt_game_id  = msg.get("game_id",  "")
                    self.ttt_role     = msg.get("role",     "X")
                    self.ttt_opponent = msg.get("opponent", "")
                    self.ttt_board    = [""] * 9
                    self.ttt_winner   = None
                    self.ttt_turn     = msg.get("turn", "")
                    self.state        = "TICTACTOE"

                elif cmd == "GAME_UPDATE":
                    self.ttt_board  = msg.get("board",  self.ttt_board)
                    self.ttt_turn   = msg.get("turn",   self.ttt_turn)
                    self.ttt_winner = msg.get("winner", None)

    # Lobby movement
    def _update_movement(self):
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]  or keys[pygame.K_a]: dx -= 4
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]: dx += 4
        if keys[pygame.K_UP]    or keys[pygame.K_w]: dy -= 4
        if keys[pygame.K_DOWN]  or keys[pygame.K_s]: dy += 4
        if dx or dy:
            self.my_x = max(40, min(self.my_x + dx, W - 40))
            self.my_y = max(80, min(self.my_y + dy, H - 90))
            self.net.send({"cmd": "MOVE", "x": self.my_x, "y": self.my_y})
            pr = pygame.Rect(self.my_x - 18, self.my_y - 18, 36, 36)
            for tname, tr in self.lobby_tables.items():
                if pr.colliderect(tr):
                    self.net.send({"cmd": "JOIN_TABLE",
                                   "table_type": tname,
                                   "bet": self.bj_bet_input})
                    self.state = tname
                    break

    # Draw: Connecting
    def _draw_connecting(self):
        self.screen.fill(DARK)
        self._dot_frame += 1
        dots = "." * ((self._dot_frame // 20) % 4)

        title = self.f_lg.render("Casino Project", True, GOLD)
        self.screen.blit(title, (W // 2 - title.get_width() // 2, H // 2 - 60))

        if self.connect_error:
            msg  = self.f_med.render(
                f"Cannot connect: {self.connect_error}", True, (255, 80, 80))
            hint = self.f_sm.render(
                "Make sure run_server.py is running, then restart the client.",
                True, (180, 180, 180))
            self.screen.blit(msg,  (W // 2 - msg.get_width()  // 2, H // 2))
            self.screen.blit(hint, (W // 2 - hint.get_width() // 2, H // 2 + 40))
        else:
            ts = self.f_med.render(
                f"Connecting to server{dots}", True, (180, 180, 180))
            self.screen.blit(ts, (W // 2 - ts.get_width() // 2, H // 2))

    # Draw: Lobby
    def _draw_lobby(self):
        self.screen.fill(GREEN)
        pygame.draw.rect(self.screen, (8, 50, 25), (0, 0, W, 48))
        hdr = self.f_hdr.render(
            f"{self.username}  |  {self.balance} chips  |  "
            f"WASD / Arrows to walk   walk into a table to play",
            True, GOLD)
        self.screen.blit(hdr, (14, 13))

        for name, rect in self.lobby_tables.items():
            pygame.draw.rect(self.screen, (18, 55, 28), rect, border_radius=14)
            pygame.draw.rect(self.screen, GOLD,          rect, 3, border_radius=14)
            ts = self.f_hdr.render(name, True, GOLD)
            self.screen.blit(ts, (rect.x + (rect.w - ts.get_width())  // 2,
                                  rect.y + (rect.h - ts.get_height()) // 2))

        with self._lock:
            others  = list(self.other_players)
            bubbles = dict(self.chat_bubbles)

        for p in others:
            px, py = p["x"], p["y"]
            CharacterDrawer.draw_character(self.screen, p["char_id"], px, py)
            nt = self.f_sm.render(p["username"], True, (200, 200, 200))
            self.screen.blit(nt, (px - nt.get_width() // 2, py + 52))
            b = bubbles.get(p["username"])
            if b:
                b.update()
                b.draw(self.screen, px, py)

        CharacterDrawer.draw_character(self.screen, self.char_id,
                                       self.my_x, self.my_y)
        my_lbl = self.f_sm.render(f"{self.username} (you)", True, GOLD)
        self.screen.blit(my_lbl, (self.my_x - my_lbl.get_width() // 2,
                                  self.my_y + 52))

        cp = pygame.Rect(W - 222, 54, 216, H - 110)
        pygame.draw.rect(self.screen, (10, 40, 20), cp, border_radius=8)
        pygame.draw.rect(self.screen, GOLD, cp, 1, border_radius=8)
        self.screen.blit(self.f_sm.render("Chat", True, GOLD),
                         (cp.x + 8, cp.y + 6))

        with self._lock:
            hist = list(self.chat_history[-22:])
        for i, line in enumerate(hist):
            ts = self.f_sm.render(line[:30], True, (200, 230, 200))
            self.screen.blit(ts, (cp.x + 6, cp.y + 26 + i * 20))

        if self.error_tmr > 0:
            et = self.f_sm.render(self.error_msg, True, (255, 80, 80))
            self.screen.blit(et, (18, H - 58))
            self.error_tmr -= 1

        self.chat_box.draw(self.screen)

    # Draw: Blackjack
    def _draw_blackjack(self):
        self.screen.fill(CRIMSON)
        bet_now = self.bj_bets.get(self.username, self.bj_bet_input)
        hdr = self.f_hdr.render(
            f"Blackjack  |  {self.username}  |  {self.balance} chips  |  "
            f"Bet: {bet_now}  |  <- -> adjust  |  ESC leave",
            True, WHITE)
        self.screen.blit(hdr, (14, 10))

        self.screen.blit(self.f_sm.render("Dealer:", True, (200, 200, 200)),
                         (60, 72))
        # Show full dealer hand when round is over, otherwise live hand
        dealer_display = (self.bj_final_dealer_hand
                          if self.bj_game_result
                          else self.bj_dealer_hand)
        for i, card in enumerate(dealer_display):
            CardDrawer.draw_card(self.screen, 60 + i * 80, 92,
                                 card["value"], card["suit"])
        if self.bj_game_result is None and len(self.bj_dealer_hand) == 1:
            CardDrawer.draw_card_back(self.screen, 140, 92)

        with self._lock:
            others = {u: h for u, h in self.bj_player_hands.items()
                      if u != self.username}
        ox = 60
        for user, hand in others.items():
            self.screen.blit(self.f_sm.render(f"{user}:", True, (200, 200, 200)),
                             (ox, 224))
            for i, card in enumerate(hand):
                CardDrawer.draw_card(self.screen, ox + i * 42, 242,
                                     card["value"], card["suit"], 38, 54)
            ox += 200

        if self.bj_game_result:
            my_hand = self.bj_final_hands.get(self.username,
                                              self.bj_player_hands.get(self.username, []))
        else:
            my_hand = self.bj_player_hands.get(self.username, [])

        self.screen.blit(self.f_hdr.render("Your hand:", True, GOLD), (60, 314))
        for i, card in enumerate(my_hand):
            CardDrawer.draw_card(self.screen, 60 + i * 80, 338,
                                 card["value"], card["suit"])

        if my_hand:
            from server.blackjack_logic import BlackjackTable
            sc  = BlackjackTable.score(my_hand)
            col = (255, 100, 100) if sc > 21 else GOLD
            self.screen.blit(
                self.f_med.render(f"Score: {sc}", True, col), (60, 452))

        if self.bj_game_result:
            my_r   = self.bj_game_result.get(self.username, {})
            status = my_r.get("status", "")
            col = ((0, 220, 100)  if "WIN"  in status else
                   (255, 80, 80) if "LOSE" in status else WHITE)
            rt = self.f_lg.render(f"Round over -- {status}", True, col)
            self.screen.blit(rt, (W // 2 - rt.get_width() // 2, 490))
        else:
            if self.bj_current_turn == self.username:
                ts = self.f_lg.render(
                    "YOUR TURN  --  H: Hit     S: Stand", True, (0, 255, 120))
            elif self.bj_current_turn:
                ts = self.f_med.render(
                    f"Waiting for {self.bj_current_turn}...",
                    True, (200, 200, 200))
            else:
                ts = self.f_med.render(
                    "Waiting for round to start...", True, GOLD)
            self.screen.blit(ts, (W // 2 - ts.get_width() // 2, 490))

    # Draw: Roulette
    def _draw_roulette(self):
        self.roulette_win.update()
        self.roulette_win.draw(self.screen, self.balance)
        if self.roulette_pending_bet:
            lbl = self.f_sm.render(
                f"Selected: {self.roulette_pending_bet[0]}", True, GOLD)
            self.screen.blit(lbl, (14, H - 22))
        else:
            self.screen.blit(
                self.f_sm.render("ESC -- leave table", True, (90, 130, 90)),
                (14, H - 22))

    # Draw: Poker
    def _draw_poker(self):
        self.poker_win.update()
        self.poker_win.draw(self.screen, self.username, self.balance)
        self.screen.blit(
            self.f_sm.render("ESC -- leave table", True, (90, 130, 90)),
            (14, H - 22))

    # Main loop
    def run(self):
        # Kick off connection immediately in the background
        threading.Thread(target=self._connect_thread, daemon=True).start()

        while True:
            self.clock.tick(60)

            # Check connection result
            with self._lock:
                done  = self.connect_done
                error = self.connect_error

            if done and self.state == "CONNECTING":
                if error:
                    pass   # stay on CONNECTING screen, show error
                else:
                    self._start_auth()   # switches state to AUTH

            # Check auth completion
            if self.state == "AUTH" and self._auth_win is not None:
                result = self._auth_win.get_result()
                if result:
                    self.username, self.char_id, self.balance = result
                    self.state = "LOBBY"
                    threading.Thread(
                        target=self._recv_loop, daemon=True).start()

            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.net:
                        self.net.close()
                    pygame.quit()
                    sys.exit()

                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    if self.state in ("BLACKJACK", "ROULETTE", "POKER"):
                        self.net.send({"cmd": "LEAVE_TABLE"})
                    elif self.state == "TICTACTOE":
                        self.state = "LOBBY"

                if self.state == "AUTH" and self._auth_win:
                    self._auth_win.handle_event(event)

                if self.state == "LOBBY":

                    chat_out = self.chat_box.handle_event(event)

                    if chat_out:
                        self.net.send({"cmd": "CHAT", "text": chat_out})

                    # Click anywhere outside chat box to deactivate it

                    if event.type == pygame.MOUSEBUTTONDOWN:

                        if not self.chat_box.rect.collidepoint(event.pos):
                            self.chat_box.active = False

                elif self.state == "BLACKJACK":
                    if event.type == pygame.KEYDOWN:
                        if (event.key == pygame.K_h and
                                self.bj_current_turn == self.username and
                                not self.bj_game_result):
                            self.net.send({"cmd": "GAME_ACTION", "action": "HIT"})
                        elif (event.key == pygame.K_s and
                              self.bj_current_turn == self.username and
                              not self.bj_game_result):
                            self.net.send({"cmd": "GAME_ACTION", "action": "STAND"})
                        elif event.key == pygame.K_LEFT:
                            self.bj_bet_input = max(10, self.bj_bet_input - 50)
                        elif event.key == pygame.K_RIGHT:
                            self.bj_bet_input = min(5000, self.bj_bet_input + 50)

                elif self.state == "ROULETTE":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        result = self.roulette_win.handle_click(event.pos)
                        if result == "CONFIRM":
                            if self.roulette_pending_bet:
                                _, btype, bval = self.roulette_pending_bet
                                self.net.send({
                                    "cmd":       "PLACE_BET",
                                    "amount":    self.roulette_win.bet_amount,
                                    "bet_type":  btype,
                                    "bet_value": bval,
                                })
                        elif result is not None:
                            self.roulette_pending_bet = result

                elif self.state == "POKER":
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        action = self.poker_win.handle_click(
                            event.pos, self.username)
                        if action in ("CHECK", "CALL", "RAISE", "FOLD"):
                            amt = (self.poker_win.raise_amount
                                   if action in ("CALL", "RAISE") else 0)
                            self.net.send({"cmd":    "POKER_ACTION",
                                           "action": action,
                                           "amount": amt})



            # Per-frame updates
            if self.state == "LOBBY":
                if not self.chat_box.active:
                    self._update_movement()
                with self._lock:
                    dead = [u for u, b in self.chat_bubbles.items()
                            if not b.is_alive()]
                for u in dead:
                    with self._lock:
                        self.chat_bubbles.pop(u, None)

            # Render
            if   self.state == "CONNECTING":
                self._draw_connecting()
            elif self.state == "AUTH" and self._auth_win:
                self._auth_win.draw(self.screen)
            elif self.state == "LOBBY":
                self._draw_lobby()
            elif self.state == "BLACKJACK":
                self._draw_blackjack()
            elif self.state == "ROULETTE":
                self._draw_roulette()
            elif self.state == "POKER":
                self._draw_poker()
            elif self.state == "TICTACTOE":
                self._draw_tictactoe()

            pygame.display.flip()


if __name__ == "__main__":
    CasinoClient().run()