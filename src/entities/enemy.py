"""
Enemy optimizado:
- Glow del Exploder: caché de superficies por (radius_bucket, alpha_bucket)
  → elimina 1 Surface() allocation por exploder por frame.
- AI anti-clustering mejorada:
    · Carril determinista por enemigo (offset lateral único fijo desde spawn)
    · Separación cuadrática con radio ampliado (4x radio)
    · Predicción del jugador (apuntan a posición futura, no actual)
- Tank: special=None, sin proyectiles de roca
- Exploder: size_mult 0.8→1.4, speed_mult 2.1→0.75 (más grande y lento)
"""
import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED,
    WORLD_WIDTH, WORLD_HEIGHT,
)

SPRITE_CACHE: dict = {}

# Cache de glow surfaces: (radius_bucket, alpha_bucket) -> Surface
_GLOW_CACHE: dict = {}

def _get_glow_surface(radius: int, alpha: int) -> pygame.Surface:
    """Crea o reutiliza una superficie de glow circular."""
    rb = (radius + 4) // 5 * 5
    ab = max(0, min(255, (alpha + 7) // 15 * 15))
    key = (rb, ab)
    try:
        return _GLOW_CACHE[key]
    except KeyError:
        surf = pygame.Surface((rb * 2, rb * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 100, 0, ab), (rb, rb), rb)
        _GLOW_CACHE[key] = surf
        return surf


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
            'special': None, 'special_cooldown': 0,
        },
        'exploder': {
            # NERF: más grande (0.8→1.4) y más lento (2.1→0.75)
            'size_mult': 1.4,  'health': 70,  'speed_mult': 0.75, 'damage': 0,
            'color': (255, 80, 20),   'points': 22,
            'special': 'explode', 'special_cooldown': 0,
        },
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
        self.color  = type_data['color']
        self.damage = type_data['damage']
        self.max_health = int(type_data['health'] * health_mult)
        self.health = self.max_health
        self.points = type_data['points']

        self.special = type_data.get('special', None)
        self.special_cooldown_max   = type_data.get('special_cooldown', 0)
        self.special_cooldown_timer = (
            random.randint(0, max(1, self.special_cooldown_max // 2))
            if self.special_cooldown_max > 0 else 0
        )

        self.hitbox_padding = 10
        self.hitbox_total   = self.size + self.hitbox_padding

        self.image, self.flash_image = self._get_cached_sprite(
            self.size, self.hitbox_total, self.color
        )
        self.rect = pygame.Rect(0, 0, self.hitbox_total, self.hitbox_total)
        self.rect.center = (int(x), int(y))

        self.radius = self.size * 0.40
        self.speed_variance = random.uniform(0.9, 1.1)

        self.vx = 0.0
        self.vy = 0.0
        self.is_alive = True
        self.attack_cooldown = 0
        self.attack_delay    = 60

        self.knockback_x = 0.0
        self.knockback_y = 0.0
        self.knockback_decay = 0.88

        self.damage_flash  = 0
        self.bleed_intensity   = 0.0
        self.bleed_decay       = 0.3
        self.bleed_drip_cooldown = 0

        self.charge_level = 0.0

        # Carril determinista: valor en [-1, 1] único por instancia.
        # Basado en la posición de spawn → cada enemigo tiene su propio
        # "carril" lateral de aproximación, creando patrón en abanico.
        self._lane = math.sin(x * 0.0071 + y * 0.0053)

    # ------------------------------------------------------------------
    def recycle(self, x, y, speed_multiplier=1.0, enemy_type=None, health_mult=1.0):
        if enemy_type and enemy_type != self.enemy_type:
            self.enemy_type = enemy_type
            type_data = self.TYPES[enemy_type]
            self.size   = int(ENEMY_SIZE * type_data['size_mult'])
            self.color  = type_data['color']
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
        self.health     = self.max_health
        self.speed_variance = random.uniform(0.9, 1.1)
        self.special_cooldown_timer = (
            random.randint(0, max(1, self.special_cooldown_max // 2))
            if self.special_cooldown_max > 0 else 0
        )

        self.is_alive = True
        self.vx = self.vy = 0.0
        self.knockback_x = self.knockback_y = 0.0
        self.damage_flash = 0
        self.bleed_intensity = 0.0
        self.bleed_drip_cooldown = 0
        self.attack_cooldown = 0
        self.charge_level = 0.0

        # Recalcular carril con nueva posición de spawn
        self._lane = math.sin(x * 0.0071 + y * 0.0053)

    def teleport_to(self, x, y):
        self.x = x
        self.y = y
        self.rect.center = (int(x), int(y))
        self.vx = self.vy = 0.0
        self.knockback_x = self.knockback_y = 0.0
        # Nuevo carril al teletransportarse
        self._lane = math.sin(x * 0.0071 + y * 0.0053)

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

    def update_ai(self, player_pos, spatial_grid, player_vel=None):
        """
        IA anti-clustering con tres mecanismos combinados:

        1. PREDICCIÓN DEL JUGADOR
           Cada enemigo apunta a donde ESTARÁ el jugador en unos frames,
           no donde está ahora. Enemigos de distintos ángulos predicen
           posiciones levemente distintas → se dispersan sin lógica extra.

        2. CARRIL DETERMINISTA (_lane)
           Cada enemigo tiene un offset lateral fijo [-1..1] calculado
           desde su posición de spawn. Todos los 'lane=+0.5' van por un
           lado, los 'lane=-0.5' por el otro → patrón en abanico natural.

        3. SEPARACIÓN CUADRÁTICA AMPLIADA
           Radio = 4× el radio del enemigo. Fuerza ∝ overlap².
           Suave cuando están lejos, muy agresiva cuando se tocan.
        """
        if not self.is_alive:
            return

        ex, ey = self.x, self.y
        px, py = player_pos

        # --- 1. PREDICCIÓN ---
        if player_vel is not None:
            pvx, pvy = player_vel
            # Tiempo de predicción: proporcional a la distancia, limitado
            raw_dist = math.sqrt((px - ex)**2 + (py - ey)**2)
            predict_t = min(18.0, raw_dist / max(1.0, self.base_speed * 2.5))
            target_x = px + pvx * predict_t * 0.55
            target_y = py + pvy * predict_t * 0.55
        else:
            target_x, target_y = px, py

        dx = target_x - ex
        dy = target_y - ey
        dist_sq = dx * dx + dy * dy
        if dist_sq < 0.0001:
            dist_sq = 0.0001
        dist = math.sqrt(dist_sq)
        inv_dist = 1.0 / dist
        dir_x = dx * inv_dist
        dir_y = dy * inv_dist

        # Distancia real al jugador para lógica de ataque/rango
        real_dist_sq = (px - ex)**2 + (py - ey)**2

        special = self.special

        if special == 'spit':
            preferred = 270.0
            pref_near = preferred * 0.6
            pref_far  = preferred * 1.5
            real_dist = math.sqrt(real_dist_sq) if real_dist_sq > 0.0001 else 0.001
            if real_dist < pref_near:
                dir_x = -(px - ex) / max(real_dist, 0.001)
                dir_y = -(py - ey) / max(real_dist, 0.001)
                current_move_speed = self.base_speed * self.speed_variance * 0.9
            elif real_dist > pref_far:
                current_move_speed = self.base_speed * self.speed_variance
            else:
                current_move_speed = 0.0
        else:
            attack_range_sq = (self.size * 0.6 + 10) ** 2
            current_move_speed = (
                self.base_speed * self.speed_variance
                if real_dist_sq > attack_range_sq else 0.0
            )

        # --- 2. SEPARACIÓN CUADRÁTICA AMPLIADA ---
        # ANTI-JITTER: tres medidas combinadas:
        #   a) Fuerza reducida a 0.18 (era 0.28) → menos overshooting por par
        #   b) Push dividido por sqrt(count) → 16 vecinos no acumulan 16× fuerza
        #   c) Cap final del push → imposible que la suma supere 1.2× base_speed
        push_x = push_y = 0.0
        if spatial_grid:
            neighbors = spatial_grid.get_nearby(ex, ey, radius=1)
            sep_radius = self.radius * 4.0
            cr_sq = sep_radius * sep_radius
            count = 0
            max_n = 20

            for other in neighbors:
                if other is self or not other.is_alive:
                    continue
                if count >= max_n:
                    break
                odx = ex - other.x
                ody = ey - other.y
                odist_sq = odx * odx + ody * ody
                if 0 < odist_sq < cr_sq:
                    odist = math.sqrt(odist_sq)
                    inv_od = 1.0 / odist
                    overlap = sep_radius - odist
                    # Coeficiente reducido: 0.18 en lugar de 0.28
                    ps = overlap * (overlap / sep_radius) * 0.18
                    push_x += odx * inv_od * ps
                    push_y += ody * inv_od * ps
                    count += 1

            # b) Escalar por 1/√count: evita que muchos vecinos acumulen
            #    fuerza explosiva — con 16 vecinos la fuerza se divide por 4
            if count > 1:
                inv_sqrt = 1.0 / math.sqrt(count)
                push_x *= inv_sqrt
                push_y *= inv_sqrt

            # c) Cap duro: el push nunca supera 1.2× la velocidad base
            push_sq = push_x * push_x + push_y * push_y
            max_push = self.base_speed * 1.2
            if push_sq > max_push * max_push:
                inv_pm = max_push / math.sqrt(push_sq)
                push_x *= inv_pm
                push_y *= inv_pm

        # --- 3. CARRIL DETERMINISTA ---
        # Vector perpendicular a la dirección de movimiento
        perp_x = -dir_y
        perp_y = dir_x

        # _lane ∈ [-1, 1]: offset lateral fijo, único por enemigo.
        # Produce distribución en abanico: izquierda, centro, derecha.
        # Escala con la velocidad para que el efecto sea proporcional.
        lateral_strength = 0.38 * current_move_speed
        lane_vx = perp_x * self._lane * lateral_strength
        lane_vy = perp_y * self._lane * lateral_strength

        # --- ANTI-JITTER: lerp de velocidad ---
        # En lugar de asignar vx/vy directamente (causa oscilación inmediata),
        # interpolamos al 40% hacia el objetivo cada frame.
        # Resultado: la velocidad no puede cambiar de dirección de un frame
        # al siguiente → el temblor desaparece aunque haya muchos vecinos.
        target_vx = dir_x * current_move_speed + push_x + lane_vx
        target_vy = dir_y * current_move_speed + push_y + lane_vy

        lerp = 0.40
        self.vx = self.vx * (1.0 - lerp) + target_vx * lerp
        self.vy = self.vy * (1.0 - lerp) + target_vy * lerp

    def update_special(self, player_pos, dt=1.0):
        if not self.is_alive or not self.special:
            return None

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx * dx + dy * dy

        if self.special == 'explode':
            if dist_sq < 170 ** 2:
                self.charge_level = min(1.0, self.charge_level + 0.035 * dt)
            else:
                self.charge_level = max(0.0, self.charge_level - 0.025 * dt)

            if self.special_cooldown_timer <= 0 and dist_sq < 85 ** 2:
                self.special_cooldown_timer = 999999
                return {
                    'type': 'explosion',
                    'x': self.x, 'y': self.y,
                    'damage': 65, 'radius': 140,
                    'kill_self': True,
                }
            return None

        if self.special_cooldown_timer > 0:
            self.special_cooldown_timer -= dt
            return None

        dist = math.sqrt(dist_sq) if dist_sq > 0.0001 else 0.001
        angle = math.atan2(dy, dx)

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

        self.special_cooldown_timer = self.special_cooldown_max
        return None

    def update_physics(self, dt=1.0):
        if not self.is_alive:
            return

        self.x += (self.vx + self.knockback_x) * dt
        self.y += (self.vy + self.knockback_y) * dt

        kx, ky = self.knockback_x, self.knockback_y
        if abs(kx) > 0.01 or abs(ky) > 0.01:
            decay = self.knockback_decay ** dt
            kx *= decay
            ky *= decay
            if abs(kx) < 0.1: kx = 0.0
            if abs(ky) < 0.1: ky = 0.0
            self.knockback_x, self.knockback_y = kx, ky

        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)

        if self.attack_cooldown > 0:
            self.attack_cooldown -= dt
        if self.damage_flash > 0:
            self.damage_flash -= dt

    def update(self, particle_system=None, dt=1.0):
        if not self.is_alive:
            return

        if self.bleed_intensity > 0:
            self.bleed_intensity -= self.bleed_decay * dt
            if self.bleed_intensity < 0:
                self.bleed_intensity = 0.0
            else:
                self.bleed_drip_cooldown -= dt
                if self.bleed_drip_cooldown <= 0 and particle_system:
                    delay = max(2, 20 - (self.bleed_intensity * 0.8))
                    particle_system.create_blood_drip(self.x, self.y, self.bleed_intensity)
                    self.bleed_drip_cooldown = delay

    def can_attack(self):
        return self.attack_cooldown <= 0

    def attack(self, player):
        if not self.is_alive or not self.can_attack():
            return False
        if self.special == 'explode':
            return False
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
        self.bleed_intensity = min(40.0, self.bleed_intensity + damage)

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
            size_factor = 1.0 / self.TYPES[self.enemy_type]['size_mult']
            self.knockback_x = dx * inv_dist * force * size_factor
            self.knockback_y = dy * inv_dist * force * size_factor

    def render(self, screen, camera):
        if not self.is_alive:
            return
        if not camera.is_on_screen(self.rect):
            return

        sp = camera.apply_coords(self.rect.x, self.rect.y)
        sx, sy = sp[0], sp[1]
        ht2 = self.hitbox_total // 2
        cx_s = sx + ht2
        cy_s = sy + ht2

        # Glow del Exploder — usa caché
        cl = self.charge_level
        if self.special == 'explode' and cl > 0.05:
            gr = int(self.hitbox_total * 0.6 + cl * 20)
            ga = int(cl * 180)
            glow_surf = _get_glow_surface(gr, ga)
            screen.blit(glow_surf, (cx_s - gr, cy_s - gr))

        screen.blit(self.image, (sx, sy))

        if self.damage_flash > 0:
            alpha = min(255, int(self.damage_flash * 25.5))
            self.flash_image.set_alpha(alpha)
            screen.blit(self.flash_image, (sx, sy))

        if self.health < self.max_health:
            bar_width = self.size
            health_width = int((self.health / self.max_health) * bar_width)
            offset = (self.hitbox_total - self.size) // 2
            bar_x = int(sx + offset)
            bar_y = int(sy + offset - 7)
            BAR_H = 4

            pygame.draw.rect(screen, (60, 0, 0),
                             (bar_x, bar_y, bar_width, BAR_H))
            hp_color = (
                (255, 0, 0) if self.health < self.max_health * 0.3
                else (255, 100, 0)
            )
            if health_width > 0:
                pygame.draw.rect(screen, hp_color,
                                 (bar_x, bar_y, health_width, BAR_H))

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
            else:             enemy_type = 'large'
        else:
            if rand < 0.15:  enemy_type = 'small'
            elif rand < 0.5: enemy_type = 'normal'
            elif rand < 0.8: enemy_type = 'large'
            else:             enemy_type = 'tank'

        return Enemy(x, y, speed_multiplier, enemy_type)