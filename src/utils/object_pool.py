"""
ObjectPool optimizado:
- ParticlePool.render_all(): pasa ÚNICA (antes 2 pasadas por frame).
  Devuelve {floor_count, air_count} con un solo loop de 800 partículas.
- _blit_floor / _blit_air: listas pre-asignadas, se vacían con .clear()
  en lugar de crear nueva lista cada frame.
- bake_static_blood(): llamado externamente cada N frames (no cada frame).
- ProjectilePool sin cambios relevantes (ya es eficiente).
"""
import pygame
import math
from entities.projectile import Projectile
from entities.particle   import Particle
from settings import WINDOW_HEIGHT, WINDOW_WIDTH

BLOOD_RED  = (160,  0,  0)
DARK_BLOOD = ( 80,  0,  0)
GUTS_PINK  = (180, 90, 100)
BRIGHT_RED = (200, 20, 20)

class ProjectilePool:
    def __init__(self, initial_size=500):
        self.pool   = []
        self.active = []
        for _ in range(initial_size):
            p = Projectile(0, 0, 0)
            p.is_alive = False
            self.pool.append(p)

    def get(self, x, y, angle, speed=10, damage=25, penetration=1,
            lifetime=120, image_type='circle'):
        p = self.pool.pop() if self.pool else Projectile(0, 0, 0)
        p.x          = x
        p.y          = y
        p.angle      = angle
        p.speed      = speed
        p.damage     = damage
        p.penetration = penetration
        p.lifetime   = lifetime
        p.image_type = image_type
        p.is_alive   = True
        p.vel_x = math.cos(angle) * speed
        p.vel_y = math.sin(angle) * speed
        p.rect.x = int(x - p.size // 2)
        p.rect.y = int(y - p.size // 2)
        p.hit_enemies.clear()
        self.active.append(p)
        return p

    def return_to_pool(self, projectile):
        if projectile in self.active:
            self.active.remove(projectile)
            projectile.is_alive = False
            self.pool.append(projectile)

    def update_all(self, dt):
        for p in self.active[:]:
            p.update(dt)
            if not p.is_alive:
                self.return_to_pool(p)

    def clear(self):
        for p in self.active[:]:
            self.return_to_pool(p)

class ParticlePool:
    """
    Pool de partículas con render de pasada ÚNICA y baking por intervalo.
    """
    def __init__(self, capacity=800):
        self.capacity   = capacity
        self.pool       = [Particle(0, 0, (0, 0, 0), 0, 0, (0, 0))
                           for _ in range(capacity)]
        for p in self.pool:
            p.is_alive = False
        self.next_index = 0

        # Listas de blit pre-asignadas (evita list() allocation por frame)
        self._blit_floor: list = []
        self._blit_air:   list = []

        # Intervalo de baking (frames entre cada bake)
        self._bake_counter  = 0
        self._bake_interval = 8   # bake cada 8 frames ≈ 7.5 veces/seg a 60fps

        # Caché de superficies gore pre-renderizadas
        self.cached_surfaces: dict = {}
        self._generate_surface_cache()

    def _generate_surface_cache(self):
        colors = [BLOOD_RED, DARK_BLOOD, GUTS_PINK, BRIGHT_RED]
        sizes  = [2, 3, 4, 6, 8, 12, 16]
        alphas = [100, 180, 255]
        for color in colors:
            for size in sizes:
                for alpha in alphas:
                    for shape in ('circle', 'chunk'):
                        key  = (shape, color, size, alpha)
                        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                        if shape == 'circle':
                            pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                        else:
                            pygame.draw.rect(surf, (*color, alpha), (0, 0, size * 2, size * 2))
                        self.cached_surfaces[key] = surf

    def get_cached_surface(self, shape, color, size, alpha):
        if color == GUTS_PINK:    ck = GUTS_PINK
        elif color == BRIGHT_RED: ck = BRIGHT_RED
        elif color[0] > 140:      ck = BLOOD_RED
        else:                     ck = DARK_BLOOD
        sk = min((2, 3, 4, 6, 8, 12, 16), key=lambda s: abs(s - size))
        ak = min((100, 180, 255),          key=lambda a: abs(a - alpha))
        return self.cached_surfaces.get((shape, ck, sk, ak))

    def get(self, x, y, color, size, lifetime, velocity,
            gravity=0, friction=0.9, is_chunk=False, is_liquid=True):
        p = self.pool[self.next_index]
        self.next_index = (self.next_index + 1) % self.capacity
        p.x           = x
        p.y           = y
        p.color       = color
        p.size        = size
        p.original_size = size
        p.lifetime    = lifetime
        p.max_lifetime = lifetime
        p.is_alive    = True
        p.vel_x, p.vel_y = velocity
        p.gravity     = gravity
        p.friction    = friction
        p.is_chunk    = is_chunk
        p.is_liquid   = is_liquid
        p.angle       = 0
        return p

    def update_all(self, dt):
        for p in self.pool:
            if p.is_alive:
                p.update(dt)

    def render_all(self, screen, camera, layer='all'):
        """
        layer = 'floor'  → solo partículas estáticas (charcos)
        layer = 'air'    → solo partículas en movimiento
        layer = 'all'    → ambas (render único — llamar UNA vez por frame)

        Retorna número de partículas renderizadas.
        """
        blit_floor = self._blit_floor
        blit_air   = self._blit_air
        blit_floor.clear()
        blit_air.clear()

        cam_x   = camera.offset_x
        cam_y   = camera.offset_y
        min_x   = -50
        max_x   = WINDOW_WIDTH  + 50
        min_y   = -50
        max_y   = WINDOW_HEIGHT + 50

        for p in self.pool:
            if not p.is_alive:
                continue

            sx = p.x + cam_x
            sy = p.y + cam_y
            if not (min_x < sx < max_x and min_y < sy < max_y):
                continue

            lr = p.lifetime / p.max_lifetime
            if lr <= 0:
                continue
            alpha = int(255 * lr)
            if alpha < 10:
                continue

            is_static = (p.is_liquid and not p.is_chunk and
                         abs(p.vel_x) < 0.5 and abs(p.vel_y) < 0.5)
            shape = 'chunk' if p.is_chunk else 'circle'

            cur_size = p.size if is_static else max(1, int(p.original_size * lr))
            surf = self.get_cached_surface(shape, p.color, cur_size, alpha)

            if surf:
                dest = (int(sx - surf.get_width()  // 2),
                        int(sy - surf.get_height() // 2))
                if is_static:
                    blit_floor.append((surf, dest))
                else:
                    blit_air.append((surf, dest))
            else:
                pygame.draw.circle(screen, p.color, (int(sx), int(sy)), cur_size)

        # Renderizar según layer
        if layer == 'floor':
            screen.blits(blit_floor)
            return len(blit_floor)
        elif layer == 'air':
            screen.blits(blit_air)
            return len(blit_air)
        else:  # 'all'
            screen.blits(blit_floor)
            screen.blits(blit_air)
            return len(blit_floor) + len(blit_air)

    def bake_static_blood(self, target_surface):
        """
        Transfiere partículas estáticas a blood_surface permanente.
        NO llamar cada frame — usa el counter interno.
        Retorna True si realmente ejecutó el bake.
        """
        self._bake_counter += 1
        if self._bake_counter < self._bake_interval:
            return False
        self._bake_counter = 0

        cached = self.cached_surfaces
        for p in self.pool:
            if not p.is_alive:
                continue
            if not (p.is_liquid and not p.is_chunk and
                    abs(p.vel_x) < 0.1 and abs(p.vel_y) < 0.1):
                continue
            surf = self.get_cached_surface('circle', p.color, p.size, 200)
            if surf:
                target_surface.blit(surf, (int(p.x - surf.get_width()  // 2),
                                           int(p.y - surf.get_height() // 2)))
                p.is_alive = False
        return True

    def clear(self):
        for p in self.pool:
            p.is_alive = False