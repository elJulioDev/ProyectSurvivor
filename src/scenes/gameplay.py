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
        
        # ========== POOLS OPTIMIZADOS ==========
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
        
        # --- NUEVO: Estado de Pausa y Botones ---
        self.paused = False
        self.font_pause = pygame.font.Font(None, 80)
        self.font_btn = pygame.font.Font(None, 36)
        
        # Botones de pausa (Centrados)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.btn_continue = Button(cx, cy + 20, 200, 50, "Continuar", self.font_btn)
        self.btn_exit = Button(cx, cy + 90, 200, 50, "Salir del Juego", self.font_btn)

        self.particles_rendered = 0
        self.hit_particle_cooldown = 0
    
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
    
    def handle_events(self, event):
        # Si estamos pausados, gestionamos los botones
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            
            if self.btn_continue.is_clicked(event):
                self.paused = False
            
            if self.btn_exit.is_clicked(event):
                pygame.quit()
                sys.exit()

        # Si no estamos pausados, el jugador recibe inputs
        if self.player and not self.paused:
            self.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            
            # --- Alternar Pausa con ENTER ---
            elif event.key == pygame.K_RETURN: 
                self.paused = not self.paused
                
            elif event.key == pygame.K_F3:
                self.show_debug = not self.show_debug
    
    def update(self):
        # Calculamos dt siempre para mantener el reloj fluido
        raw_dt = self.clock.tick(self.target_fps) / (1000.0 / self.target_fps)
        self.dt = min(raw_dt, 3.0)
        
        # --- Lógica de Pausa ---
        if self.paused:
            # Actualizamos hover de botones aunque no haya eventos (para feedback visual constante)
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            return 
        # -----------------------------
        
        if not self.player or not self.player.is_alive:
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(self.game, self.score, self.wave_manager.current_wave)
            return
        
        # ========== CONTROL DE CALIDAD DINÁMICA ==========
        enemy_count = len(self.enemies)

        if enemy_count < 50:
            self.particle_system.set_quality(2)
        elif enemy_count < 150:
            self.particle_system.set_quality(1)
        else:
            self.particle_system.set_quality(0)
        
        keys = pygame.key.get_pressed()
        mouse_pos = self.game.get_mouse_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        self.player.handle_input(keys, self.dt)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update(self.dt)
        
        if mouse_pressed[0]:
            self.player.attack()

        self.camera.update(self.player, mouse_pos)
        
        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)
        
        if self.hit_particle_cooldown > 0:
            self.hit_particle_cooldown -= 1 * self.dt
        
        for weapon in self.player.weapons:
            weapon.update(dt=self.dt)

            if isinstance(weapon, LaserWeapon):
                if weapon.draw_timer >= weapon.duration - 1:
                    beam = weapon.get_beam_info()
                    if beam:
                        start, end = beam
                        for enemy in self.enemies[:]:
                            if enemy.rect.clipline(start, end):
                                if enemy.take_damage(weapon.damage):
                                    self.score += enemy.points
                                    self.particle_system.create_viscera_explosion(enemy.x, enemy.y)
                                    if enemy in self.enemies: 
                                        self.enemies.remove(enemy)
        
        # ========== PROYECTILES ==========
        for projectile in self.projectile_pool.active[:]:
            projectile.update(self.dt)
            
            hit_enemy = projectile.check_collision_grid(self.spatial_grid)
            
            if hit_enemy:
                hit_enemy.apply_knockback(projectile.x, projectile.y, force=8)
                
                if self.hit_particle_cooldown <= 0:
                    p_speed_sq = projectile.vel_x * projectile.vel_x + projectile.vel_y * projectile.vel_y
                    direction = None
                    if p_speed_sq > 0.01:
                        inv_speed = 1.0 / math.sqrt(p_speed_sq)
                        direction = (projectile.vel_x * inv_speed, projectile.vel_y * inv_speed)

                    self.particle_system.create_blood_splatter(
                        hit_enemy.x, hit_enemy.y, 
                        direction_vector=direction, 
                        force=1.2,
                        count=4
                    )
                    
                    if self.particle_system.quality == 2:
                        self.hit_particle_cooldown = 2
                    else:
                        self.hit_particle_cooldown = 5

                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_viscera_explosion(hit_enemy.x, hit_enemy.y)
                    if hit_enemy in self.enemies:
                        self.enemies.remove(hit_enemy)
            
            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)
        
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
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
        
        self.particle_pool.update_all(self.dt)
        
        self.frame_counter += 1
    
    def render(self):
        self.screen.fill(BLACK)
        self._render_grid()
        
        # --- PROTECCIÓN EXTRA ---
        # Solo intentamos dibujar el arma si el jugador existe
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
        
        # --- RENDERIZADO DE PAUSA ---
        if self.paused:
            # Capa oscura
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180)) # Negro semitransparente más oscuro
            self.screen.blit(overlay, (0, 0))
            
            # Texto
            text = self.font_pause.render("PAUSA", True, WHITE)
            rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 80))
            self.screen.blit(text, rect)
            
            # Botones
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