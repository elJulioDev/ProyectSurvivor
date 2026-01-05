"""
Escena del menú principal MEJORADA
"""
import pygame
import math
from scenes.scene import Scene
from settings import BLACK, WHITE, WINDOW_WIDTH, WINDOW_HEIGHT, CYAN, DARK_GRAY

class MenuScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.font_title = pygame.font.Font(None, 90)
        self.font_normal = pygame.font.Font(None, 36)
        self.font_small = pygame.font.Font(None, 28)
        
        # --- CONTROL DE TIEMPO ---
        self.clock = pygame.time.Clock()
        self.timer = 0  # Tiempo acumulado para funciones seno/coseno
        
        # --- ANIMACIÓN ---
        self.title_scale = 1.0
        
        # Fondo en movimiento
        self.bg_scroll_x = 0
        self.bg_scroll_y = 0
        self.bg_speed = 0.5  # Velocidad lenta
    
    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                from scenes.gameplay import GameplayScene
                self.next_scene = GameplayScene(self.game)
    
    def update(self):
        # Limitamos a 60 FPS para consistencia en el menú
        # dt será aprox 1.0 a 60 FPS
        dt_ms = self.clock.tick(60)
        dt = dt_ms / 16.0  # Normalizamos dt a ~1.0
        
        self.timer += 0.05 * dt
        
        # Animación de escala usando SENO para suavidad (oscila entre 0.95 y 1.05)
        self.title_scale = 1.0 + math.sin(self.timer) * 0.05
        
        # Desplazamiento del fondo
        self.bg_scroll_x = (self.bg_scroll_x + self.bg_speed * dt) % 100
        self.bg_scroll_y = (self.bg_scroll_y + self.bg_speed * dt) % 100
    
    def render(self):
        self.screen.fill(BLACK)
        
        # 1. RENDERIZAR FONDO (Grid en movimiento)
        self._render_background_grid()
        
        # 2. RENDERIZAR TÍTULO
        title_text = "ProyectSurvivor"
        
        # Color cambiante sutil (Blanco a Cyan suave)
        r = 255
        g = int(255 - (math.sin(self.timer) + 1) * 20) # 215-255
        b = int(255 - (math.sin(self.timer) + 1) * 20)
        title_color = (r, g, b)

        # Escalado dinámico
        current_font_size = int(90 * self.title_scale)
        font_animated = pygame.font.Font(None, current_font_size)
        
        # Sombra del título (offset dinámico)
        shadow_offset = 4 + int(math.sin(self.timer) * 2)
        shadow = font_animated.render(title_text, True, (0, 100, 100)) # Sombra Cyan oscuro
        shadow_rect = shadow.get_rect(center=(WINDOW_WIDTH//2 + shadow_offset, 180 + shadow_offset))
        self.screen.blit(shadow, shadow_rect)
        
        # Texto principal
        title = font_animated.render(title_text, True, title_color)
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 180))
        self.screen.blit(title, title_rect)
        
        # Subtítulo
        subtitle = self.font_small.render("Sobrevive a la horda", True, (150, 150, 150))
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH//2, 240))
        self.screen.blit(subtitle, subtitle_rect)
        
        # 3. TEXTO DE INICIO (Parpadeo)
        # Usamos math.sin para un parpadeo más elegante que el módulo
        blink_alpha = int((math.sin(self.timer * 3) + 1) * 127.5) # 0 a 255
        
        start_text = self.font_normal.render("Presiona ESPACIO para comenzar", True, WHITE)
        start_rect = start_text.get_rect(center=(WINDOW_WIDTH//2, 350))
        
        # Crear superficie para transparencia
        start_surf = pygame.Surface(start_text.get_size(), pygame.SRCALPHA)
        start_surf.blit(start_text, (0, 0))
        
        # Opcional: Si quieres que nunca desaparezca del todo, limita el alpha mínimo
        final_alpha = max(50, blink_alpha)
        start_surf.set_alpha(final_alpha)
        
        self.screen.blit(start_surf, start_rect)
        
        # 4. CONTROLES (Panel visual)
        self._render_controls()

    def _render_background_grid(self):
        """Dibuja una cuadrícula que se mueve lentamente"""
        grid_size = 50
        color = (20, 20, 30) # Gris azulado muy oscuro
        
        # Líneas verticales
        for x in range(int(-grid_size), WINDOW_WIDTH + grid_size, grid_size):
            draw_x = x - int(self.bg_scroll_x)
            if 0 <= draw_x <= WINDOW_WIDTH:
                pygame.draw.line(self.screen, color, (draw_x, 0), (draw_x, WINDOW_HEIGHT))
                
        # Líneas horizontales
        for y in range(int(-grid_size), WINDOW_HEIGHT + grid_size, grid_size):
            draw_y = y - int(self.bg_scroll_y)
            if 0 <= draw_y <= WINDOW_HEIGHT:
                pygame.draw.line(self.screen, color, (0, draw_y), (WINDOW_WIDTH, draw_y))

    def _render_controls(self):
        """Renderiza la lista de controles en un recuadro limpio"""
        panel_y = 420
        panel_height = 150
        panel_width = 400
        panel_x = (WINDOW_WIDTH - panel_width) // 2
        
        # Fondo del panel (semi-transparente)
        s = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        s.fill((30, 30, 35, 150)) # Gris oscuro transparente
        self.screen.blit(s, (panel_x, panel_y))
        
        # Borde decorativo
        pygame.draw.rect(self.screen, (60, 60, 80), (panel_x, panel_y, panel_width, panel_height), 1)
        
        # Título Controles
        controls_title = self.font_small.render("- CONTROLES -", True, CYAN)
        rect = controls_title.get_rect(center=(WINDOW_WIDTH//2, panel_y + 20))
        self.screen.blit(controls_title, rect)
        
        controls = [
            ("WASD / Flechas", "Moverse"),
            ("Mouse", "Apuntar"),
            ("Click Izq", "Disparar"),
            ("1 - 4", "Cambiar Arma"),
            ("H", "Curarse")
        ]
        
        start_list_y = panel_y + 50
        for i, (key_text, action_text) in enumerate(controls):
            # Tecla (Izquierda, Color destacado)
            k_surf = self.font_small.render(key_text, True, (200, 200, 200))
            k_rect = k_surf.get_rect(right=WINDOW_WIDTH//2 - 10, top=start_list_y + i * 20)
            
            # Acción (Derecha, Gris)
            a_surf = self.font_small.render(action_text, True, (120, 120, 120))
            a_rect = a_surf.get_rect(left=WINDOW_WIDTH//2 + 10, top=start_list_y + i * 20)
            
            self.screen.blit(k_surf, k_rect)
            self.screen.blit(a_surf, a_rect)