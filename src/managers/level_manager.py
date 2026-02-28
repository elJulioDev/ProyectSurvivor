"""
LevelManager — Actualizado:
  · LOD basado en enemigos VISIBLES (no en total), para no degradar gráficos
    por enemigos fuera de pantalla.
  · Proyectiles enemigos (ácido del Spitter, roca del Tank).
  · Explosiones del Exploder con daño en área.
  · Spawn circular pasando player_pos al SpawnManager.
  · Cap de enemigos dinámico hasta 800.
  · Cámara inicializada con snap_to para evitar salto brusco al inicio.
"""
import pygame
import math
from settings import WORLD_WIDTH, WORLD_HEIGHT
from entities.player import Player
from entities.particle import ParticleSystem
from entities.weapon import LaserWeapon
from entities.projectile import EnemyProjectile
from utils.camera import Camera
from utils.object_pool import ProjectilePool, ParticlePool
from utils.spatial_grid import SpatialGrid
from managers.spawn_manager import SpawnManager
from entities.experience_gem import ExperienceGem


GEM_MERGE_INTERVAL  = 120
GEM_MERGE_RADIUS    = 55
GEM_MERGE_MIN_COUNT = 3

ENEMY_TELEPORT_INTERVAL = 90
SCORE_MULTIPLIER = 100

# Máximo de proyectiles enemigos simultáneos
MAX_ENEMY_PROJECTILES = 35


