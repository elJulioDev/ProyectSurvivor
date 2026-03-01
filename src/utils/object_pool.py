"""
ObjectPool con sistema de BAKING INMEDIATO de partículas estáticas.

PARCHE 1: update_and_bake() ahora acepta cam_offset=(offset_x, offset_y)
para convertir coordenadas de mundo a coordenadas de pantalla antes de
hornear al blood_surface (que ahora es del tamaño de la ventana, no del mundo).
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
        p.prev_x     = x
        p.prev_y     = y
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
    Pool circular de partículas con baking inmediato de estáticas.

    PARCHE 1: update_and_bake() recibe cam_offset para calcular la posición
    de pantalla correcta al hornear en el blood_surface (tamaño ventana).
    """
    def __init__(self, capacity=1500):
        self.capacity   = capacity
        self.pool       = [Particle(0, 0, (0, 0, 0), 0, 0, (0, 0))
                           for _ in range(capacity)]
        for p in self.pool:
            p.is_alive = False
        self.next_index = 0

        self._alive_count = 0

        self._blit_floor: list = []
        self._blit_air:   list = []

        self._bake_interval = 1
        self._bake_counter  = 0

        self.cached_surfaces: dict = {}
        self._generate_surface_cache()

    def _generate_surface_cache(self):
        colors = [BLOOD_RED, DARK_BLOOD, GUTS_PINK, BRIGHT_RED]
        sizes  = [2, 3, 4, 6, 8, 12, 16, 20, 24]
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
        sk = min((2, 3, 4, 6, 8, 12, 16, 20, 24), key=lambda s: abs(s - size))
        ak = min((100, 180, 255),                  key=lambda a: abs(a - alpha))
        return self.cached_surfaces.get((shape, ck, sk, ak))

    def get(self, x, y, color, size, lifetime, velocity,
            gravity=0, friction=0.9, is_chunk=False, is_liquid=True):
        slot = self.pool[self.next_index]

        if slot.is_alive:
            self._alive_count -= 1

        self.next_index = (self.next_index + 1) % self.capacity

        slot.x            = x
        slot.y            = y
        slot.color        = color
        slot.size         = size
        slot.original_size = size
        slot.lifetime     = lifetime
        slot.max_lifetime = lifetime
        slot.is_alive     = True
        slot.vel_x, slot.vel_y = velocity
        slot.gravity      = gravity
        slot.friction     = friction
        slot.is_chunk     = is_chunk
        slot.is_liquid    = is_liquid
        slot.angle        = 0

        self._alive_count += 1
        return slot

    # PARCHE 1: cam_offset convierte coordenadas de mundo → pantalla para el blit
    def update_and_bake(self, dt, blood_surface=None, cam_offset=(0, 0)):
        if self._alive_count <= 0:
            self._alive_count = 0
            return

        freed = 0
        for p in self.pool:
            if not p.is_alive:
                continue

            p.update(dt)

            if not p.is_alive:
                freed += 1
                continue

            if (blood_surface is not None and
                    p.is_liquid and not p.is_chunk and
                    abs(p.vel_x) < 0.1 and abs(p.vel_y) < 0.1):
                surf = self.get_cached_surface('circle', p.color, p.size, 200)
                if surf:
                    # PARCHE 1: usar coordenadas de PANTALLA (mundo + offset cámara)
                    bx = int(p.x + cam_offset[0] - surf.get_width()  // 2)
                    by = int(p.y + cam_offset[1] - surf.get_height() // 2)
                    blood_surface.blit(surf, (bx, by))
                p.is_alive = False
                freed += 1

        self._alive_count -= freed
        if self._alive_count < 0:
            self._alive_count = 0

    def update_all(self, dt):
        """Alias de compatibilidad. Usar update_and_bake() cuando sea posible."""
        if self._alive_count <= 0:
            self._alive_count = 0
            return

        died = 0
        for p in self.pool:
            if p.is_alive:
                p.update(dt)
                if not p.is_alive:
                    died += 1
        self._alive_count -= died
        if self._alive_count < 0:
            self._alive_count = 0

    def render_all(self, screen, camera, layer='all'):
        if self._alive_count <= 0:
            return 0

        blit_floor = self._blit_floor
        blit_air   = self._blit_air
        blit_floor.clear()
        blit_air.clear()

        zoom  = camera.zoom
        cam_x = camera.offset_x
        cam_y = camera.offset_y
        min_x = -50
        max_x = WINDOW_WIDTH  + 50
        min_y = -50
        max_y = WINDOW_HEIGHT + 50

        for p in self.pool:
            if not p.is_alive:
                continue

            if zoom == 1.0:
                sx = p.x + cam_x
                sy = p.y + cam_y
            else:
                sx = p.x * zoom + cam_x
                sy = p.y * zoom + cam_y

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

        if layer == 'floor':
            screen.blits(blit_floor)
            return len(blit_floor)
        elif layer == 'air':
            screen.blits(blit_air)
            return len(blit_air)
        else:
            screen.blits(blit_floor)
            screen.blits(blit_air)
            return len(blit_floor) + len(blit_air)

    def bake_static_blood(self, target_surface):
        return False

    def clear(self):
        for p in self.pool:
            p.is_alive = False
        self._alive_count = 0