import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()

from client.main_client import CasinoClient

if __name__ == "__main__":
    CasinoClient().run()