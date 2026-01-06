"""
Escena de Gameplay con PAUSA y DEBUG corregido
"""
import pygame, math, random, sys
from scenes.scene import Scene
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT, BLACK, WHITE
from entities.player import Player
from entities.particle import ParticleSystem
from entities.weapon import LaserWeapon
from ui.hud import HUD
from ui.button import Button
from utils.wave_manager import WaveManager
from utils.camera import Camera
from utils.object_pool import ProjectilePool, ParticlePool
from utils.spatial_grid import SpatialGrid

class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        
        # POOLS OPTIMIZADOS
        self.projectile_pool = ProjectilePool(initial_size=500)
        self.particle_pool = ParticlePool(capacity=800)
        
        self.spatial_grid = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        
        self.player = None
        self.enemies = []
        self.particle_system = ParticleSystem()
        
        self.hud = HUD(self.screen)
        self.wave_manager = WaveManager()
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        
        self.score = 0
        
        self.clock = pygame.time.Clock()
        self.dt = 1.0
        self.target_fps = 60
        
        self.frame_counter = 0
        self.show_debug = False
        
        # Estado de Pausa y Botones
        self.paused = False
        self.font_pause = pygame.font.Font(None, 80)
        self.font_btn = pygame.font.Font(None, 36)
        
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.btn_continue = Button(cx, cy + 20, 200, 50, "Continuar", self.font_btn)
        self.btn_exit = Button(cx, cy + 90, 200, 50, "Salir del Juego", self.font_btn)

        self.particles_rendered = 0
        self.hit_particle_cooldown = 0
        self.blood_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        self.blood_surface.fill((0,0,0,0))

        # CONFIGURACIÓN DE BATCHING
        self.ai_update_interval = 4  # Actualizar IA cada 4 frames
        self.frame_counter = 0

        # Contador para mantener K presionada
        self.k_hold_counter = 0

    def on_enter(self):
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        self.enemies = []
        for weapon in self.player.weapons:
            weapon.set_projectile_pool(self.projectile_pool)
        self.particle_system.set_pool(self.particle_pool)
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.wave_manager.start_wave()
        self.score = 0
        self.dt = 1.0
        self.hit_particle_cooldown = 0
        self.paused = False
        self.blood_surface.fill((0,0,0,0))
    
    def handle_events(self, event):
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            if self.btn_continue.is_clicked(event):
                self.paused = False
            if self.btn_exit.is_clicked(event):
                pygame.quit()
                sys.exit()
        
        if self.player and not self.paused:
            self.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            elif event.key == pygame.K_RETURN: 
                self.paused = not self.paused
            elif event.key == pygame.K_F3:
                self.show_debug = not self.show_debug
    
    def update(self):
        raw_dt = self.clock.tick(self.target_fps) / (1000.0 / self.target_fps)
        self.dt = min(raw_dt, 3.0)
        
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            return 
        
        if not self.player or not self.player.is_alive:
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(self.game, self.score, self.wave_manager.current_wave)
            return
        
        enemy_count = len(self.enemies)
        if enemy_count < 50: self.particle_system.set_quality(2)
        elif enemy_count < 150: self.particle_system.set_quality(1)
        else: self.particle_system.set_quality(0)
        
        keys = pygame.key.get_pressed()
        mouse_pos = self.game.get_mouse_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        self.player.handle_input(keys, self.dt)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update(self.dt)
        if mouse_pressed[0]:
            self.player.attack()
        self.camera.update(self.player, mouse_pos)

        # Manejar mantener K presionada para subir oleadas rápidamente
        if keys[pygame.K_k]:
            self.k_hold_counter += 1
            if self.k_hold_counter >= 1:
                self.k_hold_counter = 0
                self.enemies.clear()
                self.spatial_grid.clear()
                self.projectile_pool.clear()
                self.wave_manager.current_wave += 1
                self.wave_manager.start_wave()
        
        # --- 1. SPATIAL GRID ---
        self.spatial_grid.clear()
        for enemy in self.enemies:
             if enemy.is_alive:
                 self.spatial_grid.insert(enemy)

        # --- 2. LOGICA DE ENEMIGOS UNIFICADA (BATCHING) ---
        player_pos = self.player.get_position()
        current_batch = self.frame_counter % self.ai_update_interval
        
        # Reconstruimos la lista para eliminar muertos eficientemente
        active_enemies = []

        for i, enemy in enumerate(self.enemies):
            if not enemy.is_alive: continue # Ignorar muertos (se limpiarán al final)

            # A. Batching AI (Lógica pesada)
            if i % self.ai_update_interval == current_batch:
                enemy.update_ai(player_pos, self.spatial_grid)
            
            # B. Física (Siempre)
            enemy.update_physics(self.dt)
            
            # C. Lógica varia (Sangre, Cooldowns)
            enemy.update(self.particle_system, self.dt)
            
            # D. Ataque (Simple distancia cuadrada)
            dist_sq = (enemy.x - self.player.x)**2 + (enemy.y - self.player.y)**2
            if dist_sq < 2500: # 50px radio
                 enemy.attack(self.player)

            # Si sigue vivo tras todo esto, lo conservamos
            if enemy.is_alive:
                active_enemies.append(enemy)
        
        # Asignamos la lista limpia
        self.enemies = active_enemies

        # --- ARMAS Y PROYECTILES ---
        if self.hit_particle_cooldown > 0:
            self.hit_particle_cooldown -= 1 * self.dt
        
        for weapon in self.player.weapons:
            weapon.update(dt=self.dt)
            if isinstance(weapon, LaserWeapon):
                if weapon.draw_timer >= weapon.duration - 1:
                    beam = weapon.get_beam_info()
                    if beam:
                        start, end = beam
                        # Copia para iterar seguro, aunque aquí el remove es menos crítico si usamos is_alive
                        for enemy in self.enemies:
                            if enemy.rect.clipline(start, end):
                                if enemy.take_damage(weapon.damage):
                                    self.score += enemy.points
                                    self.particle_system.create_viscera_explosion(enemy.x, enemy.y)
        
        for projectile in self.projectile_pool.active[:]:
            projectile.update(self.dt)
            hit_enemy = projectile.check_collision_grid(self.spatial_grid)
            
            if hit_enemy and hit_enemy.is_alive:
                hit_enemy.apply_knockback(projectile.x, projectile.y, force=8)
                
                if self.hit_particle_cooldown <= 0:
                    p_speed_sq = projectile.vel_x**2 + projectile.vel_y**2
                    direction = None
                    if p_speed_sq > 0.01:
                        inv_speed = 1.0 / math.sqrt(p_speed_sq)
                        direction = (projectile.vel_x * inv_speed, projectile.vel_y * inv_speed)
                    self.particle_system.create_blood_splatter(
                        hit_enemy.x, hit_enemy.y, direction_vector=direction, force=1.5, count=6
                    )
                    self.hit_particle_cooldown = 1 if self.particle_system.quality == 2 else 4

                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_viscera_explosion(hit_enemy.x, hit_enemy.y)
                    # No hacemos remove aquí, el bucle principal lo limpiará en el siguiente frame
                    
            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)
        
        # --- SPAWN DE OLEADAS ---
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        # --- RENDERIZADO DE PARTÍCULAS ---
        self.particle_pool.update_all(self.dt)
        self.particle_pool.bake_static_blood(self.blood_surface)
        
        self.frame_counter += 1
    
    def render(self):
        self.screen.fill(BLACK)
        self._render_grid()

        bg_x = max(0, int(-self.camera.offset_x))
        bg_y = max(0, int(-self.camera.offset_y))
        area_rect = pygame.Rect(bg_x, bg_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.screen.blit(self.blood_surface, (0, 0), area=area_rect)
        
        if self.player:
            for weapon in self.player.weapons:
                if hasattr(weapon, 'render'):
                    weapon.render(self.screen, self.camera)

        self.particles_rendered = self.particle_pool.render_all(self.screen, self.camera)
        
        for projectile in self.projectile_pool.active:
            if self.camera.is_on_screen(projectile.rect):
                projectile.render(self.screen, self.camera)
        
        enemies_rendered = 0
        for enemy in self.enemies:
            if self.camera.is_on_screen(enemy.rect):
                enemy.render(self.screen, self.camera)
                enemies_rendered += 1
        
        if self.player:
            self.player.render(self.screen, self.camera)
        
        if self.hud and self.player:
            self.hud.render(self.player, self.wave_manager.current_wave, self.score, len(self.enemies))

        if self.wave_manager.is_wave_completed():
            self._render_wave_transition()
        
        if self.paused:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            text = self.font_pause.render("PAUSA", True, WHITE)
            rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 80))
            self.screen.blit(text, rect)
            self.btn_continue.draw(self.screen)
            self.btn_exit.draw(self.screen)
        
        if self.show_debug:
            self._render_debug_info(enemies_rendered)

    def _render_grid(self):
        grid_size = 100
        start_x = self.camera.offset_x % grid_size
        start_y = self.camera.offset_y % grid_size
        grid_color = (30, 30, 30)
        
        for x in range(int(start_x), WINDOW_WIDTH, grid_size):
            pygame.draw.line(self.screen, grid_color, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(int(start_y), WINDOW_HEIGHT, grid_size):
            pygame.draw.line(self.screen, grid_color, (0, y), (WINDOW_WIDTH, y))
            
        line_x = self.camera.offset_x
        if 0 <= line_x <= WINDOW_WIDTH: pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH: pygame.draw.line(self.screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT: pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)
        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT: pygame.draw.line(self.screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)

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
        active_particles = sum(1 for p in self.particle_pool.pool if p.is_alive)
        debug_texts = [
            f"FPS: {fps:.1f} | DeltaTime: {dt_ms:.1f}ms",
            f"Enemigos: {len(self.enemies)} (Visibles: {enemies_rendered})",
            f"Proyectiles: {len(self.projectile_pool.active)}",
            f"Partículas: {active_particles} (Visibles: {self.particles_rendered}) / {self.particle_pool.capacity}",
            f"Pausa: {'SÍ' if self.paused else 'NO'}",
            "F3: Toggle Debug"
        ]
        y = 110 
        for text in debug_texts:
            surf = font.render(text, True, (0, 255, 0))
            self.screen.blit(font.render(text, True, (0, 0, 0)), (11, y + 1))
            self.screen.blit(surf, (10, y))
            y += 25