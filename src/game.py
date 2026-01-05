"""
Clase principal optimizada con efectos
"""
import pygame
from settings import BLACK, WINDOW_WIDTH, WINDOW_HEIGHT, WHITE
from entities.player import Player
from entities.particle import ParticleSystem
from ui.hud import HUD
from utils.wave_manager import WaveManager
import math

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.state = "MENU"
        
        # Gameplay
        self.player = None
        self.enemies = []
        self.projectiles = []
        self.particle_system = ParticleSystem()
        self.hud = None
        self.wave_manager = None
        self.score = 0
        
        # Control de disparo
        self.shoot_cooldown = 0
        self.shoot_delay = 15
        
    def _init_gameplay(self):
        """Inicializa gameplay"""
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        self.enemies = []
        self.projectiles = []
        self.particle_system.clear()
        self.hud = HUD(self.screen)
        self.wave_manager = WaveManager()
        self.wave_manager.start_wave()
        self.score = 0
        self.shoot_cooldown = 0
        
    def handle_events(self, event):
        if self.state == "MENU":
            self._handle_menu_events(event)
        elif self.state == "PLAYING":
            self._handle_gameplay_events(event)
        elif self.state == "GAME_OVER":
            self._handle_gameover_events(event)
    
    def update(self):
        if self.state == "PLAYING":
            self._update_gameplay()
    
    def render(self):
        self.screen.fill(BLACK)
        
        if self.state == "MENU":
            self._render_menu()
        elif self.state == "PLAYING":
            self._render_gameplay()
        elif self.state == "GAME_OVER":
            self._render_gameover()
    
    def _handle_menu_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.state = "PLAYING"
                self._init_gameplay()
    
    def _handle_gameplay_events(self, event):
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
        if not self.player or not self.player.is_alive:
            self.state = "GAME_OVER"
            return
        
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        # Jugador
        self.player.handle_input(keys)
        self.player.update_rotation(mouse_pos)
        self.player.update()
        
        # Disparo
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        if mouse_buttons[0] and self.shoot_cooldown == 0:
            projectile = self.player.shoot()
            self.projectiles.append(projectile)
            self.shoot_cooldown = self.shoot_delay
        
        # Proyectiles
        for projectile in self.projectiles[:]:
            projectile.update()
            
            hit_enemy = projectile.check_collision(self.enemies)
            if hit_enemy:
                # Aplicar retroceso CON LA POSICIÓN DEL PROYECTIL
                hit_enemy.apply_knockback(projectile.x, projectile.y, force=10)
                
                # Partículas de impacto
                self.particle_system.create_impact_particles(
                    hit_enemy.x, hit_enemy.y,
                    hit_enemy.color,
                    count=6
                )
                self.particle_system.create_blood_splatter(
                    hit_enemy.x, hit_enemy.y,
                    count=3
                )
                
                # Daño
                if hit_enemy.take_damage(projectile.damage):
                    # Muerte
                    self.score += hit_enemy.points
                    self.particle_system.create_death_particles(
                        hit_enemy.x, hit_enemy.y,
                        hit_enemy.color,
                        count=15
                    )
                    self.enemies.remove(hit_enemy)
            
            if not projectile.is_alive:
                self.projectiles.remove(projectile)
        
        # Oleadas (sin bloqueo)
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        # Enemigos
        for enemy in self.enemies[:]:
            enemy.move_towards_player(self.player.get_position())
            enemy.update()
            enemy.attack(self.player)
            
            if not enemy.is_alive:
                self.enemies.remove(enemy)
        
        # Partículas
        self.particle_system.update()
    
    def _render_menu(self):
        # Título con sombra
        font_title = pygame.font.Font(None, 84)
        title_text = "ProyectSurvivor"
        
        # Sombra
        shadow = font_title.render(title_text, True, (50, 50, 50))
        shadow_rect = shadow.get_rect(center=(WINDOW_WIDTH//2 + 3, 203))
        self.screen.blit(shadow, shadow_rect)
        
        # Título
        title = font_title.render(title_text, True, WHITE)
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 200))
        self.screen.blit(title, title_rect)
        
        # Instrucciones
        font_small = pygame.font.Font(None, 36)
        instructions = [
            "Presiona ESPACIO para comenzar",
            "",
            "WASD - Mover",
            "Mouse - Apuntar",
            "Click Izq - Disparar"
        ]
        
        y_start = 350
        for i, text in enumerate(instructions):
            if text:
                rendered = font_small.render(text, True, (200, 200, 200))
                rect = rendered.get_rect(center=(WINDOW_WIDTH//2, y_start + i * 35))
                self.screen.blit(rendered, rect)
    
    def _render_gameplay(self):
        # Partículas (atrás)
        self.particle_system.render(self.screen)
        
        # Proyectiles
        for projectile in self.projectiles:
            projectile.render(self.screen)
        
        # Enemigos
        for enemy in self.enemies:
            enemy.render(self.screen)
        
        # Jugador
        if self.player:
            self.player.render(self.screen)
        
        # HUD (actualizado con contador de enemigos)
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))
        
        # Transición de oleada (sin bloquear)
        if self.wave_manager.is_wave_completed():
            progress = self.wave_manager.get_completion_progress()
            alpha = int(255 * (1 - abs(progress - 0.5) * 2))
            surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            font = pygame.font.Font(None, 64)
            text = font.render(
                f"Oleada {self.wave_manager.current_wave - 1} Completada!",
                True,
                (0, 255, 0, alpha)
            )
            text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
            surf.blit(text, text_rect)
            self.screen.blit(surf, (0, 0))

    def _render_gameover(self):
        # Fondo semi-transparente
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Game Over con sombra
        font_big = pygame.font.Font(None, 84)
        
        shadow = font_big.render("GAME OVER", True, (100, 0, 0))
        shadow_rect = shadow.get_rect(center=(WINDOW_WIDTH//2 + 3, 203))
        self.screen.blit(shadow, shadow_rect)
        
        game_over = font_big.render("GAME OVER", True, (255, 0, 0))
        go_rect = game_over.get_rect(center=(WINDOW_WIDTH//2, 200))
        self.screen.blit(game_over, go_rect)
        
        # Stats
        font_medium = pygame.font.Font(None, 48)
        stats = [
            f"Puntuación: {self.score}",
            f"Oleada: {self.wave_manager.current_wave}",
            "",
            "R - Reintentar",
            "ESPACIO - Menú"
        ]
        
        y = 300
        for stat in stats:
            if stat:
                text = font_medium.render(stat, True, WHITE)
                rect = text.get_rect(center=(WINDOW_WIDTH//2, y))
                self.screen.blit(text, rect)
            y += 50