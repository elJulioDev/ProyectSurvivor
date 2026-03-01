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
        
        # OPTIMIZACIÓN: evitar math.sqrt usando comparación de cuadrados
        # 0.01 = 0.1^2 (umbral de velocidad al cuadrado)
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
        self.max_active_particles = 800
        self.particle_count = 0
        self.quality = 2 # 0=Low, 1=Mid, 2=High
        
    def set_pool(self, particle_pool):
        self.pool = particle_pool

    def set_quality(self, level):
        self.quality = level
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.2, count=4):
        """
        Sangrado direccional (Impactos de bala).
        OPTIMIZADO: quality 2 usa 2x en lugar de 3x para reducir picos de CPU.
        """
        if self.quality == 2:
            actual_count = count * 2   # era 3x → reducido a 2x
        elif self.quality == 1:
            actual_count = count
        else:
            actual_count = 2

        for _ in range(actual_count):
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                spread = random.uniform(-0.5, 0.5)
                angle = base_angle + spread
                speed = random.uniform(4, 12) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED, DARK_BLOOD])
            size = random.randint(2, 5)
            
            self.pool.get(
                x, y, color,
                size=size,
                lifetime=random.randint(30, 60),  # era 40-80 → reducido
                velocity=velocity,
                gravity=0,
                friction=0.85,
                is_liquid=True
            )

    def create_blood_drip(self, x, y, intensity=1.0):
        """Goteo dinámico — sin cambios, se llama con poca frecuencia."""
        if self.quality == 0: 
            return

        base_size = min(10, 2 + int(intensity * 0.3))
        drops_count = 1
        if intensity > 15:
            drops_count = random.randint(1, 2)
        
        for _ in range(drops_count):
            spawn_x = x + random.uniform(-4, 4)
            spawn_y = y + random.uniform(-4, 4)
            
            if intensity > 10:
                color = DARK_BLOOD
            else:
                color = random.choice([BLOOD_RED, DARK_BLOOD])

            size = random.randint(base_size, base_size + 3)
            
            self.pool.get(
                spawn_x, spawn_y,
                color,
                size=size,
                lifetime=random.randint(80, 150),  # era 100-200 → reducido para liberar pool más rápido
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )
    
    def create_blood_pool(self, x, y):
        """
        Charco grande irregular.
        OPTIMIZADO: menos blobs en quality 2 para no saturar el pool.
        """
        if self.quality == 2:
            blobs = random.randint(2, 4)   # era 3-6 → reducido
        elif self.quality == 1:
            blobs = 2
        else:
            blobs = 1
            
        for _ in range(blobs):
            offset_dist = random.uniform(0, 15) if blobs > 1 else 0
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist
            
            size = random.randint(10, 20)  # era 10-22
            
            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=size,
                lifetime=random.randint(600, 1000),  # era 900-1500 → reducido para liberar pool
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """
        Muerte gore: Niebla roja + Trozos de carne + Charco.
        OPTIMIZADO: conteos reducidos en quality 2 para evitar picos al matar.
        """
        if self.quality == 2:   # Antes: mist=25, chunk=10
            mist_count = 14
            chunk_count = 6
            pool_spawn = True
        elif self.quality == 1:  # Antes: mist=10, chunk=4
            mist_count = 7
            chunk_count = 3
            pool_spawn = True
        else:
            mist_count = 4
            chunk_count = 0
            pool_spawn = False

        if pool_spawn:
            self.create_blood_pool(x, y)

        # Niebla de sangre
        for _ in range(mist_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 9)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED])
            
            self.pool.get(
                x, y, color, 
                size=random.randint(3, 5),   # era 3-6
                lifetime=random.randint(18, 38),  # era 20-45 → ligeramente reducido
                velocity=velocity,
                gravity=0,
                friction=0.9
            )

        # Trozos de carne
        for _ in range(chunk_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(4, 10)   # era 5-12
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([DARK_BLOOD, GUTS_PINK])
            
            self.pool.get(
                x, y, color,
                size=random.randint(4, 8),   # era 4-9
                lifetime=random.randint(80, 220),  # era 100-300
                velocity=velocity,
                gravity=0,
                friction=0.92,
                is_chunk=True
            )
    
    def update(self, dt=1.0): pass
    def render(self, screen, camera): pass
    def clear(self):
        if hasattr(self, 'pool'): 
            self.pool.clear()