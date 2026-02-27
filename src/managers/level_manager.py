"""
LevelManager con:
  - Pipeline de reciclaje de enemigos muertos (estilo Vampire Survivors)
  - Fusión periódica de gemas de XP cercanas en una sola gema de mayor valor
  - Spawn de enemigos relativo a la cámara
  - Puntuación multiplicada x100 para que sea proporcional al esfuerzo
"""
import pygame, math
from settings import WORLD_WIDTH, WORLD_HEIGHT
from entities.player import Player
from entities.particle import ParticleSystem
from entities.weapon import LaserWeapon
from utils.camera import Camera
from utils.object_pool import ProjectilePool, ParticlePool
from utils.spatial_grid import SpatialGrid
from managers.spawn_manager import SpawnManager
from entities.experience_gem import ExperienceGem


# ── Parámetros de fusión de gemas ────────────────────────────────────────────
GEM_MERGE_INTERVAL   = 120   # Frames entre cada pasada de fusión
GEM_MERGE_RADIUS     = 55    # Px: radio de búsqueda de gemas vecinas
GEM_MERGE_MIN_COUNT  = 3     # Mínimo de gemas en el grupo para fusionar

# ── Parámetros de teletransporte de enemigos ─────────────────────────────────
ENEMY_TELEPORT_INTERVAL = 90  # Frames entre revisiones de distancia

# ── Multiplicador de puntuación ───────────────────────────────────────────────
SCORE_MULTIPLIER = 100  # Hace la puntuación más satisfactoria y legible


