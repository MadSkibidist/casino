import pygame
from client.card_drawer import CardDrawer

GOLD  = (212,175,55)
WHITE = (255,255,255)
BLACK = (0,0,0)
GREEN = (15,60,30)


class PokerWindow:
    def __init__(self, screen_w=900, screen_h=620):
        self.W, self.H         = screen_w, screen_h
        self.stage             = "WAITING"
        self.community_cards   = []
        self.my_hand           = []
        self.current_turn      = ""
        self.folded            = []
        self.player_count      = 0
        self.pot               = 0
        self.winner_msg        = ""
        self.winner_timer      = 0
        self.all_hands         = {}
        self.font_sm = self.font_med = self.font_lg = None
        bx,by0,bw,bh = 680,340,190,42
        self.btn_check = pygame.Rect(bx,by0,      bw,bh)
        self.btn_call  = pygame.Rect(bx,by0+52,   bw,bh)
        self.btn_raise = pygame.Rect(bx,by0+104,  bw,bh)
        self.btn_fold  = pygame.Rect(bx,by0+156,  bw,bh)
        self.raise_amount    = 100
        self.btn_raise_minus = pygame.Rect(bx,     by0+212,50,32)
        self.btn_raise_plus  = pygame.Rect(bx+110, by0+212,80,32)

    def _init_fonts(self):
        self.font_sm  = pygame.font.SysFont("Arial",14)
        self.font_med = pygame.font.SysFont("Arial",18,bold=True)
        self.font_lg  = pygame.font.SysFont("Arial",30,bold=True)

    def update_state(self, data, my_username):
        self.stage           = data.get("stage",          self.stage)
        self.community_cards = data.get("community_cards",self.community_cards)
        self.current_turn    = data.get("current_turn",   "")
        self.folded          = data.get("folded",         [])
        self.player_count    = data.get("player_count",   0)
        self.pot             = data.get("pot",            0)
        hands = data.get("player_hands",{})
        if my_username in hands:
            self.my_hand = hands[my_username]

    def show_result(self, data, my_username):
        self.winner_msg   = f"Winner: {data.get('winner','?')}  ({data.get('reason','')})  Pot: {data.get('pot',0)}"
        self.winner_timer = 300
        self.all_hands    = data.get("all_hands",{})
        self.community_cards = data.get("community",self.community_cards)
        if my_username in self.all_hands:
            self.my_hand = self.all_hands[my_username]

    def update(self):
        if self.winner_timer > 0:
            self.winner_timer -= 1
        if self.winner_timer == 0:
            self.all_hands = {}

    def draw(self, surf, my_username, balance):
        if not self.font_sm:
            self._init_fonts()
        surf.fill(GREEN)
        pygame.draw.ellipse(surf,(18,82,40),(70,150,660,290))
        pygame.draw.ellipse(surf,GOLD,      (70,150,660,290),3)
        self._draw_info(surf,my_username,balance)
        self._draw_community(surf)
        self._draw_my_hand(surf,my_username)
        self._draw_opponent_hands(surf,my_username)
        self._draw_action_panel(surf,my_username)
        if self.winner_timer > 0:
            ts = self.font_lg.render(self.winner_msg,True,GOLD)
            rx = self.W//2 - ts.get_width()//2
            pygame.draw.rect(surf,BLACK,(rx-10,258,ts.get_width()+20,ts.get_height()+12),border_radius=8)
            surf.blit(ts,(rx,263))

    def _draw_info(self,surf,my_username,balance):
        surf.blit(self.font_med.render(f"Stage: {self.stage}   Pot: {self.pot} chips   Players: {self.player_count}",True,GOLD),(18,12))
        surf.blit(self.font_sm.render(f"{my_username} — Balance: {balance} chips",True,WHITE),(18,38))
        if self.current_turn:
            is_mine = self.current_turn==my_username
            surf.blit(self.font_sm.render("YOUR TURN" if is_mine else f"Turn: {self.current_turn}",
                                          True,(0,230,100) if is_mine else (200,200,200)),(18,60))
        if self.stage=="WAITING":
            wt = self.font_lg.render("Waiting for players…  (need 2)",True,GOLD)
            surf.blit(wt,(self.W//2-wt.get_width()//2,250))

    def _draw_community(self,surf):
        if not self.community_cards:
            ph = self.font_sm.render("Community cards appear here after Preflop",True,(110,160,110))
            surf.blit(ph,(self.W//2-ph.get_width()//2,278)); return
        x0 = self.W//2 - len(self.community_cards)*40
        surf.blit(self.font_sm.render("Community:",True,(180,220,180)),(x0,185))
        for i,card in enumerate(self.community_cards):
            CardDrawer.draw_card(surf,x0+i*80,202,card["value_str"],card["suit"])

    def _draw_my_hand(self,surf,my_username):
        surf.blit(self.font_sm.render("Your hand:",True,GOLD),(18,454))
        for i,card in enumerate(self.my_hand):
            CardDrawer.draw_card(surf,18+i*80,472,card["value_str"],card["suit"])
        if my_username in self.folded:
            surf.blit(self.font_med.render("FOLDED",True,(255,80,80)),(18,580))

    def _draw_opponent_hands(self,surf,my_username):
        if not self.all_hands: return
        x,y = 18,88
        for user,hand in self.all_hands.items():
            if user==my_username: continue
            surf.blit(self.font_sm.render(f"{user}:",True,(200,200,200)),(x,y))
            for i,card in enumerate(hand):
                CardDrawer.draw_card(surf,x+i*42,y+18,card["value_str"],card["suit"],38,54)
            x += 170
            if x > 500: x,y = 18,y+90

    def _draw_action_panel(self,surf,my_username):
        panel = pygame.Rect(670,320,218,240)
        pygame.draw.rect(surf,(15,50,22),panel,border_radius=10)
        pygame.draw.rect(surf,GOLD,panel,2,border_radius=10)
        is_my_turn = (self.current_turn==my_username and
                      self.stage not in ("WAITING",) and
                      my_username not in self.folded and not self.all_hands)
        for btn,label,col in [(self.btn_check,"CHECK",(20,60,80)),
                               (self.btn_call, "CALL", (40,100,50)),
                               (self.btn_raise,f"RAISE  +{self.raise_amount}",(80,60,10)),
                               (self.btn_fold, "FOLD", (120,20,20))]:
            pygame.draw.rect(surf,col if is_my_turn else (38,38,38),btn,border_radius=7)
            pygame.draw.rect(surf,GOLD if is_my_turn else (60,60,60),btn,1,border_radius=7)
            ts = self.font_sm.render(label,True,WHITE if is_my_turn else (90,90,90))
            surf.blit(ts,(btn.x+(btn.w-ts.get_width())//2, btn.y+(btn.h-ts.get_height())//2))
        for btn,sym in [(self.btn_raise_minus,"−"),(self.btn_raise_plus,"+")]:
            pygame.draw.rect(surf,(38,80,48) if is_my_turn else (30,30,30),btn,border_radius=5)
            pygame.draw.rect(surf,GOLD,btn,1,border_radius=5)
            ts = self.font_med.render(sym,True,GOLD)
            surf.blit(ts,(btn.x+(btn.w-ts.get_width())//2, btn.y+(btn.h-ts.get_height())//2))

    def handle_click(self, pos, my_username):
        is_my_turn = (self.current_turn==my_username and
                      self.stage not in ("WAITING",) and
                      my_username not in self.folded and not self.all_hands)
        if self.btn_raise_minus.collidepoint(pos):
            self.raise_amount = max(10,self.raise_amount-50); return None
        if self.btn_raise_plus.collidepoint(pos):
            self.raise_amount = min(2000,self.raise_amount+50); return None
        if not is_my_turn: return None
        if self.btn_check.collidepoint(pos): return "CHECK"
        if self.btn_call.collidepoint(pos):  return "CALL"
        if self.btn_raise.collidepoint(pos): return "RAISE"
        if self.btn_fold.collidepoint(pos):  return "FOLD"
        return None