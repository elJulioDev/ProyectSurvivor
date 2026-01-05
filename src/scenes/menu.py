"""
Escena del menú principal
"""
import pygame
from scenes.scene import Scene
from settings import BLACK, WHITE, WINDOW_WIDTH, WINDOW_HEIGHT

class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font_title = pygame.font.Font(None, 84)
        self.font_normal = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 28)
        
        # Animación del título
        self.title_scale = 1.0
        self.title_direction = 1
    
    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                from scenes.gameplay import GameplayScene
                self.next_scene = GameplayScene(self.game)
    
    def update(self):
        # Animación sutil del título
        self.title_scale += 0.002 * self.title_direction
        if self.title_scale >= 1.05 or self.title_scale <= 0.95:
            self.title_direction *= -1
    
    def render(self):
        self.screen.fill(BLACK)
        
        # Título animado con sombra
        title_text = "ProyectSurvivor"
        title_size = int(84 * self.title_scale)
        font_animated = pygame.font.Font(None, title_size)
        
        # Sombra
        shadow = font_animated.render(title_text, True, (50, 50, 50))
        shadow_rect = shadow.get_rect(center=(WINDOW_WIDTH//2 + 3, 203))
        self.screen.blit(shadow, shadow_rect)
        
        # Título
        title = font_animated.render(title_text, True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 200))
        self.screen.blit(title, title_rect)
        
        # Subtítulo
        subtitle = self.font_small.render("Un juego de supervivencia", True, (150, 150, 150))
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH//2, 250))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Instrucciones de inicio
        start_text = self.font_normal.render("Presiona ESPACIO para comenzar", True, (200, 200, 200))
        start_rect = start_text.get_rect(center=(WINDOW_WIDTH//2, 350))
        
        # Parpadeo sutil
        alpha = int(200 + 55 * abs(pygame.time.get_ticks() % 1000 - 500) / 500)
        start_surf = pygame.Surface(start_text.get_size(), pygame.SRCALPHA)
        start_surf.fill((0, 0, 0, 0))
        start_surf.blit(start_text, (0, 0))
        start_surf.set_alpha(alpha)
        self.screen.blit(start_surf, start_rect)
        
        # Controles
        controls_title = self.font_normal.render("Controles", True, (180, 180, 180))
        controls_rect = controls_title.get_rect(center=(WINDOW_WIDTH//2, 420))
        self.screen.blit(controls_title, controls_rect)
        
        controls = [
            "WASD o Flechas - Mover",
            "Mouse - Apuntar",
            "Click Izquierdo - Disparar",
            "ESC - Volver al menú"
        ]
        
        y_start = 460
        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, (150, 150, 150))
            rect = text.get_rect(center=(WINDOW_WIDTH//2, y_start + i * 25))
            self.screen.blit(text, rect)