class LevelManager:
    """
    Gestiona toda la lógica del nivel:
    - Entidades (Player, Enemies)
    - Sistemas (Particles, Weapons, Collisions)
    - Estado del juego (Score, Wave)
    - Reciclaje de enemigos muertos
    - Fusión de gemas de XP cercanas
    """
    
    def __init__(self):
        self.projectile_pool  = ProjectilePool(initial_size=500)
        self.particle_pool    = ParticlePool(capacity=800)
        self.spatial_grid     = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        self.particle_system  = ParticleSystem()
        self.spawn_manager    = SpawnManager()
        self.gems: list[ExperienceGem] = []
        self.camera           = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.player           = None
        self.enemies: list    = []        # Solo enemigos VIVOS
        self.score            = 0
        self.game_over        = False
        self.blood_surface    = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
        self.blood_surface.fill((0, 0, 0, 0))

        self.ai_update_interval   = 4
        self.frame_counter        = 0
        self.hit_particle_cooldown = 0
        self.particles_rendered   = 0
        self.enemies_rendered     = 0

        # Contadores de ciclos secundarios
        self._gem_merge_timer      = 0
        self._teleport_timer       = 0
        
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
        self.score            = 0
        self.game_over        = False
        self.gems.clear()
        self.spawn_manager    = SpawnManager()
        self.hit_particle_cooldown = 0
        self.frame_counter    = 0
        self._gem_merge_timer = 0
        self._teleport_timer  = 0
        
    # ── Update principal ─────────────────────────────────────────────────────

    def update(self, dt, keys, mouse_pos, mouse_pressed):
        if self.game_over or not self.player or not self.player.is_alive:
            self.game_over = True
            return
        
        # Calidad de partículas según carga
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
        cam_offset = (self.camera.offset_x, self.camera.offset_y)

        # Spatial grid
        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)
        
        self._update_enemies(dt)
        self._update_weapons(dt)
        self._update_projectiles(dt)
        
        # ── Spawn / reciclaje ─────────────────────────────────────────
        new_enemy = self.spawn_manager.update(dt, len(self.enemies), cam_offset)
        if new_enemy:
            self.enemies.append(new_enemy)

        # ── Teletransporte periódico de enemigos lejanos ──────────────
        self._teleport_timer += dt
        if self._teleport_timer >= ENEMY_TELEPORT_INTERVAL:
            self._teleport_timer = 0
            self.spawn_manager.try_teleport_distant_enemies(self.enemies, cam_offset)

        # ── Gemas de XP ───────────────────────────────────────────────
        for i in range(len(self.gems) - 1, -1, -1):
            gem = self.gems[i]
            gem.update(self.player.get_position(), dt)
            if self.player.rect.colliderect(gem.rect):
                self.player.gain_experience(gem.xp_value)
                self.gems.pop(i)

        # ── Fusión periódica de gemas ─────────────────────────────────
        self._gem_merge_timer += dt
        if self._gem_merge_timer >= GEM_MERGE_INTERVAL:
            self._gem_merge_timer = 0
            self._merge_nearby_gems()
        
        self.particle_pool.update_all(dt)
        self.particle_pool.bake_static_blood(self.blood_surface)
        
        self.frame_counter += 1
    
    # ── Actualización de entidades ────────────────────────────────────────────

    def _update_enemies(self, dt):
        """Actualiza enemigos con batching de IA y recicla los muertos."""
        player_pos = self.player.get_position()

        # Batching dinámico
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
                # ── Reciclar en lugar de eliminar ──────────────────────
                self.spawn_manager.add_to_dead_pool(enemy)
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
            else:
                # Murió durante este frame → reciclar también
                self.spawn_manager.add_to_dead_pool(enemy)
        
        self.enemies = active_enemies
    
    def _update_weapons(self, dt):
        if self.hit_particle_cooldown > 0:
            self.hit_particle_cooldown -= 1 * dt
        
        for weapon in self.player.weapons:
            weapon.update(dt=dt)
            
            if isinstance(weapon, LaserWeapon):
                if weapon.draw_timer > 0:
                    beam = weapon.get_beam_info()
                    if beam:
                        start, end = beam
                        laser_damage_per_second = weapon.damage * 6
                        damage_this_frame = laser_damage_per_second * (dt / 60.0)
                        
                        for enemy in self.enemies:
                            if enemy.rect.clipline(start, end):
                                if enemy.take_damage(damage_this_frame):
                                    # Puntuación con multiplicador
                                    self.score += enemy.points * SCORE_MULTIPLIER
                                    self.particle_system.create_viscera_explosion(enemy.x, enemy.y)
                                    gem = ExperienceGem(enemy.x, enemy.y, enemy.points)
                                    self.gems.append(gem)
    
    def _update_projectiles(self, dt):
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
                        direction_vector=direction, force=1.5, count=6
                    )
                    self.hit_particle_cooldown = 1 if self.particle_system.quality == 2 else 4
                
                if hit_enemy.take_damage(projectile.damage):
                    # Puntuación con multiplicador
                    self.score += hit_enemy.points * SCORE_MULTIPLIER
                    self.particle_system.create_viscera_explosion(hit_enemy.x, hit_enemy.y)
                    gem = ExperienceGem(hit_enemy.x, hit_enemy.y, hit_enemy.points)
                    self.gems.append(gem)
            
            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)

    # ── Fusión de gemas de XP ─────────────────────────────────────────────────

    def _merge_nearby_gems(self):
        """
        Agrupa gemas que estén dentro de GEM_MERGE_RADIUS entre sí.
        Si un grupo tiene GEM_MERGE_MIN_COUNT o más gemas, las fusiona en una sola
        con la XP total, posicionada en el centroide del grupo.

        Las gemas magnetizadas (ya en camino al jugador) no se fusionan para evitar
        que desaparezcan de forma brusca.
        """
        if len(self.gems) < GEM_MERGE_MIN_COUNT:
            return

        radius_sq = GEM_MERGE_RADIUS * GEM_MERGE_RADIUS
        visited   = [False] * len(self.gems)
        new_gems: list[ExperienceGem] = []

        for i, gem_a in enumerate(self.gems):
            if visited[i]:
                continue

            # Gemas magnetizadas se pasan directamente sin agrupar
            if gem_a.is_magnetized or gem_a.z > 0:
                visited[i] = True
                new_gems.append(gem_a)
                continue

            group = [i]

            for j in range(i + 1, len(self.gems)):
                if visited[j]:
                    continue
                gem_b = self.gems[j]
                if gem_b.is_magnetized or gem_b.z > 0:
                    continue
                dx = gem_a.x - gem_b.x
                dy = gem_a.y - gem_b.y
                if dx * dx + dy * dy <= radius_sq:
                    group.append(j)

            if len(group) >= GEM_MERGE_MIN_COUNT:
                # ── Fusionar grupo ────────────────────────────────────
                total_xp = sum(self.gems[idx].xp_value for idx in group)
                cx = sum(self.gems[idx].x for idx in group) / len(group)
                cy = sum(self.gems[idx].y for idx in group) / len(group)

                merged = ExperienceGem(cx, cy, total_xp)
                # La gema fusionada aparece directamente sin animación de caída
                merged.z  = 0
                merged.vz = 0
                merged.vx = 0
                merged.vy = 0

                new_gems.append(merged)
                for idx in group:
                    visited[idx] = True
            else:
                # Grupo demasiado pequeño → conservar las gemas individuales
                for idx in group:
                    if not visited[idx]:
                        new_gems.append(self.gems[idx])
                        visited[idx] = True

        # Añadir las que no se visitaron (edge case)
        for i, gem in enumerate(self.gems):
            if not visited[i]:
                new_gems.append(gem)

        self.gems = new_gems

    # ── Renderizado ───────────────────────────────────────────────────────────

    def render_world(self, screen):
        self._render_grid(screen)
        
        bg_x = max(0, int(-self.camera.offset_x))
        bg_y = max(0, int(-self.camera.offset_y))
        from settings import WINDOW_WIDTH, WINDOW_HEIGHT
        area_rect = pygame.Rect(bg_x, bg_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        screen.blit(self.blood_surface, (0, 0), area=area_rect)
        
        rendered_floor = self.particle_pool.render_all(screen, self.camera, layer='floor')

        for gem in self.gems:
            gem.render(screen, self.camera)
        
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
    
    # ── Debug / utilidades ────────────────────────────────────────────────────

    def get_debug_info(self):
        active_particles = sum(1 for p in self.particle_pool.pool if p.is_alive)
        return {
            'enemies_total':      len(self.enemies),
            'enemies_rendered':   self.enemies_rendered,
            'dead_pool_size':     len(self.spawn_manager.dead_pool),
            'projectiles':        len(self.projectile_pool.active),
            'particles_active':   active_particles,
            'particles_rendered': self.particles_rendered,
            'particles_capacity': self.particle_pool.capacity,
            'gems_count':         len(self.gems),
        }
    
    def cleanup(self):
        self.enemies.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.spatial_grid.clear()