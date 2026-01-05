"""
Escena principal del juego (gameplay)
"""
import pygame
from scenes.scene import Scene
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, DARK_GRAY, BLACK
from entities.player import Player
from entities.particle import ParticleSystem
from ui.hud import HUD
from utils.wave_manager import WaveManager
from utils.camera import Camera

class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        
        # Entidades
        self.player = None
        self.enemies = []
        self.projectiles = []
        self.particle_system = ParticleSystem()
        
        # Sistemas
        self.hud = HUD(self.screen)
        self.wave_manager = WaveManager()
        
        # Estadísticas
        self.score = 0
        
        # Control de disparo
        self.shoot_cooldown = 0
        self.shoot_delay = 15

        # Inicializar Cámara con tamaño del MUNDO
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
    
    def on_enter(self):
        """Inicializa el gameplay cuando se entra a la escena"""
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.enemies = []
        self.projectiles = []
        self.particle_system.clear()
        self.wave_manager.start_wave()
        self.score = 0
        self.shoot_cooldown = 0
    
    def handle_events(self, event):
        # Pasar eventos al jugador para detectar el Dash
        if self.player:
            self.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
    
    def update(self):
        if not self.player or not self.player.is_alive:
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(self.game, self.score, self.wave_manager.current_wave)
            return
        
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        
        # Actualizar jugador
        self.player.handle_input(keys)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update()
        self.camera.update(self.player)
        
        # Actualizar armas (y sumar puntos si matan enemigos directamente)
        for weapon in self.player.weapons:
            points_gained = 0
            if hasattr(weapon, 'render'): # Armas físicas (Orbital, Laser)
                 points_gained = weapon.update(self.enemies, particle_system=self.particle_system)
            else: # Armas de proyectiles (Varita, Escopeta)
                 weapon.update(self.enemies, self.projectiles)
            
            # Sumar puntos devueltos por armas directas
            if points_gained > 0:
                self.score += points_gained
        
        # Actualizar proyectiles y sumar puntos de ellos
        for projectile in self.projectiles[:]:
            projectile.update()
            hit_enemy = projectile.check_collision(self.enemies)
            
            if hit_enemy:
                hit_enemy.apply_knockback(projectile.x, projectile.y, force=8)
                self.particle_system.create_impact_particles(hit_enemy.x, hit_enemy.y, hit_enemy.color)
                
                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_death_particles(hit_enemy.x, hit_enemy.y, hit_enemy.color)
                    if hit_enemy in self.enemies:
                        self.enemies.remove(hit_enemy)
            
            if not projectile.is_alive:
                self.projectiles.remove(projectile)
        
        # Sistema de oleadas
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        # Actualizar enemigos
        for enemy in self.enemies[:]:
            enemy.move_towards_player(self.player.get_position())
            enemy.update()
            enemy.attack(self.player)
            
            if not enemy.is_alive:
                self.enemies.remove(enemy)
        
        # Actualizar partículas
        self.particle_system.update()
    
    def render(self):
        self.screen.fill(BLACK)

        # Para dar sensación de movimiento
        self._render_grid()

        # Armas (Orbital/Laser)
        for weapon in self.player.weapons:
             if hasattr(weapon, 'render'):
                 weapon.render(self.screen, self.camera) # Pasar cámara
        
        # Partículas
        self.particle_system.render(self.screen, self.camera)
        
        # Proyectiles
        for projectile in self.projectiles:
            projectile.render(self.screen, self.camera)
        
        # Enemigos (Optimización: Solo dibujar los que están en pantalla)
        for enemy in self.enemies:
            # Simple Culling: Si el rect en pantalla choca con la pantalla
            screen_rect = self.camera.apply_rect(enemy.rect)
            if screen_rect.colliderect(self.screen.get_rect()):
                enemy.render(self.screen, self.camera)
        
        # Jugador
        if self.player:
            self.player.render(self.screen, self.camera)
        
        # HUD (El HUD NO usa cámara, se dibuja fijo en pantalla)
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))

        # Mensaje de oleada completada
        if self.wave_manager.is_wave_completed():
            self._render_wave_transition()

    def _render_grid(self):
        """Dibuja una cuadrícula ajustada a la cámara"""
        grid_size = 100
        # Calcular inicio del grid basado en la cámara para efecto infinito
        start_x = self.camera.offset_x % grid_size
        start_y = self.camera.offset_y % grid_size
        
        # Color gris muy oscuro
        grid_color = (30, 30, 30)
        
        for x in range(start_x, WINDOW_WIDTH, grid_size):
            pygame.draw.line(self.screen, grid_color, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(start_y, WINDOW_HEIGHT, grid_size):
            pygame.draw.line(self.screen, grid_color, (0, y), (WINDOW_WIDTH, y))
            
        # Dibujar bordes del mundo (para saber dónde termina)
        # Borde Izquierdo
        line_x = self.camera.offset_x
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        # Borde Derecho
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        # Borde Superior
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

        # Borde Inferior
        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT:
             pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

    def _render_wave_transition(self):
        """Renderiza la transición entre oleadas"""
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