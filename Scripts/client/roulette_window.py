import pygame
import math

WHEEL_NUMBERS = [0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,
                 8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26]
RED_SET = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}

DARK_GREEN  = (5,  71, 42)
LIGHT_GREEN = (10,102, 62)
GOLD        = (212,175,55)
WHITE       = (255,255,255)
BLACK       = (0,  0,  0)

BET_LABELS = ["RED","BLACK","GREEN  (35×)","LOW  (1–18)","HIGH (19–36)",
              "1st Dozen","2nd Dozen","3rd Dozen"]


class RouletteWindow:
    def __init__(self, screen_w=900, screen_h=620):
        self.W, self.H = screen_w, screen_h
        self.cx, self.cy, self.R, self.r = 270, 320, 200, 65
        self.rotation   = 0.0
        self.spin_speed = 0.0
        self.spinning   = False
        self.time_left  = 20
        self.win_number = None
        self.win_color  = None
        self.result_msg   = ""
        self.result_col   = WHITE
        self.result_timer = 0
        self.bet_amount       = 100
        self.selected_bet     = None
        self.font_sm = self.font_med = self.font_lg = None
        self._build_ui_rects()

    def _build_ui_rects(self):
        x0, y0, bw, bh, gap = 570, 100, 290, 36, 7
        self.bet_rects = [(label, pygame.Rect(x0, y0+i*(bh+gap), bw, bh))
                          for i, label in enumerate(BET_LABELS)]
        ctrl_y         = y0 + len(BET_LABELS)*(bh+gap) + 14
        self.btn_minus = pygame.Rect(x0,       ctrl_y, 80, 34)
        self.btn_plus  = pygame.Rect(x0+210,   ctrl_y, 80, 34)
        self.btn_bet   = pygame.Rect(x0, ctrl_y+48, bw, 44)
        self.num_rects = {}
        nx0, ny0, nw, nh = 30, self.H-68, 22, 22
        for n in range(37):
            self.num_rects[n] = pygame.Rect(nx0+(n%19)*(nw+2), ny0+(n//19)*(nh+2), nw, nh)

    def _init_fonts(self):
        self.font_sm  = pygame.font.SysFont("Arial",13)
        self.font_med = pygame.font.SysFont("Arial",17,bold=True)
        self.font_lg  = pygame.font.SysFont("Arial",28,bold=True)

    def update(self):
        if self.spinning:
            self.spin_speed = min(self.spin_speed+0.35, 9.0)
            self.rotation  += self.spin_speed
            if self.rotation >= 360:
                self.rotation -= 360
        if self.result_timer > 0:
            self.result_timer -= 1

    def start_spinning(self):
        self.spinning   = True
        self.spin_speed = 2.5

    def stop_spinning(self, win_number, win_color):
        if win_number in WHEEL_NUMBERS:
            idx = WHEEL_NUMBERS.index(win_number)
            self.rotation = (270 - idx*(360/len(WHEEL_NUMBERS)) - (360/len(WHEEL_NUMBERS))/2) % 360
        self.spin_speed = 0.0
        self.spinning   = False
        self.win_number = win_number
        self.win_color  = win_color

    def show_result(self, msg, won):
        self.result_msg   = msg
        self.result_col   = (0,220,100) if won else (255,80,80)
        self.result_timer = 240

    def draw(self, surf, balance=5000):
        if not self.font_sm:
            self._init_fonts()
        surf.fill((15,55,30))
        self._draw_wheel(surf)
        self._draw_arrow(surf)
        self._draw_timer_info(surf)
        self._draw_right_panel(surf, balance)
        self._draw_number_grid(surf)
        if self.result_timer > 0:
            ts = self.font_lg.render(self.result_msg, True, self.result_col)
            surf.blit(ts,(self.cx-ts.get_width()//2, self.cy-ts.get_height()//2))

    def _draw_wheel(self, surf):
        n, deg = len(WHEEL_NUMBERS), 360/len(WHEEL_NUMBERS)
        cx,cy,R,r = self.cx,self.cy,self.R,self.r
        for i, num in enumerate(WHEEL_NUMBERS):
            start, end = self.rotation+i*deg, self.rotation+i*deg+deg
            color = (0,160,60) if num==0 else (180,20,20) if num in RED_SET else (28,28,28)
            pts = [(cx,cy)]
            for step in range(21):
                a = math.radians(start+(end-start)*step/20-90)
                pts.append((cx+R*math.cos(a), cy+R*math.sin(a)))
            pygame.draw.polygon(surf,color,pts)
            pygame.draw.polygon(surf,GOLD, pts,1)
            pts2 = [(cx,cy)]
            for step in range(21):
                a = math.radians(start+(end-start)*step/20-90)
                pts2.append((cx+r*math.cos(a), cy+r*math.sin(a)))
            pygame.draw.polygon(surf,(18,38,20),pts2)
            pygame.draw.polygon(surf,GOLD,pts2,1)
            mid_a = math.radians(start+deg/2-90)
            tx = cx+(r+(R-r)*0.62)*math.cos(mid_a)
            ty = cy+(r+(R-r)*0.62)*math.sin(mid_a)
            ts = self.font_sm.render(str(num),True,WHITE)
            ts_rot = pygame.transform.rotate(ts,-(start+deg/2))
            surf.blit(ts_rot,(tx-ts_rot.get_width()//2, ty-ts_rot.get_height()//2))
        pygame.draw.circle(surf,(35,28,8),(cx,cy),r)
        pygame.draw.circle(surf,GOLD,     (cx,cy),r,2)
        pygame.draw.circle(surf,GOLD,     (cx,cy),14)

    def _draw_arrow(self, surf):
        cx,cy,R = self.cx,self.cy,self.R
        tip = (cx, cy-R-8)
        pts = [tip,(cx-11,cy-R-28),(cx+11,cy-R-28)]
        pygame.draw.polygon(surf,GOLD, pts)
        pygame.draw.polygon(surf,WHITE,pts,2)

    def _draw_timer_info(self, surf):
        if self.spinning:
            msg,col = "SPINNING…",GOLD
        else:
            msg = f"Place bets: {self.time_left}s"
            col = (0,230,120) if self.time_left>8 else (255,120,50)
        ts = self.font_med.render(msg,True,col)
        surf.blit(ts,(self.cx-ts.get_width()//2, self.cy+self.R+18))
        if self.win_number is not None and not self.spinning:
            wc = ((0,200,80) if self.win_color=="GREEN" else
                  (220,50,50) if self.win_color=="RED" else (200,200,200))
            wt = self.font_lg.render(f"▶  {self.win_number}  ◀",True,wc)
            surf.blit(wt,(self.cx-wt.get_width()//2, self.cy+self.R+46))

    def _draw_right_panel(self, surf, balance):
        panel = pygame.Rect(562,55,316,520)
        pygame.draw.rect(surf,(18,48,26),panel,border_radius=10)
        pygame.draw.rect(surf,GOLD,panel,2,border_radius=10)
        surf.blit(self.font_med.render(f"Balance: {balance} chips",True,GOLD),(572,65))
        mx,my = pygame.mouse.get_pos()
        for label,rect in self.bet_rects:
            is_sel   = self.selected_bet is not None and self.selected_bet[0]==label
            is_hover = rect.collidepoint(mx,my)
            if is_sel:
                pygame.draw.rect(surf,GOLD,rect,border_radius=6)
                ts = self.font_sm.render(label,True,BLACK)
            elif is_hover:
                pygame.draw.rect(surf,LIGHT_GREEN,rect,border_radius=6)
                ts = self.font_sm.render(label,True,WHITE)
            else:
                pygame.draw.rect(surf,(28,58,34),rect,border_radius=6)
                pygame.draw.rect(surf,GOLD,rect,1,border_radius=6)
                ts = self.font_sm.render(label,True,WHITE)
            surf.blit(ts,(rect.x+8, rect.y+(rect.height-ts.get_height())//2))
        surf.blit(self.font_sm.render(f"Bet: {self.bet_amount} chips",True,WHITE),
                  (572, self.btn_minus.y-20))
        for btn,lbl in [(self.btn_minus,"−"),(self.btn_plus,"+")]:
            pygame.draw.rect(surf,(38,80,48),btn,border_radius=6)
            pygame.draw.rect(surf,GOLD,btn,1,border_radius=6)
            bt = self.font_med.render(lbl,True,GOLD)
            surf.blit(bt,(btn.x+(btn.w-bt.get_width())//2, btn.y+(btn.h-bt.get_height())//2))
        btn_col = (175,140,0) if not self.spinning else (50,50,50)
        pygame.draw.rect(surf,btn_col,self.btn_bet,border_radius=8)
        bbt = self.font_med.render("PLACE BET" if not self.spinning else "BETS CLOSED",
                                   True, BLACK if not self.spinning else (100,100,100))
        surf.blit(bbt,(self.btn_bet.x+(self.btn_bet.w-bbt.get_width())//2,
                       self.btn_bet.y+(self.btn_bet.h-bbt.get_height())//2))

    def _draw_number_grid(self, surf):
        surf.blit(self.font_sm.render("Or bet on a single number:",True,WHITE),(30,self.H-86))
        for n,rect in self.num_rects.items():
            c = (0,150,60) if n==0 else (160,20,20) if n in RED_SET else (30,30,30)
            pygame.draw.rect(surf,c,rect)
            pygame.draw.rect(surf,GOLD,rect,1)
            nt = self.font_sm.render(str(n),True,WHITE)
            if nt.get_width() <= rect.width:
                surf.blit(nt,(rect.x+(rect.width-nt.get_width())//2,
                              rect.y+(rect.height-nt.get_height())//2))

    def handle_click(self, pos):
        if self.btn_minus.collidepoint(pos):
            self.bet_amount = max(10, self.bet_amount-50); return None
        if self.btn_plus.collidepoint(pos):
            self.bet_amount = min(5000, self.bet_amount+50); return None
        if self.btn_bet.collidepoint(pos):
            return "CONFIRM" if not self.spinning else None
        for label,rect in self.bet_rects:
            if rect.collidepoint(pos):
                if   label=="RED":                  return (label,"COLOR","RED")
                elif label=="BLACK":                return (label,"COLOR","BLACK")
                elif label.startswith("GREEN"):     return (label,"COLOR","GREEN")
                elif label.startswith("LOW"):       return (label,"HALF","LOW")
                elif label.startswith("HIGH"):      return (label,"HALF","HIGH")
                elif label.startswith("1st"):       return (label,"DOZEN","1")
                elif label.startswith("2nd"):       return (label,"DOZEN","2")
                elif label.startswith("3rd"):       return (label,"DOZEN","3")
        for n,rect in self.num_rects.items():
            if rect.collidepoint(pos):
                return (f"Number {n}","NUMBER",str(n))
        return None