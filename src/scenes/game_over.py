"""
Escena de Game Over
"""
import pygame
from scenes.scene import Scene
from settings import BLACK, WHITE, WINDOW_WIDTH, WINDOW_HEIGHT

class GameOverScene(Scene):
    def __init__(self, game, final_score, final_wave):
        super().__init__(game)
        self.final_score = final_score
        self.final_wave = final_wave
        
        self.font_big = pygame.font.Font(None, 84)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        
        self.fade_alpha = 0
        self.fade_speed = 5
    
    def on_enter(self):
        """Reset de animación al entrar"""
        self.fade_alpha = 0
    
    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            elif event.key == pygame.K_r:
                from scenes.gameplay import GameplayScene
                self.next_scene = GameplayScene(self.game)
    
    def update(self):
        if self.fade_alpha < 255:
            self.fade_alpha = min(255, self.fade_alpha + self.fade_speed)
    
    def render(self):
        self.screen.fill(BLACK)
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, min(180, self.fade_alpha)))
        self.screen.blit(overlay, (0, 0))
        
        if self.fade_alpha < 100:
            return
        
        shadow = self.font_big.render("GAME OVER", True, (100, 0, 0))
        shadow_rect = shadow.get_rect(center=(WINDOW_WIDTH//2 + 3, 153))
        self.screen.blit(shadow, shadow_rect)
        
        game_over_text = self.font_big.render("GAME OVER", True, (255, 0, 0))
        go_rect = game_over_text.get_rect(center=(WINDOW_WIDTH//2, 150))
        self.screen.blit(game_over_text, go_rect)
        
        stats_y = 250
        
        # Puntuación
        score_label = self.font_small.render("Puntuación Final", True, (150, 150, 150))
        score_label_rect = score_label.get_rect(center=(WINDOW_WIDTH//2, stats_y))
        self.screen.blit(score_label, score_label_rect)
        
        score_text = self.font_medium.render(f"{self.final_score:,}", True, WHITE)
        score_rect = score_text.get_rect(center=(WINDOW_WIDTH//2, stats_y + 40))
        
        # Sombra del score
        score_shadow = self.font_medium.render(f"{self.final_score:,}", True, BLACK)
        shadow_rect = score_shadow.get_rect(center=(score_rect.centerx + 2, score_rect.centery + 2))
        self.screen.blit(score_shadow, shadow_rect)
        self.screen.blit(score_text, score_rect)
        
        # Oleada alcanzada
        wave_label = self.font_small.render("Oleada Alcanzada", True, (150, 150, 150))
        wave_label_rect = wave_label.get_rect(center=(WINDOW_WIDTH//2, stats_y + 90))
        self.screen.blit(wave_label, wave_label_rect)
        
        wave_text = self.font_medium.render(str(self.final_wave), True, (255, 200, 0))
        wave_rect = wave_text.get_rect(center=(WINDOW_WIDTH//2, stats_y + 130))
        
        # Sombra de la oleada
        wave_shadow = self.font_medium.render(str(self.final_wave), True, BLACK)
        shadow_rect = wave_shadow.get_rect(center=(wave_rect.centerx + 2, wave_rect.centery + 2))
        self.screen.blit(wave_shadow, shadow_rect)
        self.screen.blit(wave_text, wave_rect)
        
        # Opciones
        options_y = stats_y + 200
        
        restart_text = self.font_small.render("R - Reintentar", True, (200, 200, 200))
        restart_rect = restart_text.get_rect(center=(WINDOW_WIDTH//2, options_y))
        self.screen.blit(restart_text, restart_rect)
        
        menu_text = self.font_small.render("ESPACIO - Menú Principal", True, (200, 200, 200))
        menu_rect = menu_text.get_rect(center=(WINDOW_WIDTH//2, options_y + 40))
        self.screen.blit(menu_text, menu_rect)