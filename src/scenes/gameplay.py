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

        # Inicializar Cámara
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
    
    def on_enter(self):
        """Inicializa el gameplay"""
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.enemies = []
        self.projectiles = []
        self.particle_system.clear()
        self.wave_manager.start_wave()
        self.score = 0
        self.shoot_cooldown = 0
    
    def handle_events(self, event):
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
        
        # 1. Actualizar Jugador
        self.player.handle_input(keys)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update()
        
        # 2. Actualizar Cámara (AQUÍ ESTABA EL FALLO ANTERIOR)
        # Pasamos mouse_pos para que la cámara "mire" hacia donde apuntas
        self.camera.update(self.player, mouse_pos)
        
        # Actualizar armas
        for weapon in self.player.weapons:
            points_gained = 0
            if hasattr(weapon, 'render'): 
                 points_gained = weapon.update(self.enemies, particle_system=self.particle_system)
            else: 
                 weapon.update(self.enemies, self.projectiles)
            if points_gained > 0: self.score += points_gained
        
        # Actualizar proyectiles
        for projectile in self.projectiles[:]:
            projectile.update()
            # Optimización: Eliminar proyectiles muy lejos fuera de pantalla
            if not self.camera.is_on_screen(projectile.rect):
                # Opcional: solo eliminarlos si están MUY lejos (margen doble)
                # Por ahora dejamos que su lifetime los mate, o el límite del mundo.
                pass

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
            if not enemy.is_alive: self.enemies.remove(enemy)
            
        self.particle_system.update()
    
    def render(self):
        self.screen.fill(BLACK)

        self._render_grid()

        # --- RENDERIZADO OPTIMIZADO ---
        
        # 1. Armas Físicas (Orbital, Laser)
        for weapon in self.player.weapons:
             if hasattr(weapon, 'render'):
                 weapon.render(self.screen, self.camera)
        
        # 2. Partículas
        self.particle_system.render(self.screen, self.camera)
        
        # 3. Proyectiles (Solo si están en pantalla + margen)
        for projectile in self.projectiles:
            if self.camera.is_on_screen(projectile.rect):
                projectile.render(self.screen, self.camera)
        
        # 4. Enemigos (Solo si están en pantalla + margen)
        for enemy in self.enemies:
            # Usamos el nuevo método is_on_screen que ya incluye el margen seguro
            if self.camera.is_on_screen(enemy.rect):
                enemy.render(self.screen, self.camera)
        
        # 5. Jugador
        if self.player:
            self.player.render(self.screen, self.camera)
        
        # HUD
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))

        if self.wave_manager.is_wave_completed():
            self._render_wave_transition()

    def _render_grid(self):
        """Dibuja una cuadrícula ajustada a la cámara (Optimizada)"""
        grid_size = 100
        start_x = self.camera.offset_x % grid_size
        start_y = self.camera.offset_y % grid_size
        grid_color = (30, 30, 30)
        
        for x in range(start_x, WINDOW_WIDTH, grid_size):
            pygame.draw.line(self.screen, grid_color, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(start_y, WINDOW_HEIGHT, grid_size):
            pygame.draw.line(self.screen, grid_color, (0, y), (WINDOW_WIDTH, y))
            
        # Bordes del mundo
        line_x = self.camera.offset_x
        if 0 <= line_x <= WINDOW_WIDTH: # Izquierda
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH: # Derecha
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT: # Arriba
            pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT: # Abajo
             pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

    def _render_wave_transition(self):
        # ... (Igual que antes) ...
        progress = self.wave_manager.get_completion_progress()
        alpha = int(255 * (1 - abs(progress - 0.5) * 2))
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        font = pygame.font.Font(None, 64)
        text = font.render(f"Oleada {self.wave_manager.current_wave - 1} Completada!", True, (0, 255, 0, alpha))
        text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
        surf.blit(text, text_rect)
        self.screen.blit(surf, (0, 0))