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
        
        # Lógica de líquidos (Charcos)
        speed = math.sqrt(self.vel_x**2 + self.vel_y**2)
        if self.is_liquid and speed < 0.1 and not self.is_chunk:
            self.vel_x = 0
            self.vel_y = 0
            # Los charcos se secan muy lento
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
    
    def _can_spawn(self, count):
        if not hasattr(self, 'pool'): return False
        # Estimación rápida para no recorrer toda la lista cada vez
        # Asumimos que si pedimos spawn y el índice está dando la vuelta rápido, estamos llenos
        # (Para una implementación estricta, contaríamos activas, pero es lento en Python)
        return True 
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.0, count=4):
        """Sangrado direccional (Impactos de bala)"""
        if self.quality == 2:
            actual_count = count * 2 # Más partículas en High
        elif self.quality == 1:
            actual_count = count
        else:
            actual_count = 1

        for _ in range(actual_count):
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                spread = random.uniform(-0.6, 0.6)
                angle = base_angle + spread
                speed = random.uniform(3, 9) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            # Variedad de color
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
        """Goteo mientras camina (Solo High Quality)"""
        if self.quality < 2: return
        
        self.pool.get(
            x + random.randint(-3, 3), 
            y + random.randint(-3, 3),
            DARK_BLOOD,
            size=random.randint(3, 5),
            lifetime=random.randint(200, 300), # Dura mucho
            velocity=(0, 0),
            gravity=0,
            friction=0,
            is_liquid=True
        )
    
    def create_blood_pool(self, x, y):
        """
        Charco grande irregular.
        En High Quality crea múltiples 'blobs' para dar forma orgánica.
        En Low Quality crea solo uno.
        """
        blobs = 1
        if self.quality == 2:
            blobs = random.randint(3, 5)
        elif self.quality == 1:
            blobs = 2
            
        for _ in range(blobs):
            offset_dist = random.uniform(0, 8) if blobs > 1 else 0
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist
            
            self.pool.get(
                px, py,
                DARK_BLOOD,
                size=random.randint(8, 14),
                lifetime=random.randint(600, 900), # 10-15 segundos
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """Muerte gore: Niebla roja + Trozos de carne"""
        
        if self.quality == 2: # ULTRA GORE
            mist_count = 20
            chunk_count = 8
            pool_spawn = True
        elif self.quality == 1: # NORMAL
            mist_count = 10
            chunk_count = 3
            pool_spawn = True
        else: # LOW
            mist_count = 5
            chunk_count = 0
            pool_spawn = False

        # 1. Charco base
        if pool_spawn:
            self.create_blood_pool(x, y)

        # 2. Niebla de sangre (rápida y efímera)
        for _ in range(mist_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 7)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            color = random.choice([BLOOD_RED, BRIGHT_RED])
            
            self.pool.get(
                x, y, color, 
                size=random.randint(2, 4), 
                lifetime=random.randint(20, 40),
                velocity=velocity,
                gravity=0,
                friction=0.9
            )

        # 3. Trozos de carne (Chunks) - Se deslizan
        for _ in range(chunk_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(4, 9)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            color = random.choice([DARK_BLOOD, GUTS_PINK])
            
            p = self.pool.get(
                x, y, color,
                size=random.randint(4, 7),
                lifetime=random.randint(60, 120),
                velocity=velocity,
                gravity=0,
                friction=0.88, # Se deslizan un poco más
                is_chunk=True
            )
    
    def update(self, dt=1.0): pass
    def render(self, screen, camera): pass
    def clear(self):
        if hasattr(self, 'pool'): 
            self.pool.clear()