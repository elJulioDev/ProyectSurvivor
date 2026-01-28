"""
Level Manager - Encapsula toda la lógica de simulación del gameplay
Separa la lógica del juego de la presentación (Scene)
"""
import pygame, math
from settings import WORLD_WIDTH, WORLD_HEIGHT
from entities.player import Player
from entities.particle import ParticleSystem
from entities.weapon import LaserWeapon
from utils.wave_manager import WaveManager
from utils.camera import Camera
from utils.object_pool import ProjectilePool, ParticlePool
from utils.spatial_grid import SpatialGrid

class LevelManager:
    """
    Gestiona toda la lógica del nivel:
    - Entidades (Player, Enemies)
    - Sistemas (Particles, Weapons, Collisions)
    - Estado del juego (Score, Wave)
    """
    
    def __init__(self):
        self.projectile_pool = ProjectilePool(initial_size=500)
        self.particle_pool = ParticlePool(capacity=800)
        self.spatial_grid = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        self.particle_system = ParticleSystem()
        self.wave_manager = WaveManager()
        self.camera = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.player = None
        self.enemies = []
        self.score = 0
        self.game_over = False
        self.blood_surface = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        self.blood_surface.fill((0, 0, 0, 0))
        self.ai_update_interval = 4
        self.frame_counter = 0
        self.hit_particle_cooldown = 0
        self.particles_rendered = 0
        self.enemies_rendered = 0
        
    def initialize(self):
        """Inicializa o reinicia el nivel"""

        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        
        for weapon in self.player.weapons:
            weapon.set_projectile_pool(self.projectile_pool)
        
        self.particle_system.set_pool(self.particle_pool)
        self.enemies.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.blood_surface.fill((0, 0, 0, 0))
        self.score = 0
        self.game_over = False
        self.wave_manager.reset()
        self.wave_manager.start_wave()
        self.hit_particle_cooldown = 0
        self.frame_counter = 0
        
    def update(self, dt, keys, mouse_pos, mouse_pressed):
        """
        Actualiza toda la lógica del nivel
        
        Args:
            dt: Delta time
            keys: pygame.key.get_pressed()
            mouse_pos: Posición virtual del mouse
            mouse_pressed: pygame.mouse.get_pressed()
        """
        if self.game_over or not self.player or not self.player.is_alive:
            self.game_over = True
            return
        
        enemy_count = len(self.enemies)
        if enemy_count < 50:
            self.particle_system.set_quality(2)
        elif enemy_count < 150:
            self.particle_system.set_quality(1)
        else:
            self.particle_system.set_quality(0)
        
        self.player.handle_input(keys, dt)
        self.player.update_rotation(mouse_pos, (self.camera.offset_x, self.camera.offset_y))
        self.player.update(dt)
        
        if mouse_pressed[0]:
            self.player.attack(self.camera)
        
        self.camera.update(self.player, mouse_pos)
        
        if keys[pygame.K_k]:
            self.enemies.clear()
            self.spatial_grid.clear()
            self.projectile_pool.clear()
            self.wave_manager.current_wave += 1
            self.wave_manager.start_wave()
        
        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)
        
        self._update_enemies(dt)
        self._update_weapons(dt)
        self._update_projectiles(dt)
        
        new_enemy = self.wave_manager.update(self.enemies)
        if new_enemy:
            self.enemies.append(new_enemy)
        
        self.particle_pool.update_all(dt)
        self.particle_pool.bake_static_blood(self.blood_surface)
        
        self.frame_counter += 1
    
    def _update_enemies(self, dt):
        """Actualiza todos los enemigos con batching de IA"""
        player_pos = self.player.get_position()

        # Ajuste dinámico del batching
        enemy_count = len(self.enemies)
        if enemy_count > 800:
            self.ai_update_interval = 8
        elif enemy_count > 400:
            self.ai_update_interval = 6
        else:
            self.ai_update_interval = 4

        current_batch = self.frame_counter % self.ai_update_interval
        
        active_enemies = []
        
        for i, enemy in enumerate(self.enemies):
            if not enemy.is_alive:
                continue
            
            if i % self.ai_update_interval == current_batch:
                enemy.update_ai(player_pos, self.spatial_grid)
            
            enemy.update_physics(dt)
            enemy.update(self.particle_system, dt)
            
            dist_sq = (enemy.x - self.player.x)**2 + (enemy.y - self.player.y)**2
            if dist_sq < 2500:
                enemy.attack(self.player)
            
            if enemy.is_alive:
                active_enemies.append(enemy)
        
        self.enemies = active_enemies
    
    def _update_weapons(self, dt):
        """Actualiza todas las armas del jugador"""
        if self.hit_particle_cooldown > 0:
            self.hit_particle_cooldown -= 1 * dt
        
        for weapon in self.player.weapons:
            weapon.update(dt=dt)
            
            if isinstance(weapon, LaserWeapon):
                if weapon.draw_timer > 0:  # Mientras esté activo
                    # Aplicar daño cada frame, pero ajustado por dt
                    beam = weapon.get_beam_info()
                    if beam:
                        start, end = beam
                        laser_damage_per_second = weapon.damage * 6  # 60 FPS base
                        damage_this_frame = laser_damage_per_second * (dt / 60.0)
                        
                        for enemy in self.enemies:
                            if enemy.rect.clipline(start, end):
                                if enemy.take_damage(damage_this_frame):
                                    self.score += enemy.points
                                    self.particle_system.create_viscera_explosion(enemy.x, enemy.y)
    
    def _update_projectiles(self, dt):
        """Actualiza proyectiles y detecta colisiones"""
        for projectile in self.projectile_pool.active[:]:
            projectile.update(dt)
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
                        hit_enemy.x, hit_enemy.y,
                        direction_vector=direction,
                        force=1.5,
                        count=6
                    )
                    self.hit_particle_cooldown = 1 if self.particle_system.quality == 2 else 4
                
                if hit_enemy.take_damage(projectile.damage):
                    self.score += hit_enemy.points
                    self.particle_system.create_viscera_explosion(hit_enemy.x, hit_enemy.y)
            
            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)
    
    def render_world(self, screen):
        """
        Renderiza el mundo del juego (sin UI)
        
        Args:
            screen: Superficie de pygame donde renderizar
        """
        self._render_grid(screen)
        
        bg_x = max(0, int(-self.camera.offset_x))
        bg_y = max(0, int(-self.camera.offset_y))
        from settings import WINDOW_WIDTH, WINDOW_HEIGHT
        area_rect = pygame.Rect(bg_x, bg_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        screen.blit(self.blood_surface, (0, 0), area=area_rect)
        
        rendered_floor = self.particle_pool.render_all(screen, self.camera, layer='floor')
        
        for projectile in self.projectile_pool.active:
            if self.camera.is_on_screen(projectile.rect):
                projectile.render(screen, self.camera)
        
        self.enemies_rendered = 0
        render_margin = 200
        
        for enemy in self.enemies:
            expanded_rect = enemy.rect.inflate(render_margin * 2, render_margin * 2)
            if self.camera.is_on_screen(expanded_rect):
                enemy.render(screen, self.camera)
                self.enemies_rendered += 1
        
        if self.player:
            for weapon in self.player.weapons:
                if hasattr(weapon, 'render'):
                    weapon.render(screen, self.camera)
        
        if self.player:
            self.player.render(screen, self.camera)

        rendered_air = self.particle_pool.render_all(screen, self.camera, layer='air')
        self.particles_rendered = rendered_floor + rendered_air
    
    def _render_grid(self, screen):
        """Renderiza el grid de fondo"""
        from settings import WINDOW_WIDTH, WINDOW_HEIGHT
        
        grid_size = 100
        start_x = self.camera.offset_x % grid_size
        start_y = self.camera.offset_y % grid_size
        grid_color = (30, 30, 30)
        
        for x in range(int(start_x), WINDOW_WIDTH, grid_size):
            pygame.draw.line(screen, grid_color, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(int(start_y), WINDOW_HEIGHT, grid_size):
            pygame.draw.line(screen, grid_color, (0, y), (WINDOW_WIDTH, y))
        
        line_x = self.camera.offset_x
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(screen, (100, 0, 0), (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)
        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(screen, (100, 0, 0), (0, line_y), (WINDOW_WIDTH, line_y), 2)
    
    def get_debug_info(self):
        """Retorna información para el debug overlay"""
        active_particles = sum(1 for p in self.particle_pool.pool if p.is_alive)
        return {
            'enemies_total': len(self.enemies),
            'enemies_rendered': self.enemies_rendered,
            'projectiles': len(self.projectile_pool.active),
            'particles_active': active_particles,
            'particles_rendered': self.particles_rendered,
            'particles_capacity': self.particle_pool.capacity,
        }
    
    def cleanup(self):
        """Limpia recursos al salir del nivel"""
        self.enemies.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.spatial_grid.clear()