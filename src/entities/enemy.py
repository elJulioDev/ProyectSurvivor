import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED,
    WORLD_WIDTH, WORLD_HEIGHT,
)

SPRITE_CACHE = {}

class Enemy:
    TYPES = {
        'small': {
            'size_mult': 0.85, 'health': 40,  'speed_mult': 1.2,  'damage': 6,
            'color': (160, 240, 160), 'points': 5,
            'special': None, 'special_cooldown': 0,
        },
        'normal': {
            'size_mult': 1.0,  'health': 90,  'speed_mult': 1.0,  'damage': 12,
            'color': (70, 160, 70),   'points': 10,
            'special': None, 'special_cooldown': 0,
        },
        'large': {
            'size_mult': 1.5,  'health': 220, 'speed_mult': 0.72, 'damage': 18,
            'color': (30, 100, 30),   'points': 20,
            'special': None, 'special_cooldown': 0,
        },
        'tank': {
            'size_mult': 2.2,  'health': 700, 'speed_mult': 0.38, 'damage': 30,
            'color': (45, 65, 30),    'points': 60,
            'special': 'rock', 'special_cooldown': 420,
        },
        # Zombie corredor: explota al llegar cerca del jugador
        'exploder': {
            'size_mult': 0.8,  'health': 50,  'speed_mult': 2.1,  'damage': 0,
            'color': (255, 80, 20),   'points': 22,
            'special': 'explode', 'special_cooldown': 0,
        },
        # Zombie escupidor: mantiene distancia y lanza ácido
        'spitter': {
            'size_mult': 1.1,  'health': 110, 'speed_mult': 0.75, 'damage': 8,
            'color': (80, 210, 50),   'points': 30,
            'special': 'spit', 'special_cooldown': 360,
        },
    }

    def __init__(self, x, y, speed_multiplier=1.0, enemy_type='normal', health_mult=1.0):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        self.health_mult = health_mult
        type_data = self.TYPES[enemy_type]

        self.size = int(ENEMY_SIZE * type_data['size_mult'])
        self.base_speed = ENEMY_SPEED * speed_multiplier * type_data['speed_mult']
        self.color = type_data['color']
        self.damage = type_data['damage']
        self.max_health = int(type_data['health'] * health_mult)
        self.health = self.max_health
        self.points = type_data['points']

        self.special = type_data.get('special', None)
        self.special_cooldown_max = type_data.get('special_cooldown', 0)
        self.special_cooldown_timer = random.randint(
            0, max(1, self.special_cooldown_max // 2)
        ) if self.special_cooldown_max > 0 else 0

        self.hitbox_padding = 10
        self.hitbox_total = self.size + self.hitbox_padding

        self.image, self.flash_image = self._get_cached_sprite(
            self.size, self.hitbox_total, self.color
        )
        self.rect = pygame.Rect(0, 0, self.hitbox_total, self.hitbox_total)
        self.rect.center = (self.x, self.y)

        self.radius = self.size * 0.40
        self.speed_variance = random.uniform(0.9, 1.1)

        self.vx = 0
        self.vy = 0
        self.is_alive = True
        self.attack_cooldown = 0
        self.attack_delay = 60

        self.knockback_x = 0
        self.knockback_y = 0
        self.knockback_decay = 0.88

        self.damage_flash = 0
        self.bleed_intensity = 0.0
        self.bleed_decay = 0.3
        self.bleed_drip_cooldown = 0

        # Carga visual del Exploder (0.0 → 1.0)
        self.charge_level = 0.0

    # ─────────────────────────────────────────────────────────
    # Reciclado / Teletransporte
    # ─────────────────────────────────────────────────────────

    def recycle(self, x, y, speed_multiplier=1.0, enemy_type=None, health_mult=1.0):
        if enemy_type and enemy_type != self.enemy_type:
            self.enemy_type = enemy_type
            type_data = self.TYPES[enemy_type]
            self.size = int(ENEMY_SIZE * type_data['size_mult'])
            self.color = type_data['color']
            self.damage = type_data['damage']
            self.points = type_data['points']
            self.special = type_data.get('special', None)
            self.special_cooldown_max = type_data.get('special_cooldown', 0)
            self.hitbox_total = self.size + self.hitbox_padding
            self.radius = self.size * 0.40
            self.image, self.flash_image = self._get_cached_sprite(
                self.size, self.hitbox_total, self.color
            )
            self.rect = pygame.Rect(0, 0, self.hitbox_total, self.hitbox_total)
        else:
            type_data = self.TYPES[self.enemy_type]

        self.x = x
        self.y = y
        self.rect.center = (int(x), int(y))
        self.health_mult = health_mult

        self.base_speed = ENEMY_SPEED * speed_multiplier * type_data['speed_mult']
        self.max_health = int(type_data['health'] * health_mult)
        self.health = self.max_health
        self.speed_variance = random.uniform(0.9, 1.1)
        self.special_cooldown_timer = random.randint(
            0, max(1, self.special_cooldown_max // 2)
        ) if self.special_cooldown_max > 0 else 0

        self.is_alive = True
        self.vx = 0
        self.vy = 0
        self.knockback_x = 0
        self.knockback_y = 0
        self.damage_flash = 0
        self.bleed_intensity = 0.0
        self.bleed_drip_cooldown = 0
        self.attack_cooldown = 0
        self.charge_level = 0.0

    def teleport_to(self, x, y):
        self.x = x
        self.y = y
        self.rect.center = (int(x), int(y))
        self.vx = 0
        self.vy = 0
        self.knockback_x = 0
        self.knockback_y = 0

    # ─────────────────────────────────────────────────────────
    # Sprite
    # ─────────────────────────────────────────────────────────

    def _get_cached_sprite(self, size, total_size, color):
        key = (size, total_size, color)
        if key not in SPRITE_CACHE:
            offset = (total_size - size) // 2
            draw_rect = pygame.Rect(offset, offset, size, size)
            border_color = tuple(max(0, c - 50) for c in color)

            center_size = max(2, size // 3)
            c_pos = offset + (size - center_size) // 2
            center_rect = (c_pos, c_pos, center_size, center_size)

            surf = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, draw_rect)
            pygame.draw.rect(surf, border_color, draw_rect, 2)
            pygame.draw.rect(surf, border_color, center_rect)

            surf_flash = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
            pygame.draw.rect(surf_flash, (255, 255, 255), draw_rect)
            pygame.draw.rect(surf_flash, border_color, draw_rect, 2)
            pygame.draw.rect(surf_flash, border_color, center_rect)

            SPRITE_CACHE[key] = (surf, surf_flash)

        return SPRITE_CACHE[key]

    # ─────────────────────────────────────────────────────────
    # IA
    # ─────────────────────────────────────────────────────────

    def update_ai(self, player_pos, spatial_grid):
        if not self.is_alive:
            return

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx * dx + dy * dy
        dist = math.sqrt(dist_sq) if dist_sq > 0.0001 else 0.001

        dir_x = dx / dist
        dir_y = dy / dist

        # ── Spitter: mantiene distancia preferida ──────────────────────
        if self.special == 'spit':
            preferred = 270
            if dist < preferred * 0.6:
                dir_x, dir_y = -dir_x, -dir_y
                current_move_speed = self.base_speed * self.speed_variance * 0.9
            elif dist > preferred * 1.5:
                current_move_speed = self.base_speed * self.speed_variance
            else:
                current_move_speed = 0  # Quieto en la zona cómoda
        else:
            attack_range_sq = (self.size * 0.6 + 10) ** 2
            current_move_speed = (
                self.base_speed * self.speed_variance
                if dist_sq > attack_range_sq else 0
            )

        # ── Separación entre enemigos ──────────────────────────────────
        push_x, push_y = 0, 0
        if spatial_grid:
            neighbors = spatial_grid.get_nearby(self.x, self.y, radius=1)
            collision_radius_sq = (self.radius * 2) ** 2
            count = 0
            max_neighbors = 12 if len(neighbors) > 500 else 8

            for other in neighbors:
                if other is self or not other.is_alive:
                    continue
                if count >= max_neighbors:
                    break
                odx = self.x - other.x
                ody = self.y - other.y
                odist_sq = odx * odx + ody * ody
                if 0 < odist_sq < collision_radius_sq:
                    inv_odist = 1.0 / math.sqrt(odist_sq)
                    overlap = (self.radius * 2) - (odist_sq * inv_odist)
                    push_strength = overlap * 0.04
                    push_x += (odx * inv_odist) * push_strength
                    push_y += (ody * inv_odist) * push_strength
                    count += 1

        self.vx = (dir_x * current_move_speed) + push_x
        self.vy = (dir_y * current_move_speed) + push_y

    def update_special(self, player_pos, dt=1.0):
        """
        Evalúa habilidades especiales.
        Retorna un dict si se activa algo, o None.

        Tipos de retorno:
          {'type': 'explosion', 'x', 'y', 'damage', 'radius', 'kill_self': True}
          {'type': 'projectile', 'x', 'y', 'angle', 'speed', 'damage',
                                 'lifetime', 'color', 'radius', 'proj_type'}
        """
        if not self.is_alive or not self.special:
            return None

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx * dx + dy * dy

        # ── Exploder ───────────────────────────────────────────────────
        if self.special == 'explode':
            # Actualiza el nivel de carga visual
            if dist_sq < 170 ** 2:
                self.charge_level = min(1.0, self.charge_level + 0.035 * dt)
            else:
                self.charge_level = max(0.0, self.charge_level - 0.025 * dt)

            # Explosión cuando está muy cerca y el timer lo permite
            if self.special_cooldown_timer <= 0 and dist_sq < 85 ** 2:
                self.special_cooldown_timer = 999999
                return {
                    'type': 'explosion',
                    'x': self.x, 'y': self.y,
                    'damage': 65, 'radius': 140,
                    'kill_self': True,
                }
            return None

        # ── Cooldown general ───────────────────────────────────────────
        if self.special_cooldown_timer > 0:
            self.special_cooldown_timer -= dt
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0.0001 else 0.001
        angle = math.atan2(dy, dx)

        # ── Spitter ───────────────────────────────────────────────────
        if self.special == 'spit' and dist_sq < 530 ** 2:
            self.special_cooldown_timer = self.special_cooldown_max
            return {
                'type': 'projectile',
                'x': self.x, 'y': self.y,
                'angle': angle, 'speed': 5.0,
                'damage': 14, 'lifetime': 175,
                'color': (60, 230, 20), 'radius': 8,
                'proj_type': 'acid',
            }

        # ── Tank ──────────────────────────────────────────────────────
        elif self.special == 'rock' and dist_sq < 700 ** 2:
            self.special_cooldown_timer = self.special_cooldown_max
            # Leve imprecisión para que no sea imposible esquivar
            wobble = random.uniform(-0.18, 0.18)
            return {
                'type': 'projectile',
                'x': self.x, 'y': self.y,
                'angle': angle + wobble, 'speed': 5.8,
                'damage': 40, 'lifetime': 145,
                'color': (165, 145, 110), 'radius': 14,
                'proj_type': 'rock',
            }

        # Si estaba fuera de rango, reiniciar cooldown para el siguiente intento
        self.special_cooldown_timer = self.special_cooldown_max
        return None

    # ─────────────────────────────────────────────────────────
    # Física
    # ─────────────────────────────────────────────────────────

    def update_physics(self, dt=1.0):
        if not self.is_alive:
            return

        self.x += (self.vx + self.knockback_x) * dt
        self.y += (self.vy + self.knockback_y) * dt

        if abs(self.knockback_x) > 0.01 or abs(self.knockback_y) > 0.01:
            self.knockback_x *= self.knockback_decay ** dt
            self.knockback_y *= self.knockback_decay ** dt
            if abs(self.knockback_x) < 0.1: self.knockback_x = 0
            if abs(self.knockback_y) < 0.1: self.knockback_y = 0

        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)

        if self.attack_cooldown > 0: self.attack_cooldown -= 1 * dt
        if self.damage_flash > 0:    self.damage_flash   -= 1 * dt

    def update(self, particle_system=None, dt=1.0):
        if not self.is_alive:
            return

        if self.bleed_intensity > 0:
            self.bleed_intensity -= self.bleed_decay * dt
            if self.bleed_intensity < 0:
                self.bleed_intensity = 0

            if self.bleed_drip_cooldown > 0:
                self.bleed_drip_cooldown -= 1 * dt

            if self.bleed_drip_cooldown <= 0 and particle_system:
                delay = max(2, 20 - (self.bleed_intensity * 0.8))
                particle_system.create_blood_drip(self.x, self.y, self.bleed_intensity)
                self.bleed_drip_cooldown = delay

    # ─────────────────────────────────────────────────────────
    # Combate
    # ─────────────────────────────────────────────────────────

    def can_attack(self):
        return self.attack_cooldown <= 0

    def attack(self, player):
        if not self.is_alive or not self.can_attack():
            return False
        if self.special == 'explode':
            return False  # Solo daña por explosión
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.attack_cooldown = self.attack_delay
            return True
        return False

    def take_damage(self, damage):
        if not self.is_alive:
            return False

        self.health -= damage
        self.damage_flash = 10
        self.bleed_intensity += damage
        if self.bleed_intensity > 40:
            self.bleed_intensity = 40

        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True
        return False

    def apply_knockback(self, projectile_x, projectile_y, force=5):
        dx = self.x - projectile_x
        dy = self.y - projectile_y
        dist_sq = dx * dx + dy * dy
        if dist_sq > 1:
            inv_dist = 1.0 / math.sqrt(dist_sq)
            dx *= inv_dist
            dy *= inv_dist
            size_factor = 1.0 / self.TYPES[self.enemy_type]['size_mult']
            self.knockback_x = dx * force * size_factor
            self.knockback_y = dy * force * size_factor

    # ─────────────────────────────────────────────────────────
    # Renderizado
    # ─────────────────────────────────────────────────────────

    def render(self, screen, camera):
        if not self.is_alive:
            return
        if not camera.is_on_screen(self.rect):
            return

        screen_pos = camera.apply_coords(self.rect.x, self.rect.y)
        cx_s = screen_pos[0] + self.hitbox_total // 2
        cy_s = screen_pos[1] + self.hitbox_total // 2

        # ── Glow naranja del Exploder cuando se carga ──────────────────
        if self.special == 'explode' and self.charge_level > 0.05:
            gr = int(self.hitbox_total * 0.6 + self.charge_level * 20)
            ga = int(self.charge_level * 180)
            gs = pygame.Surface((gr * 2, gr * 2), pygame.SRCALPHA)
            pygame.draw.circle(gs, (255, 100, 0, ga), (gr, gr), gr)
            screen.blit(gs, (cx_s - gr, cy_s - gr))

        screen.blit(self.image, screen_pos)

        if self.damage_flash > 0:
            alpha = int(min(255, max(0, self.damage_flash * 25.5)))
            self.flash_image.set_alpha(alpha)
            screen.blit(self.flash_image, screen_pos)

        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 4
            health_width = (self.health / self.max_health) * bar_width
            offset = (self.hitbox_total - self.size) // 2
            bar_x = screen_pos[0] + offset
            bar_y = screen_pos[1] + offset - 7

            pygame.draw.rect(screen, (60, 0, 0),
                             (bar_x, bar_y, bar_width, bar_height))
            hp_color = (
                (255, 0, 0)
                if self.health < self.max_health * 0.3
                else (255, 100, 0)
            )
            pygame.draw.rect(screen, hp_color,
                             (bar_x, bar_y, health_width, bar_height))

    # ─────────────────────────────────────────────────────────
    # Spawn helper (legado)
    # ─────────────────────────────────────────────────────────

    @staticmethod
    def spawn_random(speed_multiplier=1.0, wave=1):
        side = random.choice(['top', 'bottom', 'left', 'right'])

        if side == 'top':
            x = random.randint(0, WORLD_WIDTH);  y = -30
        elif side == 'bottom':
            x = random.randint(0, WORLD_WIDTH);  y = WORLD_HEIGHT + 30
        elif side == 'left':
            x = -30;  y = random.randint(0, WORLD_HEIGHT)
        else:
            x = WORLD_WIDTH + 30;  y = random.randint(0, WORLD_HEIGHT)

        rand = random.random()
        if wave < 3:
            enemy_type = 'small' if rand < 0.3 else 'normal'
        elif wave < 6:
            if rand < 0.2:   enemy_type = 'small'
            elif rand < 0.7: enemy_type = 'normal'
            else:            enemy_type = 'large'
        else:
            if rand < 0.15:  enemy_type = 'small'
            elif rand < 0.5: enemy_type = 'normal'
            elif rand < 0.8: enemy_type = 'large'
            else:            enemy_type = 'tank'

        return Enemy(x, y, speed_multiplier, enemy_type)