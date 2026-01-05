import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0
        
        # Suavizado (Lerp)
        self.lerp_speed = 0.08
        
        # Precisión float
        self.true_scroll_x = 0
        self.true_scroll_y = 0
        
        # --- NUEVO: Rectángulo de visión con margen para Culling ---
        # Definimos qué tan lejos fuera de la pantalla seguimos renderizando
        # para evitar que las cosas aparezcan de golpe (pop-in).
        self.culling_margin = 100 
        self.viewport_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)
    
    def apply_coords(self, x, y):
        return (x + self.offset_x, y + self.offset_y)
        
    def is_on_screen(self, rect):
        """
        Determina si un rectángulo (en coordenadas de mundo) 
        debe renderizarse, aplicando un margen de seguridad.
        """
        # Convertimos el rect del mundo a coordenadas de pantalla
        screen_rect = self.apply_rect(rect)
        
        # Creamos un rectángulo de la pantalla "inflado" con el margen
        # Si el objeto toca este área ampliada, se dibuja.
        display_area = self.viewport_rect.inflate(self.culling_margin, self.culling_margin)
        
        return screen_rect.colliderect(display_area)

    def update(self, target, mouse_pos=None):
        """
        Sigue al objetivo con suavizado y offset dinámico del mouse.
        """
        # 1. Centro deseado (Jugador)
        target_x = -target.rect.centerx + int(WINDOW_WIDTH / 2)
        target_y = -target.rect.centery + int(WINDOW_HEIGHT / 2)
        
        # 2. Look Ahead (Mirar hacia adelante con el mouse)
        if mouse_pos:
            # Distancia del mouse al centro de la pantalla
            mx = mouse_pos[0] - WINDOW_WIDTH / 2
            my = mouse_pos[1] - WINDOW_HEIGHT / 2
            
            # --- AJUSTE: Aumentamos el factor (0.4) para que la cámara se mueva más ---
            # Esto permite ver más "entorno" al apuntar.
            target_x -= mx * 0.4 
            target_y -= my * 0.4

        # 3. Aplicar Lerp (Suavizado)
        self.true_scroll_x += (target_x - self.true_scroll_x) * self.lerp_speed
        self.true_scroll_y += (target_y - self.true_scroll_y) * self.lerp_speed
        
        # 4. Limitar al mundo (Clamping)
        x = int(self.true_scroll_x)
        y = int(self.true_scroll_y)
        
        # Evitar ver fuera del mapa (zona negra)
        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))
        
        # Corrección de "rebote" en los bordes
        if x == 0 or x == -(self.width - WINDOW_WIDTH):
            self.true_scroll_x = x
        if y == 0 or y == -(self.height - WINDOW_HEIGHT):
            self.true_scroll_y = y

        self.camera = pygame.Rect(x, y, self.width, self.height)
        self.offset_x = x
        self.offset_y = y