__author__ = "Tamir Raz"

import pygame
import math


class CharacterDrawer:
    @staticmethod
    def _face(surf, x, y, skin):
        pygame.draw.circle(surf, skin,          (x, y),     25)
        pygame.draw.circle(surf, (255,255,255), (x-8, y-5),  4)
        pygame.draw.circle(surf, (255,255,255), (x+8, y-5),  4)
        pygame.draw.circle(surf, (0,0,0),       (x-8, y-5),  2)
        pygame.draw.circle(surf, (0,0,0),       (x+8, y-5),  2)
        pygame.draw.arc(surf, (0,0,0), (x-7, y, 14, 10), math.pi, 0, 2)

    @staticmethod
    def draw_char_0(s,x,y):
        pygame.draw.rect(s,(30,144,255),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))
        pygame.draw.ellipse(s,(220,20,60),(x-25,y-30,50,15))
        pygame.draw.rect(s,(220,20,60),(x-20,y-25,40,5))

    @staticmethod
    def draw_char_1(s,x,y):
        pygame.draw.rect(s,(255,215,0),(x-28,y-20,56,50),border_radius=10)
        pygame.draw.rect(s,(46,139,87),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,218,185))

    @staticmethod
    def draw_char_2(s,x,y):
        pygame.draw.rect(s,(30,30,30),(x-20,y+20,40,30),border_radius=5)
        pygame.draw.polygon(s,(220,20,60),[(x,y+20),(x-5,y+35),(x+5,y+35)])
        CharacterDrawer._face(s,x,y,(244,164,96))
        pygame.draw.circle(s,(0,0,0),(x-8,y-5),6,2)
        pygame.draw.circle(s,(0,0,0),(x+8,y-5),6,2)
        pygame.draw.line(s,(0,0,0),(x-2,y-5),(x+2,y-5),2)

    @staticmethod
    def draw_char_3(s,x,y):
        pygame.draw.rect(s,(100,100,100),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))
        pygame.draw.arc(s,(139,69,19),(x-15,y+5,30,18),math.pi,0,4)

    @staticmethod
    def draw_char_4(s,x,y):
        pygame.draw.rect(s,(255,69,0),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))
        pygame.draw.ellipse(s,(75,0,130),(x-22,y-32,44,18))
        pygame.draw.circle(s,(255,255,255),(x,y-32),5)

    @staticmethod
    def draw_char_5(s,x,y):
        pygame.draw.circle(s,(0,0,0),(x+22,y-5),10)
        pygame.draw.rect(s,(138,43,226),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))

    @staticmethod
    def draw_char_6(s,x,y):
        pygame.draw.rect(s,(192,192,192),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(222,184,135))
        pygame.draw.circle(s,(255,0,0),(x-8,y-5),5)
        pygame.draw.circle(s,(255,255,255),(x-8,y-5),1)

    @staticmethod
    def draw_char_7(s,x,y):
        pygame.draw.rect(s,(255,0,0),(x-4,y-38,8,15))
        pygame.draw.rect(s,(255,215,0),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))

    @staticmethod
    def draw_char_8(s,x,y):
        pygame.draw.rect(s,(240,240,240),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(101,67,33))
        pygame.draw.rect(s,(0,128,128),(x-24,y-20,48,6))

    @staticmethod
    def draw_char_9(s,x,y):
        pygame.draw.rect(s,(255,182,193),(x-20,y+20,40,30),border_radius=5)
        CharacterDrawer._face(s,x,y,(255,224,189))
        pygame.draw.polygon(s,(0,0,0),[(x-8,y+22),(x,y+26),(x-8,y+30)])
        pygame.draw.polygon(s,(0,0,0),[(x+8,y+22),(x,y+26),(x+8,y+30)])

    @classmethod
    def draw_character(cls, surf, char_id, x, y):
        methods = [cls.draw_char_0,cls.draw_char_1,cls.draw_char_2,
                   cls.draw_char_3,cls.draw_char_4,cls.draw_char_5,
                   cls.draw_char_6,cls.draw_char_7,cls.draw_char_8,cls.draw_char_9]
        methods[max(0,min(int(char_id),9))](surf,x,y)