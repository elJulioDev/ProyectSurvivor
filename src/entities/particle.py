"""
Sistema de partículas optimizado con DeltaTime
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
        self.angle = random.randint(0, 360)

    def update(self, dt=1.0):
        """Actualización con DeltaTime"""
        if not self.is_alive:
            return
        
        # Aplicar física escalada por dt
        self.vel_y += self.gravity * dt
        self.vel_x *= self.friction ** dt
        self.vel_y *= self.friction ** dt
        
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        # Lógica de líquidos/charcos
        speed_sq = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        
        if self.is_liquid and speed_sq < 0.01 and not self.is_chunk:
            # Charco estático
            self.gravity = 0
            self.vel_x = 0
            self.vel_y = 0
            self.lifetime -= 0.3 * dt  # Desgaste lento
        else:
            self.lifetime -= 1 * dt
            
        if self.lifetime <= 0:
            self.is_alive = False


class ParticleSystem:
    """Sistema de partículas que usa Object Pooling"""
    def __init__(self):
        # El pool real se gestiona externamente ahora
        self.particles = []
    
    def set_pool(self, particle_pool):
        """Establece el pool de partículas (llamar desde GameplayScene)"""
        self.pool = particle_pool
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.0, count=10):
        """Sangrado direccional al recibir daño"""
        if not hasattr(self, 'pool'):
            return
        
        for _ in range(count):
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                spread = random.uniform(-0.6, 0.6) 
                angle = base_angle + spread
                speed = random.uniform(3, 9) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            color = random.choice([BLOOD_RED, BRIGHT_RED, DARK_BLOOD])
            
            self.pool.get(
                x, y, color,
                size=random.randint(2, 5),
                lifetime=random.randint(30, 60),
                velocity=velocity,
                gravity=0,
                friction=0.85,
                is_liquid=True
            )

    def create_blood_drip(self, x, y):
        """Goteo mientras camina"""
        if not hasattr(self, 'pool'):
            return
        
        self.pool.get(
            x + random.randint(-3, 3), 
            y + random.randint(-3, 3),
            DARK_BLOOD,
            size=random.randint(3, 5),
            lifetime=random.randint(200, 400),
            velocity=(0, 0),
            gravity=0,
            friction=0,
            is_liquid=True
        )
    
    def create_blood_pool(self, x, y):
        """Crea un charco grande y estático"""
        if not hasattr(self, 'pool'):
            return
        
        blobs = random.randint(3, 7)
        for _ in range(blobs):
            offset_dist = random.uniform(0, 10)
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist
            
            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=random.randint(8, 16),
                lifetime=random.randint(300, 500),
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """Muerte gore: Charco + Explosión"""
        if not hasattr(self, 'pool'):
            return
        
        # 1. Charco
        self.create_blood_pool(x, y)

        # 2. Niebla roja
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 5)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            self.pool.get(
                x, y, BLOOD_RED, 
                size=random.randint(2, 4), 
                lifetime=40, 
                velocity=velocity,
                gravity=0,
                friction=0.9
            )

        # 3. Trozos de carne
        num_chunks = random.randint(8, 14)
        for _ in range(num_chunks):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 8)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            color = random.choice([DARK_BLOOD, GUTS_PINK])
            
            self.pool.get(
                x, y, color,
                size=random.randint(4, 7),
                lifetime=random.randint(60, 120),
                velocity=velocity,
                gravity=0,
                friction=0.88,
                is_chunk=True
            )
    
    def update(self, dt=1.0):
        """El pool maneja las actualizaciones ahora"""
        pass
    
    def render(self, screen, camera):
        """El pool maneja el renderizado ahora"""
        pass
    
    def clear(self):
        """Limpia partículas (delegado al pool)"""
        if hasattr(self, 'pool'):
            self.pool.clear()