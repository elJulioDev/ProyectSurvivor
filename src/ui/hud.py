"""
HUD - Heads Up Display (Interfaz en pantalla)
"""
import pygame
from settings import WHITE, RED, GREEN, GRAY

class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
    
    def render(self, player, wave=1, score=0):
        """Renderiza el HUD con información del jugador"""
        # Barra de vida
        self._render_health_bar(player)
        
        # Información de oleada y puntuación
        self._render_wave_info(wave)
        self._render_score(score)
        
        # Controles (temporal)
        self._render_controls()
    
    def _render_health_bar(self, player):
        """Dibuja la barra de vida"""
        bar_width = 200
        bar_height = 20
        x = 20
        y = 20
        
        # Fondo de la barra
        pygame.draw.rect(self.screen, GRAY, (x, y, bar_width, bar_height))
        
        # Barra de vida actual
        health_width = (player.health / player.max_health) * bar_width
        health_color = GREEN if player.health > 50 else RED
        pygame.draw.rect(self.screen, health_color, (x, y, health_width, bar_height))
        
        # Borde
        pygame.draw.rect(self.screen, WHITE, (x, y, bar_width, bar_height), 2)
        
        # Texto de vida
        health_text = self.font_small.render(
            f"HP: {int(player.health)}/{player.max_health}",
            True,
            WHITE
        )
        self.screen.blit(health_text, (x + 5, y + 2))
    
    def _render_wave_info(self, wave):
        """Muestra la oleada actual"""
        wave_text = self.font.render(f"Oleada: {wave}", True, WHITE)
        self.screen.blit(wave_text, (20, 50))
    
    def _render_score(self, score):
        """Muestra la puntuación"""
        score_text = self.font.render(f"Puntos: {score}", True, WHITE)
        text_rect = score_text.get_rect(topright=(self.screen.get_width() - 20, 20))
        self.screen.blit(score_text, text_rect)
    
    def _render_controls(self):
        """Muestra los controles (temporal)"""
        controls = [
            "WASD / Flechas: Mover",
            "Mouse: Apuntar",
            "ESC: Menú"
        ]
        
        y_offset = self.screen.get_height() - 80
        for i, control in enumerate(controls):
            text = self.font_small.render(control, True, GRAY)
            self.screen.blit(text, (20, y_offset + i * 20))