class LevelManager:
    def __init__(self):
        self.projectile_pool  = ProjectilePool(initial_size=500)
        self.particle_pool    = ParticlePool(capacity=800)
        self.spatial_grid     = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        self.particle_system  = ParticleSystem()
        self.spawn_manager    = SpawnManager()
        self.gems: list[ExperienceGem] = []
        self.camera           = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.player           = None
        self.enemies: list    = []
        self.enemy_projectiles: list[EnemyProjectile] = []
        self.score            = 0
        self.game_over        = False
        self.blood_surface    = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT),
                                               pygame.SRCALPHA)
        self.blood_surface.fill((0, 0, 0, 0))

        self.ai_update_interval    = 4
        self.frame_counter         = 0
        self.hit_particle_cooldown = 0
        self.particles_rendered    = 0
        self.enemies_rendered      = 0

        self._gem_merge_timer  = 0
        self._teleport_timer   = 0

        # Superficie de aviso de explosión (flash en pantalla)
        self._explosion_flash = 0

    def initialize(self):
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        for weapon in self.player.weapons:
            weapon.set_projectile_pool(self.projectile_pool)
        self.particle_system.set_pool(self.particle_pool)
        self.enemies.clear()
        self.enemy_projectiles.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.blood_surface.fill((0, 0, 0, 0))
        self.score             = 0
        self.game_over         = False
        self.gems.clear()
        self.spawn_manager     = SpawnManager()
        self.hit_particle_cooldown = 0
        self.frame_counter     = 0
        self._gem_merge_timer  = 0
        self._teleport_timer   = 0
        self._explosion_flash  = 0

        # Snap de cámara: evita el salto brusco al inicio
        self.camera.snap_to(self.player)

    def update(self, dt, keys, mouse_pos, mouse_pressed):
        if self.game_over or not self.player or not self.player.is_alive:
            self.game_over = True
            return

        # LOD CORREGIDO: basado en enemigos VISIBLES, no en total
        visible = self.enemies_rendered
        if visible < 200:
            self.particle_system.set_quality(2)
        elif visible < 400:
            self.particle_system.set_quality(1)
        else:
            self.particle_system.set_quality(0)

        self.player.handle_input(keys, dt)
        self.player.update_rotation(mouse_pos,
                                    (self.camera.offset_x, self.camera.offset_y))
        self.player.update(dt)

        if mouse_pressed[0]:
            self.player.attack(self.camera)

        self.camera.update(self.player, mouse_pos)
        cam_offset = (self.camera.offset_x, self.camera.offset_y)

        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)

        self._update_enemies(dt)
        self._update_weapons(dt)
        self._update_projectiles(dt)
        self._update_enemy_projectiles(dt)

        # Spawn con posición real del jugador (spawn circular)
        player_pos = self.player.get_position()
        new_enemy = self.spawn_manager.update(
            dt, len(self.enemies), cam_offset, player_pos=player_pos
        )
        if new_enemy:
            self.enemies.append(new_enemy)

        self._teleport_timer += dt
        if self._teleport_timer >= ENEMY_TELEPORT_INTERVAL:
            self._teleport_timer = 0
            self.spawn_manager.try_teleport_distant_enemies(
                self.enemies, cam_offset, player_pos=player_pos
            )

        # Gemas
        magnet_range = getattr(self.player, 'magnet_range_mult', 1.0)
        magnet_spd   = getattr(self.player, 'magnet_speed_mult', 1.0)

        for i in range(len(self.gems) - 1, -1, -1):
            gem = self.gems[i]
            gem.update(self.player.get_position(), dt,
                       magnet_range_mult=magnet_range,
                       magnet_speed_mult=magnet_spd)
            if self.player.rect.colliderect(gem.rect):
                self.player.gain_experience(gem.xp_value)
                self.gems.pop(i)

        self._gem_merge_timer += dt
        if self._gem_merge_timer >= GEM_MERGE_INTERVAL:
            self._gem_merge_timer = 0
            self._merge_nearby_gems()

        self.particle_pool.update_all(dt)
        self.particle_pool.bake_static_blood(self.blood_surface)

        if self._explosion_flash > 0:
            self._explosion_flash -= 1 * dt

        self.frame_counter += 1

    # ── Entidades ─────────────────────────────────────────────────────────────

    def _update_enemies(self, dt):
        player_pos = self.player.get_position()

        enemy_count = len(self.enemies)
        if enemy_count > 800:    self.ai_update_interval = 8
        elif enemy_count > 400:  self.ai_update_interval = 6
        else:                    self.ai_update_interval = 4

        current_batch = self.frame_counter % self.ai_update_interval
        active_enemies = []

        for i, enemy in enumerate(self.enemies):
            if not enemy.is_alive:
                self.spawn_manager.add_to_dead_pool(enemy)
                continue

            if i % self.ai_update_interval == current_batch:
                enemy.update_ai(player_pos, self.spatial_grid)

            enemy.update_physics(dt)
            enemy.update(self.particle_system, dt)

            # ── Habilidades especiales ──────────────────────────────────
            action = enemy.update_special(player_pos, dt)
            if action:
                self._handle_enemy_action(action, enemy)

            # Ataque cuerpo a cuerpo
            dist_sq = ((enemy.x - self.player.x) ** 2 +
                       (enemy.y - self.player.y) ** 2)
            if dist_sq < 2500:
                enemy.attack(self.player)

            if enemy.is_alive:
                active_enemies.append(enemy)
            else:
                self.spawn_manager.add_to_dead_pool(enemy)

        self.enemies = active_enemies

    def _handle_enemy_action(self, action, enemy):
        """Procesa el resultado de una habilidad especial enemiga."""
        if action['type'] == 'explosion':
            self._handle_explosion(
                action['x'], action['y'],
                action['damage'], action['radius']
            )
            self.particle_system.create_viscera_explosion(action['x'], action['y'])
            self._explosion_flash = 8
            if action.get('kill_self'):
                enemy.is_alive = False

        elif action['type'] == 'projectile':
            if len(self.enemy_projectiles) < MAX_ENEMY_PROJECTILES:
                ep = EnemyProjectile(
                    x         = action['x'],
                    y         = action['y'],
                    angle     = action['angle'],
                    speed     = action['speed'],
                    damage    = action['damage'],
                    lifetime  = action['lifetime'],
                    color     = action['color'],
                    radius    = action['radius'],
                    proj_type = action.get('proj_type', 'acid'),
                )
                self.enemy_projectiles.append(ep)

    def _handle_explosion(self, ex, ey, damage, radius):
        """Daño en área al jugador."""
        radius_sq = radius * radius
        px, py = self.player.x, self.player.y
        dx = px - ex
        dy = py - ey
        if dx * dx + dy * dy <= radius_sq:
            dist = math.sqrt(dx * dx + dy * dy) if (dx or dy) else 0
            falloff = max(0.2, 1.0 - (dist / radius) * 0.7)
            self.player.take_damage(int(damage * falloff))
            self.camera.add_shake(12)

        self.particle_system.create_blood_pool(ex, ey)

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
                        dps = weapon.get_damage_per_second()
                        damage_this_frame = dps * (dt / 60.0)

                        for enemy in self.enemies:
                            if enemy.rect.clipline(start, end):
                                if enemy.take_damage(damage_this_frame):
                                    self._on_enemy_killed(enemy)

    def _update_projectiles(self, dt):
        knockback_mult = getattr(self.player, 'knockback_mult', 1.0)

        for projectile in self.projectile_pool.active[:]:
            projectile.update(dt)
            hit_enemy = projectile.check_collision_grid(self.spatial_grid)

            if hit_enemy and hit_enemy.is_alive:
                hit_enemy.apply_knockback(projectile.x, projectile.y,
                                          force=8 * knockback_mult)

                if self.hit_particle_cooldown <= 0:
                    p_speed_sq = projectile.vel_x ** 2 + projectile.vel_y ** 2
                    direction = None
                    if p_speed_sq > 0.01:
                        inv_speed = 1.0 / math.sqrt(p_speed_sq)
                        direction = (projectile.vel_x * inv_speed,
                                     projectile.vel_y * inv_speed)
                    self.particle_system.create_blood_splatter(
                        hit_enemy.x, hit_enemy.y,
                        direction_vector=direction, force=1.5, count=6
                    )
                    self.hit_particle_cooldown = (
                        1 if self.particle_system.quality == 2 else 4
                    )

                if hit_enemy.take_damage(projectile.damage):
                    self._on_enemy_killed(hit_enemy)

            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)

    def _update_enemy_projectiles(self, dt):
        alive = []
        for ep in self.enemy_projectiles:
            ep.update(dt)
            if ep.is_alive:
                ep.check_player_collision(self.player)
            if ep.is_alive:
                alive.append(ep)
        self.enemy_projectiles = alive

    def _on_enemy_killed(self, enemy):
        self.score += enemy.points * SCORE_MULTIPLIER
        self.particle_system.create_viscera_explosion(enemy.x, enemy.y)

        gem = ExperienceGem(enemy.x, enemy.y, enemy.points)
        self.gems.append(gem)

        lifesteal = getattr(self.player, 'lifesteal', 0)
        if lifesteal > 0:
            self.player.heal(lifesteal)

        xp_bonus = getattr(self.player, 'xp_on_kill_bonus', 0)
        if xp_bonus > 0:
            self.player.gain_experience(xp_bonus)

    # Fusión de gemas
    def _merge_nearby_gems(self):
        if len(self.gems) < GEM_MERGE_MIN_COUNT:
            return

        radius_sq = GEM_MERGE_RADIUS * GEM_MERGE_RADIUS
        visited   = [False] * len(self.gems)
        new_gems: list[ExperienceGem] = []

        for i, gem_a in enumerate(self.gems):
            if visited[i]:
                continue
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
                total_xp = sum(self.gems[idx].xp_value for idx in group)
                cx = sum(self.gems[idx].x for idx in group) / len(group)
                cy = sum(self.gems[idx].y for idx in group) / len(group)

                merged = ExperienceGem(cx, cy, total_xp)
                merged.z  = 0
                merged.vz = 0
                merged.vx = 0
                merged.vy = 0

                new_gems.append(merged)
                for idx in group:
                    visited[idx] = True
            else:
                for idx in group:
                    if not visited[idx]:
                        new_gems.append(self.gems[idx])
                        visited[idx] = True

        for i, gem in enumerate(self.gems):
            if not visited[i]:
                new_gems.append(gem)

        self.gems = new_gems

    # Renderizado
    def render_world(self, screen):
        self._render_grid(screen)

        bg_x = max(0, int(-self.camera.offset_x))
        bg_y = max(0, int(-self.camera.offset_y))
        from settings import WINDOW_WIDTH, WINDOW_HEIGHT
        area_rect = pygame.Rect(bg_x, bg_y, WINDOW_WIDTH, WINDOW_HEIGHT)
        screen.blit(self.blood_surface, (0, 0), area=area_rect)

        self.particle_pool.render_all(screen, self.camera, layer='floor')

        for gem in self.gems:
            gem.render(screen, self.camera)

        for projectile in self.projectile_pool.active:
            if self.camera.is_on_screen(projectile.rect):
                projectile.render(screen, self.camera)

        for ep in self.enemy_projectiles:
            if self.camera.is_on_screen(ep.rect):
                ep.render(screen, self.camera)

        self.enemies_rendered = 0
        render_margin = 200
        for enemy in self.enemies:
            expanded_rect = enemy.rect.inflate(render_margin * 2,
                                               render_margin * 2)
            if self.camera.is_on_screen(expanded_rect):
                enemy.render(screen, self.camera)
                self.enemies_rendered += 1

        if self.player:
            for weapon in self.player.weapons:
                if hasattr(weapon, 'render'):
                    weapon.render(screen, self.camera)

        if self.player:
            self.player.render(screen, self.camera)

        rendered_air = self.particle_pool.render_all(screen, self.camera,
                                                      layer='air')
        self.particles_rendered = rendered_air

        if self._explosion_flash > 0:
            alpha = int(self._explosion_flash * 14)
            flash_surf = pygame.Surface(
                (screen.get_width(), screen.get_height()), pygame.SRCALPHA
            )
            flash_surf.fill((255, 60, 0, min(80, alpha)))
            screen.blit(flash_surf, (0, 0))

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
            pygame.draw.line(screen, (100, 0, 0),
                             (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_x = self.camera.offset_x + WORLD_WIDTH
        if 0 <= line_x <= WINDOW_WIDTH:
            pygame.draw.line(screen, (100, 0, 0),
                             (line_x, 0), (line_x, WINDOW_HEIGHT), 2)
        line_y = self.camera.offset_y
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(screen, (100, 0, 0),
                             (0, line_y), (WINDOW_WIDTH, line_y), 2)
        line_y = self.camera.offset_y + WORLD_HEIGHT
        if 0 <= line_y <= WINDOW_HEIGHT:
            pygame.draw.line(screen, (100, 0, 0),
                             (0, line_y), (WINDOW_WIDTH, line_y), 2)

    # Debug
    def get_debug_info(self):
        active_particles = sum(1 for p in self.particle_pool.pool if p.is_alive)
        return {
            'enemies_total':      len(self.enemies),
            'enemies_rendered':   self.enemies_rendered,
            'dead_pool_size':     len(self.spawn_manager.dead_pool),
            'projectiles':        len(self.projectile_pool.active),
            'enemy_projectiles':  len(self.enemy_projectiles),
            'particles_active':   active_particles,
            'particles_rendered': self.particles_rendered,
            'particles_capacity': self.particle_pool.capacity,
            'gems_count':         len(self.gems),
        }

    def cleanup(self):
        self.enemies.clear()
        self.enemy_projectiles.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.spatial_grid.clear()