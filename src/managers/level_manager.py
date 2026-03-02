"""
LevelManager con sistema de partículas GORE optimizado + ChunkManager.

CAMBIOS vs versión anterior:
  - _update_weapons(): llama weapon.auto_shoot(dt) en todas las armas
    → NovaWeapon dispara solo, OrbitalWeapon detecta colisiones sin pool.
  - _update_aura(): añadido knockback continuo si player.aura_knockback > 0
    → empuja a los enemigos hacia afuera del radio del aura.
  - Importa OrbitalWeapon para isinstance() check en _update_weapons().

OPTIMIZACIONES MÓVIL (v2):
  - _render_aura(): superficies SRCALPHA pre-alocadas y reutilizadas cada frame
    → elimina 2-3 Surface() allocations por frame (crítico en Android).
  - _update_lod(): umbrales agresivos en móvil (quality=0 desde 60 visibles).
  - _update_aura(): usa spatial_grid en lugar de iterar todos los enemigos.
  - _render_grid(): saltado completamente en móvil (decorativo, costoso).
  - echo del aura: desactivado en móvil (Surface dinámica de tamaño variable).
"""
import pygame
import math
import random
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT
from entities.player     import Player
from entities.particle   import ParticleSystem
from entities.weapon     import LaserWeapon, OrbitalWeapon
from entities.projectile import EnemyProjectile
from utils.camera        import Camera
from utils.object_pool   import ProjectilePool, ParticlePool
from utils.spatial_grid  import SpatialGrid
from utils.chunk_manager import ChunkManager
from managers.spawn_manager  import SpawnManager
from entities.experience_gem import ExperienceGem
from utils.platform_detect import is_mobile

GEM_MERGE_INTERVAL  = 120
GEM_MERGE_RADIUS    = 55
GEM_MERGE_MIN_COUNT = 3

ENEMY_TELEPORT_INTERVAL = 90
SCORE_MULTIPLIER        = 100
MAX_ENEMY_PROJECTILES   = 35

GEM_UPDATE_RADIUS_SQ = 2000 ** 2

_PARTICLE_FULL_KILLS  = 6
_PARTICLE_POOL_KILLS  = 16


