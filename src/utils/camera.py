import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0
        
        # --- NUEVO: Suavizado ---
        self.lerp_speed = 0.08  # Entre 0 y 1. Menor = más suave/lento.
        
        # --- NUEVO: Posición objetivo flotante para precisión ---
        self.true_scroll_x = 0
        self.true_scroll_y = 0

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)
    
    def apply_coords(self, x, y):
        return (x + self.offset_x, y + self.offset_y)

    def update(self, target, mouse_pos=None):
        """
        Sigue al objetivo con suavizado (Lerp) y offset del mouse.
        """
        # 1. Calcular el centro deseado (donde debería estar la cámara idealmente)
        # Queremos centrar al jugador
        target_x = -target.rect.centerx + int(WINDOW_WIDTH / 2)
        target_y = -target.rect.centery + int(WINDOW_HEIGHT / 2)
        
        # 2. Look Ahead (Mirar hacia adelante)
        # Desplaza la cámara ligeramente hacia donde está el mouse
        if mouse_pos:
            # El mouse es relativo a la pantalla (0 a 800), lo centramos (-400 a 400)
            mx = mouse_pos[0] - WINDOW_WIDTH / 2
            my = mouse_pos[1] - WINDOW_HEIGHT / 2
            # Añadimos un porcentaje de esa distancia (ej. 20%)
            target_x -= mx * 0.2
            target_y -= my * 0.2

        # 3. Aplicar LERP (Suavizado)
        # Fórmula: Actual += (Destino - Actual) * Velocidad
        self.true_scroll_x += (target_x - self.true_scroll_x) * self.lerp_speed
        self.true_scroll_y += (target_y - self.true_scroll_y) * self.lerp_speed
        
        # 4. Limitar a los bordes del mundo (Clamping)
        # Convertimos a entero para Pygame
        x = int(self.true_scroll_x)
        y = int(self.true_scroll_y)
        
        # Evitar ver fuera del mapa
        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))
        
        # Si choca con el borde, ajustamos el scroll verdadero para evitar "tirones" al salir del borde
        if x == 0 or x == -(self.width - WINDOW_WIDTH):
            self.true_scroll_x = x
        if y == 0 or y == -(self.height - WINDOW_HEIGHT):
            self.true_scroll_y = y

        self.camera = pygame.Rect(x, y, self.width, self.height)
        self.offset_x = x
        self.offset_y = y