__author__ = "Tamir Raz"

import threading
import pygame

from client.network import Network
from shared.protocol import MSG_LOGIN, MSG_SIGNUP, MSG_AUTH_OK

DARK  = (22,  22,  34)
PANEL = (35,  35,  52)
GOLD  = (212, 175,  55)
WHITE = (255, 255, 255)
GRAY  = (160, 160, 180)
RED   = (220,  60,  60)
GREEN = (46,  139,  87)
BLUE  = (70,  130, 180)


class AuthWindow:


    def __init__(self, net: Network):
        self.net = net

        self.f_sm    = pygame.font.SysFont("Arial", 14)
        self.f_med   = pygame.font.SysFont("Arial", 18)
        self.f_lg    = pygame.font.SysFont("Arial", 24, bold=True)
        self.f_title = pygame.font.SysFont("Arial", 30, bold=True)

        self.view        = "INPUT"
        self.purpose     = "LOG"
        self.status      = "Welcome!  Enter your details below."
        self.status_ok   = True
        self.my_username = ""
        self._balance    = 5000

        self.username = ""
        self.password = ""
        self.email    = ""
        self.otp      = ""
        self.active   = "USER"

        self._result         = None
        self._char_id        = 0
        self._busy           = False
        self._in_char_select = False

        self._build_rects(900, 620)

    def _build_rects(self, W, H):
        cx = W // 2
        self.user_rect     = pygame.Rect(cx - 130, 140, 260, 38)
        self.pass_rect     = pygame.Rect(cx - 130, 215, 260, 38)
        self.email_rect    = pygame.Rect(cx - 130, 290, 260, 38)
        self.login_btn     = pygame.Rect(cx - 130, 355, 120, 44)
        self.signup_btn    = pygame.Rect(cx +  10, 355, 120, 44)
        self.forgot_btn    = pygame.Rect(cx - 130, 415, 260, 34)
        self.otp_rect      = pygame.Rect(cx -  75, 230, 150, 52)
        self.verify_btn    = pygame.Rect(cx -  75, 305, 150, 44)
        self.new_pass_rect = pygame.Rect(cx - 130, 240, 260, 38)
        self.reset_btn     = pygame.Rect(cx -  75, 308, 150, 44)

    def get_result(self):

        return self._result

    def handle_event(self, event):
        if self._result:
            return
        if self._in_char_select:
            self._handle_char_event(event)
            return
        if self._busy:
            return
        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_click(event.pos)
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event)

    def _handle_char_event(self, event):
        if event.type == pygame.KEYDOWN:
            if   event.key == pygame.K_LEFT:
                self._char_id = (self._char_id - 1) % 10
            elif event.key == pygame.K_RIGHT:
                self._char_id = (self._char_id + 1) % 10
            elif event.key == pygame.K_RETURN:
                self.net.send({"cmd": "SET_CHAR", "char_id": self._char_id})
                self._result = (self.my_username, self._char_id, self._balance)

    def _handle_click(self, pos):
        if self.view == "INPUT":
            if   self.user_rect.collidepoint(pos):   self.active = "USER"
            elif self.pass_rect.collidepoint(pos):   self.active = "PASS"
            elif self.email_rect.collidepoint(pos):  self.active = "EMAIL"
            elif self.login_btn.collidepoint(pos):
                threading.Thread(target=self._send_auth,
                                 args=(MSG_LOGIN,), daemon=True).start()
            elif self.signup_btn.collidepoint(pos):
                threading.Thread(target=self._send_auth,
                                 args=(MSG_SIGNUP,), daemon=True).start()
            elif self.forgot_btn.collidepoint(pos):
                threading.Thread(target=self._send_forgot, daemon=True).start()
        elif self.view == "OTP":
            if   self.otp_rect.collidepoint(pos):    self.active = "OTP"
            elif self.verify_btn.collidepoint(pos):
                threading.Thread(target=self._send_otp, daemon=True).start()
        elif self.view == "RESET":
            if   self.new_pass_rect.collidepoint(pos): self.active = "RESET_PASS"
            elif self.reset_btn.collidepoint(pos):
                threading.Thread(target=self._send_reset, daemon=True).start()

    def _handle_key(self, event):
        if event.key == pygame.K_RETURN:
            if   self.view == "INPUT":
                threading.Thread(target=self._send_auth,
                                 args=(MSG_LOGIN,), daemon=True).start()
            elif self.view == "OTP":
                threading.Thread(target=self._send_otp, daemon=True).start()
            elif self.view == "RESET":
                threading.Thread(target=self._send_reset, daemon=True).start()
            return
        if event.key == pygame.K_TAB:
            cycle = {"USER": "PASS", "PASS": "EMAIL", "EMAIL": "USER",
                     "OTP": "OTP", "RESET_PASS": "RESET_PASS"}
            self.active = cycle.get(self.active, self.active)
            return
        if event.key == pygame.K_BACKSPACE:
            self._del_char()
            return
        ch = event.unicode
        if not ch or ch == " ":
            return
        if   self.active == "USER"       and len(self.username) < 16: self.username += ch
        elif self.active == "PASS"       and len(self.password) < 16: self.password += ch
        elif self.active == "EMAIL"      and len(self.email)    < 50: self.email    += ch
        elif self.active == "OTP"        and ch.isdigit() and len(self.otp) < 4: self.otp += ch
        elif self.active == "RESET_PASS" and len(self.password) < 16: self.password += ch

    def _del_char(self):
        if   self.active == "USER":        self.username = self.username[:-1]
        elif self.active == "PASS":        self.password = self.password[:-1]
        elif self.active == "EMAIL":       self.email    = self.email[:-1]
        elif self.active == "OTP":         self.otp      = self.otp[:-1]
        elif self.active == "RESET_PASS":  self.password = self.password[:-1]

    def _send_auth(self, cmd_type):
        if self._busy: return
        if not self.username.strip() or not self.password.strip():
            self._status("Username and password are required.", False); return
        self._busy = True
        self._status("Connecting...", True)
        payload = {"cmd": cmd_type,
                   "username": self.username.strip(),
                   "password": self.password}
        if cmd_type == MSG_SIGNUP:
            if not self.email.strip():
                self._status("Email is required for sign-up.", False)
                self._busy = False; return
            payload["email"] = self.email.strip()
        try:
            self.net.send(payload)
            resp = self.net.recv()
        except Exception as e:
            self._status(f"Network error: {e}", False)
            self._busy = False; return
        if resp and resp.get("cmd") == "NEED_OTP":
            self.my_username = self.username.strip()
            self.purpose     = "REG" if cmd_type == MSG_SIGNUP else "LOG"
            self.otp = ""; self.active = "OTP"; self.view = "OTP"
            self._status(resp.get("msg", "Code sent!"), True)
        else:
            self._status(
                resp.get("msg", "Error") if resp else "No response from server.",
                False)
        self._busy = False

    def _send_forgot(self):
        if self._busy: return
        if not self.username.strip() or not self.email.strip():
            self._status("Enter username and email first.", False); return
        self._busy = True
        self._status("Sending reset code...", True)
        try:
            self.net.send({"cmd": "FORGOT_PASSWORD",
                           "username": self.username.strip(),
                           "email":    self.email.strip()})
            resp = self.net.recv()
        except Exception as e:
            self._status(f"Network error: {e}", False)
            self._busy = False; return
        if resp and resp.get("cmd") == "NEED_OTP":
            self.my_username = self.username.strip()
            self.purpose = "FORGOT"
            self.otp = ""; self.active = "OTP"; self.view = "OTP"
            self._status(resp.get("msg", "Code sent!"), True)
        else:
            self._status(
                resp.get("msg", "Error.") if resp else "No response.", False)
        self._busy = False

    def _send_otp(self):
        if self._busy: return
        if len(self.otp) < 4:
            self._status("Please enter the full 4-digit code.", False); return
        self._busy = True
        self._status("Verifying...", True)
        try:
            self.net.send({"cmd": "VERIFY_OTP",
                           "code": self.otp, "purpose": self.purpose})
            resp = self.net.recv()
        except Exception as e:
            self._status(f"Network error: {e}", False)
            self._busy = False; return
        if not resp:
            self._status("No response from server.", False)
            self._busy = False; return
        if resp.get("cmd") == "GOTO_RESET":
            self.password = ""; self.active = "RESET_PASS"; self.view = "RESET"
            self._status(resp.get("msg", "Enter new password."), True)
        elif resp.get("cmd") == MSG_AUTH_OK:
            self._balance        = resp.get("balance", 5000)
            self._in_char_select = True
            self._status("Authenticated! Choose your character.", True)
        else:
            self.otp = ""
            self._status(resp.get("msg", "Wrong code."), False)
        self._busy = False

    def _send_reset(self):
        if self._busy: return
        if not self.password.strip():
            self._status("Please enter a new password.", False); return
        self._busy = True
        self._status("Updating password...", True)
        try:
            self.net.send({"cmd": "RESET_PASSWORD", "password": self.password})
            resp = self.net.recv()
        except Exception as e:
            self._status(f"Network error: {e}", False)
            self._busy = False; return
        if resp and resp.get("cmd") == MSG_AUTH_OK:
            self.password = ""; self.otp = ""
            self.active = "USER"; self.view = "INPUT"
            self._status("Password updated! Please log in.", True)
        else:
            self._status(
                resp.get("msg", "Error.") if resp else "Error.", False)
        self._busy = False

    def _status(self, msg: str, ok: bool):
        self.status    = msg
        self.status_ok = ok

    def draw(self, screen):
        W, H = screen.get_size()
        cx   = W // 2
        self._build_rects(W, H)
        screen.fill(DARK)

        if self._in_char_select:
            self._draw_char_select(screen, W, H)
            return

        title = self.f_title.render("Casino Project", True, GOLD)
        screen.blit(title, (cx - title.get_width() // 2, 34))

        if self._busy:
            bt = self.f_med.render("Please wait...", True, (200, 200, 80))
            screen.blit(bt, (cx - bt.get_width() // 2, 90))

        if self.view == "INPUT":
            self._field(screen, "Username:",
                        self.username, self.user_rect, self.active == "USER")
            self._field(screen, "Password:",
                        "*" * len(self.password), self.pass_rect, self.active == "PASS")
            self._field(screen, "Email  (required for Sign-Up):",
                        self.email, self.email_rect, self.active == "EMAIL")
            self._btn(screen, self.login_btn,  "Login",   GREEN)
            self._btn(screen, self.signup_btn, "Sign Up", BLUE)
            pygame.draw.rect(screen, PANEL, self.forgot_btn, border_radius=5)
            ft = self.f_sm.render("Forgot password?", True, GRAY)
            screen.blit(ft, (self.forgot_btn.x +
                             (self.forgot_btn.w - ft.get_width()) // 2,
                             self.forgot_btn.y + 8))

        elif self.view == "OTP":
            lbl = self.f_med.render(
                "Enter the 4-digit code sent to your email:", True, WHITE)
            screen.blit(lbl, (cx - lbl.get_width() // 2, 185))
            pygame.draw.rect(screen, PANEL, self.otp_rect, border_radius=8)
            pygame.draw.rect(screen,
                             GOLD if self.active == "OTP" else GRAY,
                             self.otp_rect, 2, border_radius=8)
            ot = self.f_lg.render(self.otp or "____", True, WHITE)
            screen.blit(ot, (self.otp_rect.x +
                             (self.otp_rect.w - ot.get_width()) // 2,
                             self.otp_rect.y + 10))
            self._btn(screen, self.verify_btn, "Verify", (218, 165, 32))

        elif self.view == "RESET":
            lbl = self.f_med.render("Enter your new password:", True, WHITE)
            screen.blit(lbl, (cx - lbl.get_width() // 2, 200))
            self._field(screen, "New password:",
                        "*" * len(self.password),
                        self.new_pass_rect, self.active == "RESET_PASS")
            self._btn(screen, self.reset_btn, "Update Password", (199, 21, 133))

        col = (80, 220, 120) if self.status_ok else RED
        st  = self.f_sm.render(self.status, True, col)
        screen.blit(st, (cx - st.get_width() // 2, H - 115))
        hint = self.f_sm.render(
            "ENTER to confirm   |   TAB to switch fields", True, (75, 75, 105))
        screen.blit(hint, (cx - hint.get_width() // 2, H - 90))

    def _draw_char_select(self, screen, W, H):
        from client.characters import CharacterDrawer
        screen.fill((22, 38, 22))
        title = self.f_lg.render("Choose Your Character", True, GOLD)
        screen.blit(title, (W // 2 - title.get_width() // 2, 90))
        CharacterDrawer.draw_character(screen, self._char_id, W // 2, 290)
        hint = self.f_sm.render(
            f"Character {self._char_id}   < > arrows   ENTER to confirm",
            True, WHITE)
        screen.blit(hint, (W // 2 - hint.get_width() // 2, 390))
        st_col = (80, 220, 120) if self.status_ok else RED
        st = self.f_sm.render(self.status, True, st_col)
        screen.blit(st, (W // 2 - st.get_width() // 2, H - 80))

    def _field(self, screen, label, text, rect, active):
        screen.blit(self.f_sm.render(label, True, GRAY), (rect.x, rect.y - 20))
        pygame.draw.rect(screen, PANEL, rect, border_radius=6)
        pygame.draw.rect(screen, GOLD if active else (68, 68, 88),
                         rect, 2, border_radius=6)
        ts = self.f_med.render(text, True, WHITE)
        screen.blit(ts, (rect.x + 10,
                         rect.y + (rect.height - ts.get_height()) // 2))

    def _btn(self, screen, rect, label, color):
        pygame.draw.rect(screen, color, rect, border_radius=7)
        ts = self.f_med.render(label, True, WHITE)
        screen.blit(ts, (rect.x + (rect.width  - ts.get_width())  // 2,
                         rect.y + (rect.height - ts.get_height()) // 2))