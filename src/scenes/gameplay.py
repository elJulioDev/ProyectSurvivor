"""
Escena de Gameplay COMPLETAMENTE OPTIMIZADA
- DeltaTime real (movimiento independiente de FPS)
- Object Pooling (proyectiles + partículas)
- Spatial Grid (colisiones O(1))
- Logic Culling (actualizar solo lo visible)
- Surface Caching (partículas pre-renderizadas)
- SISTEMA DE DISPARO MANUAL (Top-Down Shooter)
"""
import pygame
import math
import random
from scenes.scene import Scene
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, BLACK
from entities.player import Player
from entities.particle import ParticleSystem
from entities.weapon import LaserWeapon # Import necesario para lógica específica
from ui.hud import HUD
from utils.wave_manager import WaveManager
from utils.camera import Camera
from utils.object_pool import ProjectilePool, ParticlePool
from utils.spatial_grid import SpatialGrid

class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        
        # ========== OPTIMIZACIÓN: OBJECT POOLING ==========
        self.projectile_pool = ProjectilePool(initial_size=500)
        self.particle_pool = ParticlePool(initial_size=1000)
        
        # ========== OPTIMIZACIÓN: SPATIAL GRID ==========
        self.spatial_grid = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        
        # Entidades
        self.player = None
        self.enemies = []
        self.particle_system = ParticleSystem()
        
        # Sistemas
        self.hud = HUD(self.screen)
        self.wave_manager = WaveManager()
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        
        # Estadísticas
        self.score = 0
        
        # ========== DELTATIME ==========
        self.clock = pygame.time.Clock()
        self.dt = 1.0
        self.target_fps = 60
        
        # Métricas de rendimiento
        self.frame_counter = 0
        self.show_debug = False  # Cambiar a True para ver FPS
    
    def on_enter(self):
        """Inicializa el gameplay y conecta los pools"""
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.enemies = []
        
        # ========== CONECTAR POOLS A LAS ARMAS ==========
        for weapon in self.player.weapons:
            weapon.set_projectile_pool(self.projectile_pool)
        
        # ========== CONECTAR POOL AL SISTEMA DE PARTÍCULAS ==========
        self.particle_system.set_pool(self.particle_pool)
        
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.wave_manager.start_wave()
        self.score = 0
        self.dt = 1.0
    
    def handle_events(self, event):
        if self.player:
            self.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            elif event.key == pygame.K_F3:
                self.show_debug = not self.show_debug
    
    def update(self):
        # ========== CALCULAR DELTATIME ==========
        raw_dt = self.clock.tick(self.target_fps) / (1000.0 / self.target_fps)
        self.dt = min(raw_dt, 3.0)
        
        if not self.player or not self.player.is_alive:
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(self.game, self.score, self.wave_manager.current_wave)
            return
        
        keys = pygame.key.get_pressed()
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed() # Detectar clics del mouse
        
        # ========== ACTUALIZAR JUGADOR ==========
        self.player.handle_input(keys, self.dt)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update(self.dt)
        
        # ========== DISPARO MANUAL (CLIC IZQUIERDO) ==========
        if mouse_pressed[0]: # [0] es clic izquierdo
            self.player.attack()

        # ========== ACTUALIZAR CÁMARA ==========
        self.camera.update(self.player, mouse_pos)
        
        # ========== REPOBLAR SPATIAL GRID (Cada frame) ==========
        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)
        
        # ========== ACTUALIZAR ARMAS Y LÓGICA DE DAÑO ==========
        for weapon in self.player.weapons:
            # Actualizar Cooldowns (y rotación orbital)
            weapon.update(dt=self.dt)

            # CASO ESPECIAL: Láser (Hitscan instantáneo)
            if isinstance(weapon, LaserWeapon):
                # Si el láser acaba de dispararse (draw_timer alto)
                if weapon.draw_timer >= weapon.duration - 1:
                    beam = weapon.get_beam_info()
                    if beam:
                        start, end = beam
                        # Verificar colisión con todos los enemigos (Hitscan)
                        # Se podría optimizar con raycast en grid, pero iterar es rápido para <500 enemigos
                        for enemy in self.enemies[:]:
                            if enemy.rect.clipline(start, end):
                                self.particle_system.create_blood_splatter(enemy.x, enemy.y, count=5)
                                if enemy.take_damage(weapon.damage):
                                    self.score += enemy.points
                                    self.particle_system.create_viscera_explosion(enemy.x, enemy.y)
                                    if enemy in self.enemies: self.enemies.remove(enemy)

        
        # ========== ACTUALIZAR PROYECTILES (POOL) ==========
        # Wand y Shotgun usan proyectiles físicos
        for projectile in self.projectile_pool.active[:]:
            projectile.update(self.dt)
            
            # Colisiones con Grid Espacial
            hit_enemy = projectile.check_collision_grid(self.spatial_grid)
            
            if hit_enemy:
                hit_enemy.apply_knockback(projectile.x, projectile.y, force=8)
                
                # Dirección del impacto para la sangre
                p_speed_sq = projectile.vel_x * projectile.vel_x + projectile.vel_y * projectile.vel_y
                direction = None
                if p_speed_sq > 0.01:
                    inv_speed = 1.0 / math.sqrt(p_speed_sq)
                    direction = (projectile.vel_x * inv_speed, projectile.vel_y * inv_speed)

                self.particle_system.create_blood_splatter(
                    hit_enemy.x, hit_enemy.y, 
                    direction_vector=direction, 
                    force=1.5
                )
                
                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_viscera_explosion(hit_enemy.x, hit_enemy.y)
                    if hit_enemy in self.enemies:
                        self.enemies.remove(hit_enemy)
            
            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)
        
        # ========== SISTEMA DE OLEADAS ==========
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        # ========== ACTUALIZAR ENEMIGOS (CON LOGIC CULLING) ==========
        viewport_margin = 200
        
        for enemy in self.enemies[:]:
            dist_sq_to_player = enemy.get_distance_squared_to(self.player.x, self.player.y)
            max_update_dist_sq = (WINDOW_WIDTH + viewport_margin) ** 2
            
            if dist_sq_to_player > max_update_dist_sq:
                enemy.move_towards_player(self.player.get_position(), self.dt)
            else:
                enemy.move_towards_player(self.player.get_position(), self.dt)
                enemy.update(self.particle_system, self.dt)
                enemy.attack(self.player)
            
            if not enemy.is_alive:
                self.enemies.remove(enemy)
        
        # ========== ACTUALIZAR PARTÍCULAS (POOL) ==========
        self.particle_pool.update_all(self.dt)
        
        self.frame_counter += 1
    
    def render(self):
        self.screen.fill(BLACK)

        self._render_grid()

        # ========== RENDERIZADO OPTIMIZADO (Con Culling) ==========
        
        # 1. Armas Físicas y Láser
        for weapon in self.player.weapons:
            if hasattr(weapon, 'render'):
                weapon.render(self.screen, self.camera)
        
        # 2. Partículas
        self.particle_pool.render_all(self.screen, self.camera)
        
        # 3. Proyectiles
        for projectile in self.projectile_pool.active:
            if self.camera.is_on_screen(projectile.rect):
                projectile.render(self.screen, self.camera)
        
        # 4. Enemigos
        enemies_rendered = 0
        for enemy in self.enemies:
            if self.camera.is_on_screen(enemy.rect):
                enemy.render(self.screen, self.camera)
                enemies_rendered += 1
        
        # 5. Jugador
        if self.player:
            self.player.render(self.screen, self.camera)
        
        # HUD
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))

        if self.wave_manager.is_wave_completed():
            self._render_wave_transition()
        
        # DEBUG
        if self.show_debug:
            self._render_debug_info(enemies_rendered)

    def _render_grid(self):
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
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
            
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

    def _render_wave_transition(self):
        progress = self.wave_manager.get_completion_progress()
        alpha = int(255 * (1 - abs(progress - 0.5) * 2))
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        font = pygame.font.Font(None, 64)
        text = font.render(f"Oleada {self.wave_manager.current_wave - 1} Completada!", True, (0, 255, 0, alpha))
        text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
        surf.blit(text, text_rect)
        self.screen.blit(surf, (0, 0))
    
    def _render_debug_info(self, enemies_rendered):
        font = pygame.font.Font(None, 24)
        fps = self.clock.get_fps()
        dt_ms = self.dt * (1000.0 / self.target_fps)
        
        debug_texts = [
            f"FPS: {fps:.1f} | DeltaTime: {dt_ms:.1f}ms",
            f"Enemigos: {len(self.enemies)} (Renderizados: {enemies_rendered})",
            f"Proyectiles: {len(self.projectile_pool.active)}",
            f"Partículas: {len(self.particle_pool.active)}",
            f"Puntuación: {self.score}",
            "F3: Toggle Debug"
        ]
        
        y = 10
        for text in debug_texts:
            surf = font.render(text, True, (0, 255, 0))
            self.screen.blit(font.render(text, True, (0, 0, 0)), (11, y + 1))
            self.screen.blit(surf, (10, y))
            y += 25