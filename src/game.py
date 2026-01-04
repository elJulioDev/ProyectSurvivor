"""
Clase principal del juego que maneja los estados
"""
import pygame
from settings import BLACK

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = "MENU"  # Estados: MENU, PLAYING, GAME_OVER
        
    def handle_events(self, event):
        """Maneja eventos según el estado actual"""
        if self.state == "MENU":
            self._handle_menu_events(event)
        elif self.state == "PLAYING":
            self._handle_gameplay_events(event)
        elif self.state == "GAME_OVER":
            self._handle_gameover_events(event)
    
    def update(self):
        """Actualiza la lógica según el estado actual"""
        if self.state == "PLAYING":
            self._update_gameplay()
    
    def render(self):
        """Renderiza la pantalla según el estado actual"""
        self.screen.fill(BLACK)
        
        if self.state == "MENU":
            self._render_menu()
        elif self.state == "PLAYING":
            self._render_gameplay()
        elif self.state == "GAME_OVER":
            self._render_gameover()
    
    # Métodos privados para cada estado
    def _handle_menu_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "PLAYING"
    
    def _handle_gameplay_events(self, event):
        pass
    
    def _handle_gameover_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "MENU"
    
    def _update_gameplay(self):
        pass
    
    def _render_menu(self):
        font = pygame.font.Font(None, 74)
        text = font.render("ProyectSurvivor", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, 200))
        self.screen.blit(text, text_rect)
        
        font_small = pygame.font.Font(None, 36)
        text_start = font_small.render("Presiona ESPACIO para jugar", True, (200, 200, 200))
        text_start_rect = text_start.get_rect(center=(self.screen.get_width()//2, 400))
        self.screen.blit(text_start, text_start_rect)
    
    def _render_gameplay(self):
        font = pygame.font.Font(None, 36)
        text = font.render("Jugando...", True, (255, 255, 255))
        self.screen.blit(text, (50, 50))
    
    def _render_gameover(self):
        font = pygame.font.Font(None, 74)
        text = font.render("Game Over", True, (255, 0, 0))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, 300))
        self.screen.blit(text, text_rect)