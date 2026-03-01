import pygame
import random
import math

# --- PALETA DE COLORES GORE ---
BLOOD_RED = (160, 0, 0)
DARK_BLOOD = (80, 0, 0)
GUTS_PINK = (180, 90, 100)
BRIGHT_RED = (200, 20, 20)

class Particle:
    __slots__ = (
        'x', 'y', 'color', 'size', 'original_size', 'lifetime',
        'max_lifetime', 'is_alive', 'vel_x', 'vel_y',
        'gravity', 'friction', 'is_chunk', 'is_liquid', 'angle'
    )
    def __init__(self, x, y, color, size, lifetime, velocity, gravity=0, friction=0.9, is_chunk=False, is_liquid=True):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.original_size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.is_alive = True
        self.vel_x, self.vel_y = velocity
        self.gravity = gravity
        self.friction = friction
        self.is_chunk = is_chunk
        self.is_liquid = is_liquid
        self.angle = 0

    def update(self, dt=1.0):
        if not self.is_alive:
            return

        self.vel_y += self.gravity * dt
        self.vel_x *= (self.friction ** dt)
        self.vel_y *= (self.friction ** dt)

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

        # OPTIMIZACIÓN: comparación de cuadrados, sin math.sqrt
        speed_sq = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        if self.is_liquid and speed_sq < 0.01 and not self.is_chunk:
            self.vel_x = 0
            self.vel_y = 0
            self.lifetime -= 0.2 * dt
        else:
            self.lifetime -= 1 * dt

        if self.lifetime <= 0:
            self.is_alive = False


class ParticleSystem:
    def __init__(self):
        self.pool = None
        self.max_active_particles = 1500
        self.particle_count = 0
        self.quality = 2  # 0=Low, 1=Mid, 2=High

    def set_pool(self, particle_pool):
        self.pool = particle_pool

    def set_quality(self, level):
        self.quality = level

    def create_blood_splatter(self, x, y, direction_vector=None, force=1.2, count=6):
        """
        Sangrado direccional (Impactos de bala).
        RESTAURADO: 3x en quality 2 = 18 partículas por impacto.
        El rendimiento se mantiene porque las partículas que se detienen
        se hornean instantáneamente al blood_surface en update_and_bake().
        """
        if self.quality == 2:
            actual_count = count * 3   # RESTAURADO: 18 partículas por impacto
        elif self.quality == 1:
            actual_count = count
        else:
            actual_count = 2

        for _ in range(actual_count):
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                spread = random.uniform(-0.55, 0.55)
                angle = base_angle + spread
                speed = random.uniform(4, 13) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 7)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED, DARK_BLOOD])
            size = random.randint(2, 5)

            self.pool.get(
                x, y, color,
                size=size,
                lifetime=random.randint(40, 80),   # RESTAURADO
                velocity=velocity,
                gravity=0,
                friction=0.84,
                is_liquid=True
            )

    def create_blood_drip(self, x, y, intensity=1.0):
        """
        Goteo dinámico de sangre.
        vel=(0,0) → se hornea al primer frame → costo de pool casi nulo.
        """
        if self.quality == 0:
            return

        base_size = min(10, 2 + int(intensity * 0.3))
        drops_count = 1
        if intensity > 15:
            drops_count = random.randint(1, 2)

        for _ in range(drops_count):
            spawn_x = x + random.uniform(-4, 4)
            spawn_y = y + random.uniform(-4, 4)

            color = DARK_BLOOD if intensity > 10 else random.choice([BLOOD_RED, DARK_BLOOD])
            size = random.randint(base_size, base_size + 3)

            self.pool.get(
                spawn_x, spawn_y,
                color,
                size=size,
                lifetime=random.randint(60, 120),
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_blood_pool(self, x, y):
        """
        Charco grande irregular.
        RESTAURADO a conteos máximos.
        Los blobs con vel=(0,0) se hornean al primer frame → pool liberado inmediatamente.
        Resultado: charcos grandes permanentes sin costo sostenido en el pool.
        """
        if self.quality == 2:
            blobs = random.randint(4, 8)   # RESTAURADO + mejorado
        elif self.quality == 1:
            blobs = random.randint(2, 4)
        else:
            blobs = 1

        for _ in range(blobs):
            offset_dist = random.uniform(0, 18) if blobs > 1 else 0
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist

            size = random.randint(10, 24)   # RESTAURADO: charcos grandes

            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=size,
                lifetime=random.randint(60, 120),   # Corto: baked en 1er frame
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """
        Muerte gore: Niebla roja + Trozos de carne + Charco.
        RESTAURADO a conteos máximos.
        Niebla/charcos (estáticos) se hornean inmediatamente.
        Solo los chunks (is_chunk=True) persisten como partículas dinámicas.
        """
        if self.quality == 2:
            mist_count = 22    # RESTAURADO (levemente menos que 25 original)
            chunk_count = 9    # RESTAURADO (levemente menos que 10 original)
            pool_spawn = True
        elif self.quality == 1:
            mist_count = 10
            chunk_count = 4
            pool_spawn = True
        else:
            mist_count = 4
            chunk_count = 0
            pool_spawn = False

        if pool_spawn:
            self.create_blood_pool(x, y)

        # Niebla de sangre (partículas rápidas que se detienen → se hornean)
        for _ in range(mist_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 10)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED])

            self.pool.get(
                x, y, color,
                size=random.randint(3, 6),     # RESTAURADO
                lifetime=random.randint(20, 45),
                velocity=velocity,
                gravity=0,
                friction=0.89
            )

        # Trozos de carne (is_chunk=True → NO se hornean, persisten y rebotan)
        for _ in range(chunk_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(5, 12)     # RESTAURADO
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([DARK_BLOOD, GUTS_PINK])

            self.pool.get(
                x, y, color,
                size=random.randint(4, 9),     # RESTAURADO
                lifetime=random.randint(100, 300),  # Chunks persisten como decals
                velocity=velocity,
                gravity=0,
                friction=0.91,
                is_chunk=True
            )

    def update(self, dt=1.0): pass
    def render(self, screen, camera): pass
    def clear(self):
        if hasattr(self, 'pool'):
            self.pool.clear()