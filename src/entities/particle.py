"""
Sistema de partículas optimizado con DeltaTime y carga reducida
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
        
        # Física
        self.vel_y += self.gravity * dt
        
        # Optimización: Multiplicación simple en lugar de potencia (** dt)
        # Asumimos que dt está cerca de 1.0, el error es despreciable visualmente
        self.vel_x *= self.friction 
        self.vel_y *= self.friction 
        
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        self.lifetime -= 1 * dt
        if self.lifetime <= 0:
            self.is_alive = False

class ParticleSystem:
    def __init__(self):
        self.pool = None
    
    def set_pool(self, particle_pool):
        self.pool = particle_pool
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.0, count=4):
        """
        Sangrado direccional.
        REDUCIDO: count default bajado de 10 a 4 para mejor rendimiento.
        """
        if not hasattr(self, 'pool'): return
        
        # Limitamos el count máximo por seguridad
        safe_count = min(count, 8) 
        
        for _ in range(safe_count):
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                spread = random.uniform(-0.5, 0.5) 
                angle = base_angle + spread
                speed = random.uniform(3, 8) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 5)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED, DARK_BLOOD])
            
            self.pool.get(
                x, y, color,
                size=random.randint(2, 4),
                lifetime=random.randint(20, 40), # Vida más corta = menos carga
                velocity=velocity,
                gravity=0,
                friction=0.85,
                is_liquid=True
            )

    def create_blood_drip(self, x, y):
        """Goteo mientras camina"""
        if not hasattr(self, 'pool'): return
        
        self.pool.get(
            x + random.randint(-2, 2), 
            y + random.randint(-2, 2),
            DARK_BLOOD,
            size=random.randint(2, 4),
            lifetime=random.randint(100, 200),
            velocity=(0, 0),
            gravity=0,
            friction=0,
            is_liquid=True
        )
    
    def create_blood_pool(self, x, y):
        """Charco estático"""
        if not hasattr(self, 'pool'): return
        
        # Reducido de 3-7 a 1-3 blobs
        blobs = random.randint(1, 3)
        for _ in range(blobs):
            offset = random.uniform(0, 8)
            angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(angle) * offset
            py = y + math.sin(angle) * offset
            
            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=random.randint(6, 12),
                lifetime=random.randint(200, 300),
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """Muerte gore"""
        if not hasattr(self, 'pool'): return
        
        # 1. Charco pequeño
        self.create_blood_pool(x, y)

        # 2. Niebla (Reducido de 25 a 8)
        for _ in range(8):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            self.pool.get(
                x, y, BLOOD_RED, 
                size=random.randint(2, 3), 
                lifetime=30, 
                velocity=velocity,
                gravity=0,
                friction=0.9
            )

        # 3. Trozos (Reducido de 8-14 a 3-5)
        num_chunks = random.randint(3, 5)
        for _ in range(num_chunks):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 6)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            self.pool.get(
                x, y, random.choice([DARK_BLOOD, GUTS_PINK]),
                size=random.randint(3, 5),
                lifetime=random.randint(40, 80),
                velocity=velocity,
                gravity=0,
                friction=0.85,
                is_chunk=True
            )
    
    # Delegados vacíos para mantener compatibilidad si se llaman por error
    def update(self, dt=1.0): pass
    def render(self, screen, camera): pass
    def clear(self):
        if hasattr(self, 'pool'): self.pool.clear()