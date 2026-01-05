"""
Escena principal del juego (gameplay)
"""
import pygame
from scenes.scene import Scene
from settings import BLACK, WINDOW_WIDTH, WINDOW_HEIGHT
from entities.player import Player
from entities.particle import ParticleSystem
from ui.hud import HUD
from utils.wave_manager import WaveManager

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
    
    def on_enter(self):
        """Inicializa el gameplay cuando se entra a la escena"""
        self.player = Player(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
        self.enemies = []
        self.projectiles = []
        self.particle_system.clear()
        self.wave_manager.start_wave()
        self.score = 0
        self.shoot_cooldown = 0
    
    def handle_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
    
    def update(self):
        # Verificar si el jugador murió
        if not self.player or not self.player.is_alive:
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(self.game, self.score, self.wave_manager.current_wave)
            return
        
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_buttons = pygame.mouse.get_pressed()
        
        # Actualizar jugador
        self.player.handle_input(keys)
        self.player.update_rotation(mouse_pos)
        self.player.update()
        
        # Sistema de disparo
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1
        
        if mouse_buttons[0] and self.shoot_cooldown == 0:
            projectile = self.player.shoot()
            self.projectiles.append(projectile)
            self.shoot_cooldown = self.shoot_delay
        
        # Actualizar proyectiles
        for projectile in self.projectiles[:]:
            projectile.update()
            
            hit_enemy = projectile.check_collision(self.enemies)
            if hit_enemy:
                # Aplicar retroceso
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
                
                # Aplicar daño
                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_death_particles(
                        hit_enemy.x, hit_enemy.y,
                        hit_enemy.color,
                        count=15
                    )
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
        
        # Renderizar en orden: partículas → proyectiles → enemigos → jugador → HUD
        self.particle_system.render(self.screen)
        
        for projectile in self.projectiles:
            projectile.render(self.screen)
        
        for enemy in self.enemies:
            enemy.render(self.screen)
        
        if self.player:
            self.player.render(self.screen)
        
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))
        
        # Mensaje de oleada completada
        if self.wave_manager.is_wave_completed():
            self._render_wave_transition()
    
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