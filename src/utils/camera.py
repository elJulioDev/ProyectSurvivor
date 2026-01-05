import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0

    def apply(self, entity):
        """Retorna un Rect desplazado por la cámara (para renderizado)"""
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        """Aplica el desplazamiento a un Rect arbitrario"""
        return rect.move(self.camera.topleft)
    
    def apply_coords(self, x, y):
        """Retorna tupla (x, y) ajustada a la cámara"""
        return (x + self.offset_x, y + self.offset_y)

    def update(self, target):
        """Sigue al objetivo (jugador)"""
        # Queremos que el jugador esté en el centro de la pantalla
        x = -target.rect.centerx + int(WINDOW_WIDTH / 2)
        y = -target.rect.centery + int(WINDOW_HEIGHT / 2)

        # Limitar la cámara a los bordes del mundo (Clamping)
        # No dejar que se vea lo negro fuera del mapa
        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))

        self.camera = pygame.Rect(x, y, self.width, self.height)
        self.offset_x = x
        self.offset_y = y