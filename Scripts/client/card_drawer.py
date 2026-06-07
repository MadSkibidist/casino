import pygame

WHITE = (255,255,255)
BLACK = (0,0,0)
RED   = (200,0,0)
GOLD  = (212,175,55)

_SUIT_SYM = {
    "H": "♥", "D": "♦", "C": "♣", "S": "♠",
    "Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠",
}
_SUIT_COLOR = {
    "H": RED, "D": RED, "C": BLACK, "S": BLACK,
    "Hearts": RED, "Diamonds": RED, "Clubs": BLACK, "Spades": BLACK,
}


class CardDrawer:
    @staticmethod
    def draw_card(screen, x, y, value, suit, width=72, height=100):
        sym   = _SUIT_SYM.get(suit,"?")
        color = _SUIT_COLOR.get(suit, BLACK)
        fs = pygame.font.SysFont("Arial",15,bold=True)
        fl = pygame.font.SysFont("Arial",30,bold=True)
        rect = pygame.Rect(x,y,width,height)
        pygame.draw.rect(screen,WHITE,rect,border_radius=8)
        pygame.draw.rect(screen,GOLD, rect,2,border_radius=8)
        v_surf = fs.render(value,True,color)
        s_surf = fs.render(sym,True,color)
        screen.blit(v_surf,(x+5,y+4))
        screen.blit(s_surf,(x+5,y+19))
        cs = fl.render(sym,True,color)
        screen.blit(cs,(x+(width-cs.get_width())//2, y+(height-cs.get_height())//2))
        screen.blit(v_surf,(x+width-v_surf.get_width()-5, y+height-34))
        screen.blit(s_surf,(x+width-s_surf.get_width()-5, y+height-19))

    @staticmethod
    def draw_card_back(screen, x, y, width=72, height=100):
        rect  = pygame.Rect(x,y,width,height)
        inner = pygame.Rect(x+4,y+4,width-8,height-8)
        pygame.draw.rect(screen,WHITE,     rect, border_radius=8)
        pygame.draw.rect(screen,GOLD,      rect, 2,border_radius=8)
        pygame.draw.rect(screen,(20,40,80),inner,border_radius=6)
        pygame.draw.rect(screen,GOLD,      inner,2,border_radius=6)