__author__ = "Tamir Raz"

import pygame


class ChatBubble:
    def __init__(self, text: str, duration: int = 200):
        self.text  = text[:40]
        self.timer = duration

    def update(self):
        if self.timer > 0:
            self.timer -= 1

    def is_alive(self) -> bool:
        return self.timer > 0

    def draw(self, surf, cx, cy):
        if self.timer <= 0:
            return
        font = pygame.font.SysFont("Arial",13)
        ts   = font.render(self.text,True,(0,0,0))
        pad  = 7
        bw   = ts.get_width()  + pad*2
        bh   = ts.get_height() + pad*2
        bx   = cx - bw//2
        by   = cy - 78
        pygame.draw.rect(surf,(255,255,255),(bx,by,bw,bh),border_radius=7)
        pygame.draw.rect(surf,(0,0,0),      (bx,by,bw,bh),1,border_radius=7)
        pygame.draw.polygon(surf,(255,255,255),[(cx,by+bh),(cx-5,by+bh+6),(cx+5,by+bh+6)])
        pygame.draw.polygon(surf,(0,0,0),      [(cx,by+bh),(cx-5,by+bh+6),(cx+5,by+bh+6)],1)
        surf.blit(ts,(bx+pad,by+pad))


class ChatInputBox:
    def __init__(self, x, y, width, height, placeholder="Type a message..."):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.active = False
        self.placeholder = placeholder
        self.font = pygame.font.SysFont("Arial", 16)

    def handle_event(self, event) -> str | None:
        # Click inside box to activate
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        # Press T or ENTER to activate chat even without clicking
        if event.type == pygame.KEYDOWN:
            if not self.active:
                # T key activates chat (common in games)
                if event.key == pygame.K_t:
                    self.active = True
                    return None

            if self.active:
                if event.key == pygame.K_RETURN:
                    out = self.text.strip()
                    self.text = ""
                    self.active = False  # deactivate after sending
                    return out if out else None
                elif event.key == pygame.K_ESCAPE:
                    # ESC cancels chat without sending
                    self.text = ""
                    self.active = False
                    return None
                elif event.key == pygame.K_BACKSPACE:
                    self.text = self.text[:-1]
                elif event.unicode and len(self.text) < 80:
                    self.text += event.unicode

        return None

    def draw(self, surf):
        border = (255, 215, 0) if self.active else (80, 80, 110)
        pygame.draw.rect(surf, (20, 20, 40), self.rect)
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=5)

        if self.active:
            display = self.text + "|"  # blinking cursor effect
            color = (255, 255, 255)
        else:
            display = self.text if self.text else self.placeholder
            color = (255, 255, 255) if self.text else (100, 100, 130)

        ts = self.font.render(display, True, color)
        surf.blit(ts, (self.rect.x + 10,
                       self.rect.y + (self.rect.height - ts.get_height()) // 2))