"""
Sistema de partículas gore.

NIVELES DE CALIDAD:
  0 = CRISIS   → Solo efectos mínimos. Blood splatter: saltado completamente.
                  Viscera: 2 mist, 0 chunks, sin charco.
                  Activo cuando hay >400 enemigos visibles O >700 partículas activas.
  1 = MEDIO    → Efectos reducidos. Splatter: count/2. Viscera: 8 mist, 2 chunks.
  2 = ALTO     → Efectos completos (comportamiento original).

El nivel se controla externamente por LevelManager._update_lod().
"""
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
        self.quality = 2  # 0=Crisis, 1=Mid, 2=High

    def set_pool(self, particle_pool):
        self.pool = particle_pool

    def set_quality(self, level):
        self.quality = level

    def create_blood_splatter(self, x, y, direction_vector=None, force=1.2, count=6):
        """
        Sangrado direccional (impactos de bala).
        · quality 0 (CRISIS): saltado completamente — el impacto más frecuente.
        · quality 1:  count // 2 partículas.
        · quality 2:  count * 3 partículas (comportamiento original).
        """
        # CRISIS: skip total — impacto más frecuente, ahorra más CPU
        if self.quality == 0:
            return

        if self.quality == 2:
            actual_count = count * 3
        else:
            actual_count = max(1, count // 2)

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
                lifetime=random.randint(40, 80),
                velocity=velocity,
                gravity=0,
                friction=0.84,
                is_liquid=True
            )

    def create_blood_drip(self, x, y, intensity=1.0):
        """Goteo dinámico — saltado en CRISIS."""
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
        · quality 0: 1 blob pequeño (mínimo visual para marcar la muerte).
        · quality 1: 2-3 blobs.
        · quality 2: 4-8 blobs (original).
        """
        if self.quality == 2:
            blobs = random.randint(4, 8)
        elif self.quality == 1:
            blobs = random.randint(2, 3)
        else:
            blobs = 1   # CRISIS: solo un rastro mínimo

        for _ in range(blobs):
            offset_dist = random.uniform(0, 18) if blobs > 1 else 0
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist

            size = random.randint(10, 24) if self.quality == 2 else random.randint(6, 12)

            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=size,
                lifetime=random.randint(60, 120),
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """
        Muerte gore: Niebla roja + Trozos de carne + Charco.

        · quality 0 (CRISIS): 2 mist, 0 chunks, sin charco.
          Minimiza el impacto por frame en kills masivos (dash ninja, oleadas).
        · quality 1: 6 mist, 2 chunks, con charco pequeño.
        · quality 2: 22 mist, 9 chunks, charco grande (original).

        El throttle externo en LevelManager._on_enemy_killed() decide
        si llamar esta función o un efecto más ligero basándose en
        cuántos enemigos han muerto este frame.
        """
        if self.quality == 2:
            mist_count = 22
            chunk_count = 9
            pool_spawn = True
        elif self.quality == 1:
            mist_count = 6
            chunk_count = 2
            pool_spawn = True
        else:
            # CRISIS: mínimo que sigue siendo visualmente satisfactorio
            mist_count = 2
            chunk_count = 0
            pool_spawn = False

        if pool_spawn:
            self.create_blood_pool(x, y)

        # Niebla de sangre
        for _ in range(mist_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 10)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED])

            self.pool.get(
                x, y, color,
                size=random.randint(3, 6),
                lifetime=random.randint(20, 45),
                velocity=velocity,
                gravity=0,
                friction=0.89
            )

        # Trozos de carne (is_chunk → NO se hornean, persisten)
        for _ in range(chunk_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(5, 12)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([DARK_BLOOD, GUTS_PINK])

            self.pool.get(
                x, y, color,
                size=random.randint(4, 9),
                lifetime=random.randint(100, 300),
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