class LevelManager:
    def __init__(self):
        self.projectile_pool  = ProjectilePool(initial_size=500)

        _particle_cap = 600 if is_mobile() else 1500
        self.particle_pool    = ParticlePool(capacity=_particle_cap)

        self.spatial_grid     = SpatialGrid(WORLD_WIDTH, WORLD_HEIGHT, cell_size=100)
        self.particle_system  = ParticleSystem()

        self._is_mobile = is_mobile()
        self.spawn_manager    = SpawnManager(mobile=self._is_mobile)

        self.gems: list[ExperienceGem] = []
        self.camera           = Camera(WORLD_WIDTH, WORLD_HEIGHT)
        self.player           = None
        self.enemies: list    = []
        self.enemy_projectiles: list[EnemyProjectile] = []
        self.score            = 0
        self.game_over        = False

        self.chunk_manager = ChunkManager(WORLD_WIDTH, WORLD_HEIGHT, chunk_size=1000)

        self._ai_base_interval = 4
        self.ai_update_interval = 4
        self.frame_counter      = 0

        self.hit_particle_cooldown = 0
        self.particles_rendered    = 0
        self.enemies_rendered      = 0

        self._gem_merge_timer  = 0
        self._teleport_timer   = 0
        self._explosion_flash  = 0

        self._active_enemies_buf: list = []

        self._ninja_dash_hit_set: set = set()
        self._kills_this_frame: int = 0

        # ── CACHÉ DE SUPERFICIES DEL AURA (evita allocations por frame) ──────
        # Se crean UNA VEZ cuando el radio cambia; se reutilizan y limpian
        # cada frame con fill((0,0,0,0)) en vez de crear objetos nuevos.
        self._aura_fill_surf: pygame.Surface | None = None
        self._aura_ring_surf: pygame.Surface | None = None
        self._aura_last_radius: int = -1   # invalida caché cuando cambia

        # Pre-caché de la cuadrícula de fondo (surface estática)
        self._grid_surf: pygame.Surface | None = None
        self._grid_built = False

    def initialize(self):
        self.player = Player(WORLD_WIDTH // 2, WORLD_HEIGHT // 2)
        for weapon in self.player.weapons:
            weapon.set_projectile_pool(self.projectile_pool)
        self.particle_system.set_pool(self.particle_pool)
        self.enemies.clear()
        self.enemy_projectiles.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()

        self.chunk_manager.clear()

        self.score    = 0
        self.game_over = False
        self.gems.clear()

        self.spawn_manager        = SpawnManager(mobile=self._is_mobile)

        self.hit_particle_cooldown = 0
        self.frame_counter        = 0
        self._gem_merge_timer     = 0
        self._teleport_timer      = 0
        self._explosion_flash     = 0
        self._ninja_dash_hit_set.clear()
        self._kills_this_frame    = 0

        # Invalidar caché de superficies del aura
        self._aura_fill_surf  = None
        self._aura_ring_surf  = None
        self._aura_last_radius = -1

        self.camera.snap_to(self.player)
        self.chunk_manager.update_active_chunks(self.camera)

    def set_target_fps(self, fps: int):
        scale = max(1.0, fps / 60.0)
        self._ai_base_interval = max(1, int(4 * scale))
        self.particle_pool._bake_interval = 1

    # ── LOD ─────────────────────────────────────────────────────────────────
    def _update_lod(self):
        visible   = self.enemies_rendered
        particles = self.particle_pool._alive_count

        if self._is_mobile:
            # Umbrales agresivos: en móvil hay menos potencia de cómputo.
            # Con 680 enemigos cap, 60 visibles ya es media pantalla llena.
            if visible > 60 or particles > 150:
                self.particle_system.set_quality(0)   # CRISIS
            elif visible > 30 or particles > 80:
                self.particle_system.set_quality(1)   # MEDIO
            else:
                self.particle_system.set_quality(2)   # ALTO
        else:
            # Umbrales originales para PC
            if visible > 350 or particles > 600:
                self.particle_system.set_quality(0)
            elif visible > 180 or particles > 350:
                self.particle_system.set_quality(1)
            else:
                self.particle_system.set_quality(2)

    def update(self, dt, keys, mouse_pos, mouse_pressed, mobile=None):
        if self.game_over or not self.player or not self.player.is_alive:
            self.game_over = True
            return

        self._update_lod()
        self._kills_this_frame = 0

        use_mobile = mobile is not None and mobile.enabled

        if use_mobile:
            mdx, mdy = mobile.movement
            self.player.handle_input_mobile(mdx, mdy, dt)
            if mobile.aim_angle is not None:
                self.player.angle = mobile.aim_angle
            elif mdx != 0 or mdy != 0:
                self.player.angle = math.atan2(mdy, mdx)
            if mobile.fire:
                self.player.attack(self.camera)
        else:
            cam_offset = (self.camera.offset_x, self.camera.offset_y)
            self.player.handle_input(keys, dt)
            self.player.update_rotation(mouse_pos, cam_offset)

        self.player.update(dt)

        if not use_mobile and mouse_pressed[0]:
            self.player.attack(self.camera)

        cam_mouse = None if use_mobile else mouse_pos
        self.camera.update(self.player, cam_mouse, dt)

        cam_offset = (self.camera.offset_x, self.camera.offset_y)

        self.spatial_grid.clear()
        for enemy in self.enemies:
            if enemy.is_alive:
                self.spatial_grid.insert(enemy)

        self._update_enemies(dt)
        self._update_weapons(dt)
        self._update_projectiles(dt)
        self._update_enemy_projectiles(dt)

        self._update_aura(dt)
        self._check_ninja_dash()

        player_pos = self.player.get_position()
        new_enemies = self.spawn_manager.update(
            dt, len(self.enemies), cam_offset, player_pos=player_pos
        )
        if new_enemies:
            self.enemies.extend(new_enemies)

        self._teleport_timer += dt
        if self._teleport_timer >= ENEMY_TELEPORT_INTERVAL:
            self._teleport_timer = 0
            self.spawn_manager.try_teleport_distant_enemies(
                self.enemies, cam_offset, player_pos=player_pos
            )

        self._update_gems(dt)

        self.chunk_manager.tick(self.camera)
        self.particle_pool.update_and_bake(
            dt,
            chunk_manager=self.chunk_manager
        )

        if self._explosion_flash > 0:
            self._explosion_flash -= dt

        if not self.player.dash_active:
            self._ninja_dash_hit_set.clear()

        self.frame_counter += 1

    # ── AURA (lógica) ────────────────────────────────────────────────────────
    def _update_aura(self, dt):
        player = self.player
        aura_dmg = getattr(player, 'aura_damage', 0.0)
        if aura_dmg <= 0:
            return

        aura_radius    = getattr(player, 'aura_radius', 80.0)
        aura_knockback = getattr(player, 'aura_knockback', 0.0)
        radius_sq      = aura_radius * aura_radius
        px, py         = player.x, player.y
        dmg_per_frame  = aura_dmg * dt / 60.0

        # ── OPTIMIZACIÓN: usar spatial_grid en lugar de iterar todos ──────
        # Convertimos el radio del aura a "celdas de grid" (cell_size=100px)
        # y buscamos solo los enemigos cercanos.
        grid_r = max(1, int(math.ceil(aura_radius / 100.0)))
        nearby = self.spatial_grid.get_nearby(px, py, radius=grid_r)

        for enemy in nearby:
            if not enemy.is_alive:
                continue
            dx = enemy.x - px
            dy = enemy.y - py
            dist_sq = dx * dx + dy * dy
            if dist_sq <= radius_sq:
                # Partículas
                if self.frame_counter % 8 == 0 and self.particle_system.quality > 0:
                    self.particle_system.create_blood_splatter(
                        enemy.x, enemy.y, force=0.4, count=1
                    )
                # Daño
                if enemy.take_damage(dmg_per_frame):
                    self._on_enemy_killed(enemy)
                # Knockback radial continuo (si upgrade activo)
                elif aura_knockback > 0 and dist_sq > 1:
                    dist = math.sqrt(dist_sq)
                    push = aura_knockback * dt * 0.6
                    enemy.knockback_x += (dx / dist) * push
                    enemy.knockback_y += (dy / dist) * push

    def _check_ninja_dash(self):
        player = self.player
        if not getattr(player, 'ninja_dash', False):
            return
        if not player.dash_active:
            return

        px, py      = player.x, player.y
        kill_radius = player.size * 2.8
        kill_r_sq   = kill_radius * kill_radius
        ninja_kills = 0

        for enemy in self.enemies:
            if not enemy.is_alive:
                continue
            if id(enemy) in self._ninja_dash_hit_set:
                continue
            dx = enemy.x - px
            dy = enemy.y - py
            if dx * dx + dy * dy <= kill_r_sq:
                self._ninja_dash_hit_set.add(id(enemy))
                enemy.is_alive = False
                self._on_enemy_killed(enemy)
                ninja_kills += 1

        if ninja_kills > 0:
            shake_amt = min(14.0, 2.0 + ninja_kills * 0.3)
            self.camera.add_shake(shake_amt)

    def _update_gems(self, dt):
        player_pos = self.player.get_position()
        px, py     = player_pos
        magnet_range = getattr(self.player, 'magnet_range_mult', 1.0)
        magnet_spd   = getattr(self.player, 'magnet_speed_mult', 1.0)
        player_rect  = self.player.rect

        i = len(self.gems) - 1
        while i >= 0:
            gem = self.gems[i]
            dx  = gem.x - px
            dy  = gem.y - py
            if (dx * dx + dy * dy) <= GEM_UPDATE_RADIUS_SQ or gem.is_magnetized or gem.z > 0:
                gem.update(player_pos, dt,
                           magnet_range_mult=magnet_range,
                           magnet_speed_mult=magnet_spd)
                if player_rect.colliderect(gem.rect):
                    self.player.gain_experience(gem.xp_value)
                    self.gems.pop(i)
            i -= 1

        self._gem_merge_timer += dt
        if self._gem_merge_timer >= GEM_MERGE_INTERVAL:
            self._gem_merge_timer = 0
            self._merge_nearby_gems()

    def _update_enemies(self, dt):
        player_pos = self.player.get_position()
        px, py     = player_pos
        ec         = len(self.enemies)

        base = self._ai_base_interval
        if ec > 800:    interval = base * 2
        elif ec > 400:  interval = int(base * 1.5)
        else:           interval = base
        self.ai_update_interval = interval

        current_batch = self.frame_counter % interval
        sg = self.spatial_grid
        ps = self.particle_system

        buf = self._active_enemies_buf
        buf.clear()

        spawn_add = self.spawn_manager.add_to_dead_pool
        on_killed = self._on_enemy_killed
        player_vel = (self.player.vel_x, self.player.vel_y)

        for i, enemy in enumerate(self.enemies):
            if not enemy.is_alive:
                spawn_add(enemy)
                continue

            if i % interval == current_batch:
                enemy.update_ai(player_pos, sg, player_vel=player_vel)

            enemy.update_physics(dt)
            enemy.update(ps, dt)

            action = enemy.update_special(player_pos, dt)
            if action:
                self._handle_enemy_action(action, enemy)

            dx = enemy.x - px
            dy = enemy.y - py
            if dx * dx + dy * dy < 2500:
                enemy.attack(self.player)

            if enemy.is_alive:
                buf.append(enemy)
            else:
                spawn_add(enemy)

        self.enemies = list(buf)

    def _handle_enemy_action(self, action, enemy):
        if action['type'] == 'explosion':
            self._handle_explosion(action['x'], action['y'],
                                   action['damage'], action['radius'])
            self.particle_system.create_viscera_explosion(action['x'], action['y'])
            self._explosion_flash = 8
            if action.get('kill_self'):
                enemy.is_alive = False

        elif action['type'] == 'projectile':
            if len(self.enemy_projectiles) < MAX_ENEMY_PROJECTILES:
                ep = EnemyProjectile(
                    x=action['x'], y=action['y'],
                    angle=action['angle'], speed=action['speed'],
                    damage=action['damage'], lifetime=action['lifetime'],
                    color=action['color'], radius=action['radius'],
                    proj_type=action.get('proj_type', 'acid'),
                )
                self.enemy_projectiles.append(ep)

    def _handle_explosion(self, ex, ey, damage, radius):
        radius_sq = radius * radius
        px, py    = self.player.x, self.player.y
        dx = px - ex;  dy = py - ey
        if dx * dx + dy * dy <= radius_sq:
            dist    = math.sqrt(dx * dx + dy * dy) if (dx or dy) else 0
            falloff = max(0.2, 1.0 - (dist / radius) * 0.7)
            self.player.take_damage(int(damage * falloff))
            self.camera.add_shake(12)
        self.particle_system.create_blood_pool(ex, ey)

    def _update_weapons(self, dt):
        if self.hit_particle_cooldown > 0:
            self.hit_particle_cooldown -= dt

        kb_mult = getattr(self.player, 'knockback_mult', 1.0)
        
        # Iterar sobre AMBAS listas
        all_weapons = self.player.weapons + getattr(self.player, 'passive_weapons', [])

        for weapon in all_weapons:
            weapon.update(dt=dt)

            # Auto-disparo (Nova, Boomerang, etc.)
            weapon.auto_shoot(dt)

            # Orbes Orbitales: detección de impacto pasiva
            if isinstance(weapon, OrbitalWeapon):
                for enemy, dmg in weapon.check_hits(self.enemies, kb_mult):
                    if enemy.take_damage(dmg):
                        self._on_enemy_killed(enemy)

            # Láser continuo
            if isinstance(weapon, LaserWeapon) and weapon.draw_timer > 0:
                beam = weapon.get_beam_info()
                if beam:
                    start, end = beam
                    dps = weapon.get_damage_per_second()
                    dmg_frame = dps * (dt / 60.0)
                    for enemy in self.enemies:
                        if enemy.rect.clipline(start, end):
                            if enemy.take_damage(dmg_frame):
                                self._on_enemy_killed(enemy)

    def _update_projectiles(self, dt):
        knockback_mult = getattr(self.player, 'knockback_mult', 1.0)
        ps             = self.particle_system
        hpc            = self.hit_particle_cooldown

        for projectile in self.projectile_pool.active[:]:
            projectile.update(dt)
            hit_enemy = projectile.check_collision_grid(self.spatial_grid)

            if hit_enemy and hit_enemy.is_alive:
                hit_enemy.apply_knockback(projectile.x, projectile.y,
                                          force=8 * knockback_mult)

                if hpc <= 0:
                    vx, vy = projectile.vel_x, projectile.vel_y
                    sp_sq  = vx * vx + vy * vy
                    direction = None
                    if sp_sq > 0.01:
                        inv_sp = 1.0 / math.sqrt(sp_sq)
                        direction = (vx * inv_sp, vy * inv_sp)

                    ps.create_blood_splatter(hit_enemy.x, hit_enemy.y,
                                             direction_vector=direction,
                                             force=1.5, count=6)
                    hpc = 1 if ps.quality == 2 else 4

                if hit_enemy.take_damage(projectile.damage):
                    self._on_enemy_killed(hit_enemy)

            if not projectile.is_alive:
                self.projectile_pool.return_to_pool(projectile)

        self.hit_particle_cooldown = hpc

    def _update_enemy_projectiles(self, dt):
        alive  = []
        player = self.player
        for ep in self.enemy_projectiles:
            ep.update(dt)
            if ep.is_alive:
                ep.check_player_collision(player)
            if ep.is_alive:
                alive.append(ep)
        self.enemy_projectiles = alive

    def _on_enemy_killed(self, enemy):
        self.score += enemy.points * SCORE_MULTIPLIER
        self._kills_this_frame += 1

        k  = self._kills_this_frame
        ps = self.particle_system

        if k <= _PARTICLE_FULL_KILLS:
            ps.create_viscera_explosion(enemy.x, enemy.y)
        elif k <= _PARTICLE_POOL_KILLS:
            ps.create_blood_pool(enemy.x, enemy.y)

        self.gems.append(ExperienceGem(enemy.x, enemy.y, enemy.points))

        if random.random() < getattr(self.player, 'lifesteal_chance', 0.0):
            self.player.heal(getattr(self.player, 'lifesteal', 5))

        xp_bonus = getattr(self.player, 'xp_on_kill_bonus', 0)
        if xp_bonus > 0:
            self.player.gain_experience(xp_bonus)

    def _merge_nearby_gems(self):
        if len(self.gems) < GEM_MERGE_MIN_COUNT:
            return
        radius_sq = GEM_MERGE_RADIUS ** 2
        visited   = [False] * len(self.gems)
        new_gems  = []

        for i, gem_a in enumerate(self.gems):
            if visited[i]:
                continue
            if gem_a.is_magnetized or gem_a.z > 0:
                visited[i] = True
                new_gems.append(gem_a)
                continue

            group = [i]
            ax, ay = gem_a.x, gem_a.y
            for j in range(i + 1, len(self.gems)):
                if visited[j]:
                    continue
                gem_b = self.gems[j]
                if gem_b.is_magnetized or gem_b.z > 0:
                    continue
                dx = ax - gem_b.x
                dy = ay - gem_b.y
                if dx * dx + dy * dy <= radius_sq:
                    group.append(j)

            if len(group) >= GEM_MERGE_MIN_COUNT:
                total_xp = sum(self.gems[idx].xp_value for idx in group)
                cx = sum(self.gems[idx].x for idx in group) / len(group)
                cy = sum(self.gems[idx].y for idx in group) / len(group)
                merged = ExperienceGem(cx, cy, total_xp)
                merged.z = merged.vz = merged.vx = merged.vy = 0
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

    # ── RENDER ──────────────────────────────────────────────────────────────
    def render_world(self, screen):
        self._render_grid(screen)

        self.chunk_manager.render(screen, self.camera)

        self.particle_pool.render_all(screen, self.camera, layer='floor')

        cam = self.camera
        for gem in self.gems:
            gem.render(screen, cam)

        is_on = cam.is_on_screen
        for projectile in self.projectile_pool.active:
            if is_on(projectile.rect):
                projectile.render(screen, cam)

        for ep in self.enemy_projectiles:
            if is_on(ep.rect):
                ep.render(screen, cam)

        self.enemies_rendered = 0
        render_margin = 200
        for enemy in self.enemies:
            er = enemy.rect.inflate(render_margin * 2, render_margin * 2)
            if is_on(er):
                enemy.render(screen, cam)
                self.enemies_rendered += 1

        if self.player:
            self._render_aura(screen)

        if self.player:
            all_weapons = self.player.weapons + getattr(self.player, 'passive_weapons', [])
            for weapon in all_weapons:
                if hasattr(weapon, 'render'):
                    weapon.render(screen, cam)
            self.player.render(screen, cam)

        rendered_air = self.particle_pool.render_all(screen, self.camera, layer='air')
        self.particles_rendered = rendered_air

        if self._explosion_flash > 0:
            alpha = int(self._explosion_flash * 14)
            flash = pygame.Surface((screen.get_width(), screen.get_height()),
                                   pygame.SRCALPHA)
            flash.fill((255, 60, 0, min(80, alpha)))
            screen.blit(flash, (0, 0))

        if self.player and self.player.ninja_dash and self.player.dash_active:
            self._render_ninja_dash_effect(screen)

    # ── AURA (render) ────────────────────────────────────────────────────────
    def _render_aura(self, screen):
        player = self.player
        aura_dmg = getattr(player, 'aura_damage', 0.0)
        if aura_dmg <= 0:
            return

        aura_radius = int(getattr(player, 'aura_radius', 80.0))
        sp = self.camera.apply_coords(player.x, player.y)
        cx, cy = int(sp[0]), int(sp[1])

        t = self.frame_counter * 0.05
        pulse_a = (math.sin(t) + 1.0) * 0.5
        pulse_b = (math.sin(t + math.pi) + 1.0) * 0.5

        # ── CACHÉ DE SUPERFICIES: crear solo cuando el radio cambia ──────────
        # En móvil el radio raramente cambia mid-game, así que en la práctica
        # estas superficies se crean 1-2 veces por partida, no cada frame.
        if aura_radius != self._aura_last_radius:
            diam = aura_radius * 2
            self._aura_fill_surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
            self._aura_ring_surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
            self._aura_last_radius = aura_radius

        # Reutilizar fill_surf: limpiar → redibujar
        fill_alpha = int(18 + pulse_a * 14)
        self._aura_fill_surf.fill((0, 0, 0, 0))
        pygame.draw.circle(self._aura_fill_surf, (180, 30, 255, fill_alpha),
                           (aura_radius, aura_radius), aura_radius)
        screen.blit(self._aura_fill_surf, (cx - aura_radius, cy - aura_radius))

        # Reutilizar ring_surf
        ring_alpha = int(90 + pulse_b * 80)
        self._aura_ring_surf.fill((0, 0, 0, 0))
        pygame.draw.circle(self._aura_ring_surf, (220, 60, 255, ring_alpha),
                           (aura_radius, aura_radius), aura_radius, 2)
        screen.blit(self._aura_ring_surf, (cx - aura_radius, cy - aura_radius))

        # ── Echo del aura: SALTADO en móvil ──────────────────────────────────
        # El echo usa un radio dinámico (echo_r) que cambia cada frame,
        # lo que obligaría a crear una Surface nueva cada frame.
        # En móvil simplemente lo omitimos — el efecto visual es menor.
        if not self._is_mobile:
            echo_r = int(aura_radius * (1.0 + pulse_a * 0.15))
            echo_alpha = int(40 * (1.0 - pulse_a))
            if echo_r > 0 and echo_alpha > 4:
                echo_surf = pygame.Surface((echo_r * 2, echo_r * 2), pygame.SRCALPHA)
                pygame.draw.circle(echo_surf, (200, 80, 255, echo_alpha),
                                   (echo_r, echo_r), echo_r, 1)
                screen.blit(echo_surf, (cx - echo_r, cy - echo_r))

    def _render_ninja_dash_effect(self, screen):
        player = self.player
        sp = self.camera.apply_coords(player.x, player.y)
        cx, cy = int(sp[0]), int(sp[1])

        progress = player.dash_timer / player.dash_duration
        ring_r = int(player.size * 1.8 + (1.0 - progress) * 20)
        ring_alpha = int(progress * 180)

        ring_surf = pygame.Surface((ring_r * 2, ring_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(ring_surf, (140, 0, 255, ring_alpha),
                           (ring_r, ring_r), ring_r, 3)
        screen.blit(ring_surf, (cx - ring_r, cy - ring_r))

    # ── GRID ────────────────────────────────────────────────────────────────
    def _render_grid(self, screen):
        # ── En móvil la cuadrícula decorativa se salta completamente ─────────
        # Dibujar ~26 líneas horizontales + ~20 verticales cada frame no es
        # gratis en Android, y el jugador móvil no las necesita.
        if self._is_mobile:
            # Solo los bordes del mundo (útil para orientación)
            ox = self.camera.offset_x
            oy = self.camera.offset_y
            for lx in (ox, ox + WORLD_WIDTH):
                if 0 <= lx <= WINDOW_WIDTH:
                    pygame.draw.line(screen, (100, 0, 0),
                                     (int(lx), 0), (int(lx), WINDOW_HEIGHT), 2)
            for ly in (oy, oy + WORLD_HEIGHT):
                if 0 <= ly <= WINDOW_HEIGHT:
                    pygame.draw.line(screen, (100, 0, 0),
                                     (0, int(ly)), (WINDOW_WIDTH, int(ly)), 2)
            return

        # PC: cuadrícula completa + bordes del mundo (comportamiento original)
        gs = 100
        ox = self.camera.offset_x
        oy = self.camera.offset_y
        sx = ox % gs
        sy = oy % gs
        gc = (30, 30, 30)
        for x in range(int(sx), WINDOW_WIDTH, gs):
            pygame.draw.line(screen, gc, (x, 0), (x, WINDOW_HEIGHT))
        for y in range(int(sy), WINDOW_HEIGHT, gs):
            pygame.draw.line(screen, gc, (0, y), (WINDOW_WIDTH, y))
        for lx in (ox, ox + WORLD_WIDTH):
            if 0 <= lx <= WINDOW_WIDTH:
                pygame.draw.line(screen, (100, 0, 0), (lx, 0), (lx, WINDOW_HEIGHT), 2)
        for ly in (oy, oy + WORLD_HEIGHT):
            if 0 <= ly <= WINDOW_HEIGHT:
                pygame.draw.line(screen, (100, 0, 0), (0, ly), (WINDOW_WIDTH, ly), 2)

    def get_debug_info(self):
        active_p = self.particle_pool._alive_count
        cm_info  = self.chunk_manager.get_debug_info()
        return {
            'enemies_total':      len(self.enemies),
            'enemies_rendered':   self.enemies_rendered,
            'dead_pool_size':     len(self.spawn_manager.dead_pool),
            'projectiles':        len(self.projectile_pool.active),
            'enemy_projectiles':  len(self.enemy_projectiles),
            'particles_active':   active_p,
            'particles_rendered': self.particles_rendered,
            'particles_capacity': self.particle_pool.capacity,
            'gems_count':         len(self.gems),
            'particle_quality':   self.particle_system.quality,
            'kills_this_frame':   self._kills_this_frame,
            'chunks_active':      cm_info['chunks_active'],
            'chunks_total':       cm_info['chunks_total'],
        }

    def cleanup(self):
        self.enemies.clear()
        self.enemy_projectiles.clear()
        self.projectile_pool.clear()
        self.particle_pool.clear()
        self.spatial_grid.clear()
        self.chunk_manager.clear()