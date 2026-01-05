"""
HUD - Heads Up Display mejorado y profesional
"""
import pygame
from settings import WHITE, RED, GREEN, GRAY, BLACK, YELLOW, CYAN

class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 32)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 24)
        self.font_tiny = pygame.font.Font(None, 20)
        
        # Animaciones
        self.score_display = 0
        self.score_lerp_speed = 0.15
        
    def render(self, player, wave=1, score=0, enemies_alive=0):
        """Renderiza el HUD completo"""
        # Actualizar animación de score
        self.score_display += (score - self.score_display) * self.score_lerp_speed
        
        # Panel superior izquierdo
        self._render_player_panel(player)
        
        # Panel superior derecho
        self._render_stats_panel(wave, int(self.score_display), enemies_alive)
        
    def _render_player_panel(self, player):
        """Panel de información del jugador"""
        panel_x = 15
        panel_y = 15
        panel_width = 250
        panel_height = 80
        
        # Fondo del panel con transparencia
        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (20, 20, 30, 200), (0, 0, panel_width, panel_height), border_radius=10)
        pygame.draw.rect(panel_surf, (60, 60, 80, 255), (0, 0, panel_width, panel_height), 2, border_radius=10)
        self.screen.blit(panel_surf, (panel_x, panel_y))
        
        # Título "SALUD"
        title = self.font_tiny.render("SALUD", True, (150, 150, 150))
        self.screen.blit(title, (panel_x + 10, panel_y + 8))
        
        # Barra de vida mejorada
        bar_x = panel_x + 10
        bar_y = panel_y + 32
        bar_width = panel_width - 20
        bar_height = 24
        
        # Calcular porcentaje de vida
        health_percent = player.health / player.max_health
        
        # Color de la barra según la vida
        if health_percent > 0.6:
            bar_color = (0, 200, 100)
            glow_color = (0, 255, 150, 100)
        elif health_percent > 0.3:
            bar_color = (255, 180, 0)
            glow_color = (255, 200, 50, 100)
        else:
            bar_color = (255, 50, 50)
            glow_color = (255, 100, 100, 100)
        
        # Fondo de la barra (oscuro)
        pygame.draw.rect(self.screen, (40, 40, 50), (bar_x, bar_y, bar_width, bar_height), border_radius=4)
        
        # Barra de vida con efecto de brillo
        health_width = int((bar_width - 4) * health_percent)
        if health_width > 0:
            # Brillo
            glow_surf = pygame.Surface((health_width + 8, bar_height + 8), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, glow_color, (0, 0, health_width + 8, bar_height + 8), border_radius=6)
            self.screen.blit(glow_surf, (bar_x - 2, bar_y - 2))
            
            # Barra principal
            pygame.draw.rect(self.screen, bar_color, (bar_x + 2, bar_y + 2, health_width, bar_height - 4), border_radius=3)
            
            # Highlight superior
            highlight_height = (bar_height - 4) // 3
            highlight_color = tuple(min(255, c + 40) for c in bar_color)
            pygame.draw.rect(self.screen, highlight_color, 
                           (bar_x + 2, bar_y + 2, health_width, highlight_height), border_radius=3)
        
        # Borde de la barra
        pygame.draw.rect(self.screen, (100, 100, 120), (bar_x, bar_y, bar_width, bar_height), 2, border_radius=4)
        
        # Texto de vida centrado
        health_text = self.font_medium.render(
            f"{int(player.health)} / {player.max_health}",
            True,
            WHITE
        )
        text_rect = health_text.get_rect(center=(bar_x + bar_width // 2, bar_y + bar_height // 2))
        
        # Sombra del texto
        shadow = self.font_medium.render(
            f"{int(player.health)} / {player.max_health}",
            True,
            BLACK
        )
        shadow_rect = shadow.get_rect(center=(text_rect.centerx + 1, text_rect.centery + 1))
        self.screen.blit(shadow, shadow_rect)
        self.screen.blit(health_text, text_rect)
        
        # Indicador de invulnerabilidad
        if player.invulnerable_frames > 0:
            shield_text = self.font_tiny.render("ESCUDO", True, CYAN)
            self.screen.blit(shield_text, (panel_x + 10, panel_y + 62))
            
            # Barra de invulnerabilidad
            shield_width = int((panel_width - 80) * (player.invulnerable_frames / 60))
            pygame.draw.rect(self.screen, CYAN, (panel_x + 65, panel_y + 65, shield_width, 6), border_radius=3)
            pygame.draw.rect(self.screen, (100, 200, 255), (panel_x + 65, panel_y + 65, panel_width - 80, 6), 1, border_radius=3)
    
    def _render_stats_panel(self, wave, score, enemies_alive):
        """Panel de estadísticas del juego"""
        panel_width = 220
        panel_height = 110
        panel_x = self.screen.get_width() - panel_width - 15
        panel_y = 15
        
        # Fondo del panel
        panel_surf = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (20, 20, 30, 200), (0, 0, panel_width, panel_height), border_radius=10)
        pygame.draw.rect(panel_surf, (60, 60, 80, 255), (0, 0, panel_width, panel_height), 2, border_radius=10)
        self.screen.blit(panel_surf, (panel_x, panel_y))
        
        # Oleada
        wave_label = self.font_tiny.render("OLEADA", True, (150, 150, 150))
        self.screen.blit(wave_label, (panel_x + 15, panel_y + 10))
        
        wave_text = self.font.render(str(wave), True, YELLOW)
        wave_rect = wave_text.get_rect(topright=(panel_x + panel_width - 15, panel_y + 8))
        
        # Sombra
        wave_shadow = self.font.render(str(wave), True, BLACK)
        shadow_rect = wave_shadow.get_rect(topright=(wave_rect.right + 1, wave_rect.top + 1))
        self.screen.blit(wave_shadow, shadow_rect)
        self.screen.blit(wave_text, wave_rect)
        
        # Línea separadora
        pygame.draw.line(self.screen, (60, 60, 80), 
                        (panel_x + 15, panel_y + 42), 
                        (panel_x + panel_width - 15, panel_y + 42), 2)
        
        # Puntuación
        score_label = self.font_tiny.render("PUNTOS", True, (150, 150, 150))
        self.screen.blit(score_label, (panel_x + 15, panel_y + 50))
        
        score_text = self.font_medium.render(f"{score:,}", True, WHITE)
        score_rect = score_text.get_rect(topright=(panel_x + panel_width - 15, panel_y + 48))
        
        # Sombra
        score_shadow = self.font_medium.render(f"{score:,}", True, BLACK)
        shadow_rect = score_shadow.get_rect(topright=(score_rect.right + 1, score_rect.top + 1))
        self.screen.blit(score_shadow, shadow_rect)
        self.screen.blit(score_text, score_rect)
        
        # Enemigos vivos
        enemies_label = self.font_tiny.render("ENEMIGOS", True, (150, 150, 150))
        self.screen.blit(enemies_label, (panel_x + 15, panel_y + 80))
        
        enemy_color = RED if enemies_alive > 10 else (255, 150, 0) if enemies_alive > 5 else (100, 255, 100)
        enemies_text = self.font_medium.render(str(enemies_alive), True, enemy_color)
        enemies_rect = enemies_text.get_rect(topright=(panel_x + panel_width - 15, panel_y + 78))
        
        # Sombra
        enemies_shadow = self.font_medium.render(str(enemies_alive), True, BLACK)
        shadow_rect = enemies_shadow.get_rect(topright=(enemies_rect.right + 1, enemies_rect.top + 1))
        self.screen.blit(enemies_shadow, shadow_rect)
        self.screen.blit(enemies_text, enemies_rect)