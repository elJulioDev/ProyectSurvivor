"""
Clase principal del juego que maneja los estados
"""
import pygame
from settings import BLACK, WINDOW_WIDTH, WINDOW_HEIGHT
from entities.player import Player
from ui.hud import HUD

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = "MENU"  # Estados: MENU, PLAYING, GAME_OVER
        
        # Gameplay variables
        self.player = None
        self.hud = None
        self.wave = 1
        self.score = 0
        
    def _init_gameplay(self):
        """Inicializa las variables del gameplay"""
        # Crear jugador en el centro de la pantalla
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        self.hud = HUD(self.screen)
        self.wave = 1
        self.score = 0
        
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
                self._init_gameplay()
    
    def _handle_gameplay_events(self, event):
        # Pausar o volver al menú
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.state = "MENU"
    
    def _handle_gameover_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "MENU"
            elif event.key == pygame.K_r:
                self.state = "PLAYING"
                self._init_gameplay()
    
    def _update_gameplay(self):
        """Actualiza la lógica del juego"""
        if self.player and self.player.is_alive:
            # Obtener teclas presionadas
            keys = pygame.key.get_pressed()
            
            # Manejar input del jugador
            self.player.handle_input(keys)
            
            # Actualizar rotación hacia el mouse
            mouse_pos = pygame.mouse.get_pos()
            self.player.update_rotation(mouse_pos)
            
            # Actualizar jugador
            self.player.update()
        else:
            # Si el jugador murió, cambiar a game over
            if self.player and not self.player.is_alive:
                self.state = "GAME_OVER"
    
    def _render_menu(self):
        """Renderiza el menú principal"""
        font = pygame.font.Font(None, 74)
        text = font.render("ProyectSurvivor", True, (255, 255, 255))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, 200))
        self.screen.blit(text, text_rect)
        
        font_small = pygame.font.Font(None, 36)
        text_start = font_small.render("Presiona ESPACIO para jugar", True, (200, 200, 200))
        text_start_rect = text_start.get_rect(center=(self.screen.get_width()//2, 400))
        self.screen.blit(text_start, text_start_rect)
    
    def _render_gameplay(self):
        """Renderiza el gameplay"""
        # Renderizar jugador
        if self.player:
            self.player.render(self.screen)
        
        # Renderizar HUD
        if self.hud and self.player:
            self.hud.render(self.player, self.wave, self.score)
    
    def _render_gameover(self):
        """Renderiza la pantalla de game over"""
        font = pygame.font.Font(None, 74)
        text = font.render("Game Over", True, (255, 0, 0))
        text_rect = text.get_rect(center=(self.screen.get_width()//2, 250))
        self.screen.blit(text, text_rect)
        
        font_medium = pygame.font.Font(None, 48)
        score_text = font_medium.render(f"Puntuación: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(self.screen.get_width()//2, 330))
        self.screen.blit(score_text, score_rect)
        
        font_small = pygame.font.Font(None, 36)
        text_restart = font_small.render("R: Reintentar | ESPACIO: Menú", True, (200, 200, 200))
        text_restart_rect = text_restart.get_rect(center=(self.screen.get_width()//2, 420))
        self.screen.blit(text_restart, text_restart_rect)