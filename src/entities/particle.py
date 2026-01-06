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
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.2, count=4):
        """
        Sangrado direccional (Impactos de bala).
        Si hay vector de dirección, la sangre sigue la inercia del disparo.
        """
        if self.quality == 2:
            actual_count = count * 3  # ¡Mucho más sangre en calidad alta!
        elif self.quality == 1:
            actual_count = count
        else:
            actual_count = 2

        for _ in range(actual_count):
            # Cálculo de ángulo: Si hay dirección (bala), usamos un cono de dispersión
            if direction_vector:
                base_angle = math.atan2(direction_vector[1], direction_vector[0])
                # Dispersión de 45 grados aprox (0.8 radianes)
                spread = random.uniform(-0.5, 0.5)
                angle = base_angle + spread
                # La sangre sale rápido
                speed = random.uniform(4, 12) * force
            else:
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(2, 6)

            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            # Variedad de color: Sangre fresca, oscura o brillante
            color = random.choice([BLOOD_RED, BRIGHT_RED, DARK_BLOOD])
            
            # Tamaño variado
            size = random.randint(2, 5)
            
            self.pool.get(
                x, y, color,
                size=size,
                lifetime=random.randint(40, 80),
                velocity=velocity,
                gravity=0,
                friction=0.85, # Se frena al tocar el suelo
                is_liquid=True
            )

    def create_blood_drip(self, x, y, intensity=1.0):
        """
        Goteo dinámico:
        - Intensity bajo (<5): Gotas pequeñas.
        - Intensity medio (5-15): Charcos medianos.
        - Intensity alto (>15): Rastro grueso y oscuro.
        """
        # Verificamos calidad (en Low no generamos rastros para ahorrar CPU)
        if self.quality == 0: 
            return

        # Calculamos tamaño base según intensidad
        # Mínimo 2px, Máximo 10px
        base_size = min(10, 2 + int(intensity * 0.3))
        
        # Si la intensidad es MUY alta (ej. escopetazo reciente), soltamos más de una gota
        # para hacer el rastro más denso.
        drops_count = 1
        if intensity > 15:
            drops_count = random.randint(1, 2)
        
        for _ in range(drops_count):
            # Pequeña dispersión aleatoria cerca de los pies del enemigo
            spawn_x = x + random.uniform(-4, 4)
            spawn_y = y + random.uniform(-4, 4)
            
            # Color: Cuanto más intenso, más oscura la sangre (arterial/profunda)
            if intensity > 10:
                color = DARK_BLOOD
            else:
                color = random.choice([BLOOD_RED, DARK_BLOOD])

            # Variación de tamaño para que no se vea artificial
            size = random.randint(base_size, base_size + 3)
            
            self.pool.get(
                spawn_x, spawn_y,
                color,
                size=size,
                # Vida larga para que el sistema de "Baking" (Paso anterior)
                # tenga tiempo de detectarlo quieto y pegarlo al suelo.
                lifetime=random.randint(100, 200), 
                velocity=(0, 0), # Cae directo al suelo (quieto)
                gravity=0,
                friction=0,
                is_liquid=True
            )
    
    def create_blood_pool(self, x, y):
        """
        Charco grande irregular.
        En High Quality crea múltiples 'blobs' para dar forma orgánica.
        """
        blobs = 1
        if self.quality == 2:
            blobs = random.randint(3, 6) # Charcos más complejos
        elif self.quality == 1:
            blobs = 2
            
        for _ in range(blobs):
            # Desplazamiento aleatorio para que no sea un círculo perfecto
            offset_dist = random.uniform(0, 15) if blobs > 1 else 0
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist
            
            # Tamaño aleatorio grande
            size = random.randint(10, 22)
            
            self.pool.get(
                px, py,
                DARK_BLOOD, # Sangre coagulada en el piso
                size=size,
                lifetime=random.randint(900, 1500), # Duran mucho (15-25 seg)
                velocity=(0, 0),
                gravity=0,
                friction=0,
                is_liquid=True
            )

    def create_viscera_explosion(self, x, y):
        """Muerte gore: Niebla roja + Trozos de carne + Charco"""
        
        # Ajuste de cantidad según calidad
        if self.quality == 2: # ULTRA GORE
            mist_count = 25
            chunk_count = 10
            pool_spawn = True
        elif self.quality == 1: # NORMAL
            mist_count = 10
            chunk_count = 4
            pool_spawn = True
        else: # LOW
            mist_count = 5
            chunk_count = 0
            pool_spawn = False

        # 1. Charco base grande
        if pool_spawn:
            self.create_blood_pool(x, y)

        # 2. Niebla de sangre (rápida y efímera, sale en todas direcciones)
        for _ in range(mist_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 10)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            color = random.choice([BLOOD_RED, BRIGHT_RED])
            
            self.pool.get(
                x, y, color, 
                size=random.randint(3, 6), 
                lifetime=random.randint(20, 45), # Desaparece rápido
                velocity=velocity,
                gravity=0,
                friction=0.9
            )

        # 3. Trozos de carne (Chunks) - Se deslizan lejos
        for _ in range(chunk_count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(5, 12) # Salen disparados
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            # Color carne o sangre oscura
            color = random.choice([DARK_BLOOD, GUTS_PINK])
            
            p = self.pool.get(
                x, y, color,
                size=random.randint(4, 9),
                lifetime=random.randint(100, 300), # Se quedan un rato
                velocity=velocity,
                gravity=0,
                friction=0.92, # Patinan más antes de frenar
                is_chunk=True
            )
    
    def update(self, dt=1.0): pass
    def render(self, screen, camera): pass
    def clear(self):
        if hasattr(self, 'pool'): 
            self.pool.clear()