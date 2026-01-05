"""
Sistema de partículas para efectos visuales
"""
import pygame
import random
import math

class Particle:
    def __init__(self, x, y, color, size=3, lifetime=30, velocity=None):
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.is_alive = True
        
        # Velocidad aleatoria si no se especifica
        if velocity is None:
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(1, 4)
            self.vel_x = math.cos(angle) * speed
            self.vel_y = math.sin(angle) * speed
        else:
            self.vel_x, self.vel_y = velocity
        
        # Gravedad y fricción
        self.gravity = 0.15
        self.friction = 0.95
    
    def update(self):
        """Actualiza la partícula"""
        if not self.is_alive:
            return
        
        # Aplicar física
        self.vel_y += self.gravity
        self.vel_x *= self.friction
        self.vel_y *= self.friction
        
        # Mover
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Reducir tiempo de vida
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.is_alive = False
    
    def render(self, screen):
        """Renderiza la partícula con fade out"""
        if not self.is_alive:
            return
        
        # Calcular alpha basado en tiempo de vida
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        
        # Calcular tamaño que se reduce con el tiempo
        current_size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        
        # Crear superficie con alpha
        surf = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, alpha)
        pygame.draw.circle(surf, color_with_alpha, (current_size, current_size), current_size)
        
        screen.blit(surf, (int(self.x - current_size), int(self.y - current_size)))


class ParticleSystem:
    """Gestor de partículas"""
    def __init__(self):
        self.particles = []
    
    def create_impact_particles(self, x, y, color, count=8):
        """Crea partículas de impacto"""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 5)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            particle = Particle(
                x, y, 
                color,
                size=random.randint(2, 4),
                lifetime=random.randint(20, 40),
                velocity=velocity
            )
            self.particles.append(particle)
    
    def create_death_particles(self, x, y, color, count=15):
        """Crea partículas de muerte de enemigo"""
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(3, 7)
            velocity = (math.cos(angle) * speed, math.sin(angle) * speed)
            
            particle = Particle(
                x, y,
                color,
                size=random.randint(3, 6),
                lifetime=random.randint(30, 60),
                velocity=velocity
            )
            self.particles.append(particle)
    
    def create_blood_splatter(self, x, y, count=5):
        """Crea salpicadura de sangre"""
        for _ in range(count):
            particle = Particle(
                x + random.randint(-5, 5),
                y + random.randint(-5, 5),
                (random.randint(150, 255), 0, 0),  # Rojo variado
                size=random.randint(2, 3),
                lifetime=random.randint(15, 30)
            )
            self.particles.append(particle)
    
    def update(self):
        """Actualiza todas las partículas"""
        for particle in self.particles[:]:
            particle.update()
            if not particle.is_alive:
                self.particles.remove(particle)
    
    def render(self, screen):
        """Renderiza todas las partículas"""
        for particle in self.particles:
            particle.render(screen)
    
    def clear(self):
        """Limpia todas las partículas"""
        self.particles.clear()