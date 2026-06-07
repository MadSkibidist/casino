import pygame
import sys
from shared.protocol import encode

# הגדרות צבעים
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GREEN = (5, 71, 42)
LIGHT_GREEN = (10, 102, 62)
GOLD = (212, 175, 55)


class LobbyWindow:
    def __init__(self, screen, client_socket, username):
        self.screen = screen
        self.client_socket = client_socket
        self.username = username
        self.font = pygame.font.Font(None, 36)
        self.title_font = pygame.font.Font(None, 60)

        # הגדרת מיקומים וגדלים של כפתורי המשחקים
        self.buttons = {
            "ROULETTE": pygame.Rect(300, 200, 200, 60),
            "BLACKJACK": pygame.Rect(300, 300, 200, 60),
            "POKER": pygame.Rect(300, 400, 200, 60)
        }

    def draw(self, balance=5000):
        """ציור מסך הלובי"""
        # רקע ירוק קלאסי של אולם משחקים
        self.screen.fill(DARK_GREEN)

        # כותרת ראשית
        title_text = self.title_font.render(f"Welcome, {self.username}!", True, GOLD)
        self.screen.blit(title_text, (400 - title_text.get_width() // 2, 50))

        # תצוגת אסימונים (Balance)
        balance_text = self.font.render(f"Your Balance: {balance} Chips", True, WHITE)
        self.screen.blit(balance_text, (400 - balance_text.get_width() // 2, 120))

        # ציור הכפתורים
        mouse_pos = pygame.mouse.get_pos()
        for game_name, rect in self.buttons.items():
            # אפקט כפתור מואר כאשר העכבר מרחף מעליו (Hover)
            color = LIGHT_GREEN if rect.collidepoint(mouse_pos) else BLACK
            pygame.draw.rect(self.screen, color, rect, border_radius=10)
            pygame.draw.rect(self.screen, GOLD, rect, width=2, border_radius=10)

            # כיתוב על הכפתור
            btn_text = self.font.render(game_name, True, GOLD)
            self.screen.blit(btn_text, (rect.x + (rect.width - btn_text.get_width()) // 2,
                                        rect.y + (rect.height - btn_text.get_height()) // 2))

    def handle_event(self, event):
        """טיפול בלחיצות עכבר ומעבר משחקים"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for game_name, rect in self.buttons.items():
                if rect.collidepoint(event.pos):
                    print(f"[LOBBY] Requesting to join {game_name}...")

                    # שליחת הודעת הצטרפות לשרת לפי הפרוטוקול המעודכן
                    join_payload = {
                        "cmd": "JOIN_TABLE",
                        "table_type": game_name
                    }
                    try:
                        self.client_socket.sendall(encode(join_payload))
                        # נחזיר את שם המשחק הנבחר כדי שהלולאה הראשית תדע להחליף מסך
                        return game_name
                    except Exception as e:
                        print(f"[LOBBY] Error sending join command: {e}")

        return None