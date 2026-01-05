"""
Sistema de partículas avanzado para efectos visuales (Gore Top-Down)
"""
import pygame
import random
import math

# --- PALETA DE COLORES GORE ---
BLOOD_RED = (160, 0, 0)      # Rojo sangre estándar
DARK_BLOOD = (80, 0, 0)      # Sangre coagulada/oscura (para charcos)
GUTS_PINK = (180, 90, 100)   # Rosado carne/intestinos
BRIGHT_RED = (200, 20, 20)   # Sangre arterial fresca

class Particle:
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
        self.gravity = gravity  # En top-down, esto suele ser 0
        self.friction = friction
        self.is_chunk = is_chunk
        self.is_liquid = is_liquid 
        self.angle = random.randint(0, 360) 

    def update(self):
        if not self.is_alive: return
        
        # Aplicar física
        self.vel_y += self.gravity
        self.vel_x *= self.friction
        self.vel_y *= self.friction
        
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Lógica de líquidos/charcos:
        # Si es líquido y se detiene, se convierte en mancha (no desaparece rápido)
        speed = math.hypot(self.vel_x, self.vel_y)
        if self.is_liquid and speed < 0.1 and not self.is_chunk:
            self.gravity = 0
            self.vel_x = 0
            self.vel_y = 0
            # Desgaste muy lento para que el charco dure
            self.lifetime -= 0.3 
        else:
            self.lifetime -= 1
            
        if self.lifetime <= 0:
            self.is_alive = False
    
    def render(self, screen, camera):
        if not self.is_alive: return
        
        # Calcular transparencia
        life_ratio = self.lifetime / self.max_lifetime
        alpha = int(255 * life_ratio)
        
        # Los charcos (líquido estático) MANTIENEN su tamaño, no se encogen hasta el final
        is_static_puddle = (self.vel_x == 0 and self.vel_y == 0 and self.is_liquid and not self.is_chunk)
        
        if is_static_puddle:
            # Si es charco, mantiene tamaño hasta que alpha es muy bajo
            current_size = self.size
        else:
            # Si vuela, se encoge
            current_size = max(1, int(self.original_size * life_ratio))
        
        screen_pos = camera.apply_coords(self.x, self.y)
        
        surf = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)
        
        if self.is_chunk:
            pygame.draw.rect(surf, color_with_alpha, (0, 0, current_size*2, current_size*2))
            surf = pygame.transform.rotate(surf, self.angle)
        else:
            # Dibujar círculos irregulares para charcos (simulación simple)
            pygame.draw.circle(surf, color_with_alpha, (current_size, current_size), current_size)
            
        screen.blit(surf, (int(screen_pos[0] - current_size), int(screen_pos[1] - current_size)))


class ParticleSystem:
    def __init__(self):
        self.particles = []
    
    def create_blood_splatter(self, x, y, direction_vector=None, force=1.0, count=10):
        """Sangrado direccional al recibir daño"""
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
            
            particle = Particle(
                x, y, color,
                size=random.randint(2, 5),
                lifetime=random.randint(30, 60),
                velocity=velocity,
                gravity=0, # Sin gravedad vertical para top-down
                friction=0.85,
                is_liquid=True
            )
            self.particles.append(particle)

    def create_blood_drip(self, x, y):
        """Goteo mientras camina"""
        particle = Particle(
            x + random.randint(-3, 3), 
            y + random.randint(-3, 3),
            DARK_BLOOD,
            size=random.randint(3, 5),
            lifetime=random.randint(200, 400), # Dura bastante en el suelo
            velocity=(0, 0),
            gravity=0,
            friction=0,
            is_liquid=True
        )
        self.particles.append(particle)
    
    def create_blood_pool(self, x, y):
        """Crea un charco grande y estático"""
        # Varias manchas superpuestas crean una forma irregular
        blobs = random.randint(3, 7)
        for _ in range(blobs):
            offset_dist = random.uniform(0, 10)
            offset_angle = random.uniform(0, math.pi * 2)
            px = x + math.cos(offset_angle) * offset_dist
            py = y + math.sin(offset_angle) * offset_dist
            
            particle = Particle(
                px, py,
                DARK_BLOOD,
                size=random.randint(8, 16), # Manchas grandes
                lifetime=random.randint(600, 900), # Duran 10-15 segundos
                velocity=(0,0), # Estáticas
                gravity=0,
                friction=0,
                is_liquid=True
            )
            self.particles.append(particle)

    def create_viscera_explosion(self, x, y):
        """Muerte gore: Charco + Explosión"""
        
        # 1. CREAR CHARCO (La base de sangre)
        self.create_blood_pool(x, y)

        # 2. Niebla roja (expansión rápida)
        for _ in range(25):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 5)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            p = Particle(
                x, y, BLOOD_RED, 
                size=random.randint(2, 4), 
                lifetime=40, 
                velocity=velocity,
                gravity=0, # Top-down
                friction=0.9
            )
            self.particles.append(p)

        # 3. Trozos de carne (Se deslizan por el suelo)
        num_chunks = random.randint(8, 14)
        for _ in range(num_chunks):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 8) # Salen rápido
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            color = random.choice([DARK_BLOOD, GUTS_PINK])
            
            particle = Particle(
                x, y, color,
                size=random.randint(4, 7),
                lifetime=random.randint(60, 120),
                velocity=velocity,
                gravity=0,      # No caen hacia el sur
                friction=0.88,  # Fricción simula deslizarse por el suelo
                is_chunk=True
            )
            self.particles.append(particle)
    
    def update(self):
        for particle in self.particles[:]:
            particle.update()
            if not particle.is_alive:
                self.particles.remove(particle)
    
    def render(self, screen, camera):
        # Optimización: Renderizar solo partículas en pantalla si son muchas
        for particle in self.particles:
            # Opcional: if camera.is_on_screen(...):
            particle.render(screen, camera)
    
    def clear(self):
        self.particles.clear()