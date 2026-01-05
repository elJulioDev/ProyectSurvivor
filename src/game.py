"""
Clase principal del juego que maneja los estados
"""
import pygame
from settings import BLACK, WINDOW_WIDTH, WINDOW_HEIGHT
from entities.player import Player
from ui.hud import HUD
from utils.wave_manager import WaveManager

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = "MENU"  # Estados: MENU, PLAYING, GAME_OVER
        
        # Gameplay variables
        self.player = None
        self.enemies = []
        self.projectiles = []
        self.hud = None
        self.wave_manager = None
        self.score = 0
        
        # Control de disparo
        self.shoot_cooldown = 0
        self.shoot_delay = 15  # frames entre disparos
        
    def _init_gameplay(self):
        """Inicializa las variables del gameplay"""
        # Crear jugador en el centro de la pantalla
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        self.enemies = []
        self.projectiles = []
        self.hud = HUD(self.screen)
        self.wave_manager = WaveManager()
        self.wave_manager.start_wave()
        self.score = 0
        self.shoot_cooldown = 0
        
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
        if not self.player or not self.player.is_alive:
            self.state = "GAME_OVER"
            return
        
        # Obtener teclas presionadas y posición del mouse
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        # Manejar input del jugador
        self.player.handle_input(keys)
        self.player.update_rotation(mouse_pos)
        self.player.update()
        
        # Disparar con clic izquierdo
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        if mouse_buttons[0] and self.shoot_cooldown == 0:  # Clic izquierdo
            projectile = self.player.shoot()
            self.projectiles.append(projectile)
            self.shoot_cooldown = self.shoot_delay
        
        # Actualizar proyectiles
        for projectile in self.projectiles[:]:
            projectile.update()
            
            # Verificar colisiones con enemigos
            hit_enemy = projectile.check_collision(self.enemies)
            if hit_enemy:
                if hit_enemy.take_damage(projectile.damage):
                    # Enemigo murió
                    self.score += 10
                    self.enemies.remove(hit_enemy)
            
            # Eliminar proyectiles muertos
            if not projectile.is_alive:
                self.projectiles.remove(projectile)
        
        # Actualizar sistema de oleadas
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        # Mostrar mensaje entre oleadas
        if self.wave_manager.is_wave_completed():
            pygame.time.wait(2000)  # Pausa de 2 segundos
            self.wave_manager.reset_wave_completion()
            self.wave_manager.start_wave()
        
        # Actualizar enemigos
        for enemy in self.enemies[:]:
            enemy.move_towards_player(self.player.get_position())
            enemy.update()
            
            # Verificar ataque al jugador
            enemy.attack(self.player)
            
            # Eliminar enemigos muertos
            if not enemy.is_alive:
                self.enemies.remove(enemy)
    
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
        # Renderizar proyectiles
        for projectile in self.projectiles:
            projectile.render(self.screen)
        
        # Renderizar enemigos
        for enemy in self.enemies:
            enemy.render(self.screen)
        
        # Renderizar jugador
        if self.player:
            self.player.render(self.screen)
        
        # Renderizar HUD
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score)
        
        # Mensaje entre oleadas
        if self.wave_manager.is_wave_completed():
            font = pygame.font.Font(None, 64)
            text = font.render(f"Oleada {self.wave_manager.current_wave} completada!", True, (0, 255, 0))
            text_rect = text.get_rect(center=(self.screen.get_width()//2, self.screen.get_height()//2))
            self.screen.blit(text, text_rect)
        
        # Contador de enemigos (debug)
        font_debug = pygame.font.Font(None, 24)
        enemies_text = font_debug.render(f"Enemigos: {len(self.enemies)}", True, (150, 150, 150))
        self.screen.blit(enemies_text, (self.screen.get_width() - 150, 50))
    
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
        
        wave_text = font_medium.render(f"Oleada alcanzada: {self.wave_manager.current_wave}", True, (255, 255, 255))
        wave_rect = wave_text.get_rect(center=(self.screen.get_width()//2, 380))
        self.screen.blit(wave_text, wave_rect)
        
        font_small = pygame.font.Font(None, 36)
        text_restart = font_small.render("R: Reintentar | ESPACIO: Menú", True, (200, 200, 200))
        text_restart_rect = text_restart.get_rect(center=(self.screen.get_width()//2, 480))
        self.screen.blit(text_restart, text_restart_rect)