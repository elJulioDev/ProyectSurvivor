"""
Sistema de Object Pooling optimizado con Ring Buffer
"""
import pygame
import math
from entities.projectile import Projectile
from entities.particle import Particle
from settings import WINDOW_HEIGHT, WINDOW_WIDTH

class ProjectilePool:
    """Pool de proyectiles (Mantiene lógica original funcional)"""
    def __init__(self, initial_size=500):
        self.pool = []
        self.active = []
        for _ in range(initial_size):
            p = Projectile(0, 0, 0)
            p.is_alive = False
            self.pool.append(p)
    
    def get(self, x, y, angle, speed=10, damage=25, penetration=1, lifetime=120, image_type='circle'):
        if self.pool:
            p = self.pool.pop()
        else:
            p = Projectile(0, 0, 0)
        
        p.x = x
        p.y = y
        p.angle = angle
        p.speed = speed
        p.damage = damage
        p.penetration = penetration
        p.lifetime = lifetime
        p.image_type = image_type
        p.is_alive = True
        
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
    Pool de partículas optimizado con RING BUFFER (Memoria Circular).
    Evita allocs/deallocs y pone un límite duro a la cantidad de partículas.
    """
    def __init__(self, capacity=1500): # Límite fijo de 1500 partículas
        self.capacity = capacity
        # Pre-creamos TODAS las partículas. No usaremos append/pop nunca más.
        self.pool = [Particle(0, 0, (0,0,0), 0, 0, (0,0)) for _ in range(capacity)]
        for p in self.pool: p.is_alive = False
        
        # Puntero circular
        self.next_index = 0
        
        # CACHE DE SUPERFICIES (Igual que antes)
        self.cached_surfaces = {}
        self._generate_surface_cache()
    
    def _generate_surface_cache(self):
        colors = [
            (160, 0, 0), (80, 0, 0), (180, 90, 100), (200, 20, 20)
        ]
        sizes = [2, 3, 4, 5, 6, 8, 10, 12, 16]
        alphas = [50, 100, 150, 200, 255]
        
        for color in colors:
            for size in sizes:
                for alpha in alphas:
                    key = ('circle', color, size, alpha)
                    surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                    self.cached_surfaces[key] = surf
                    
                    key_chunk = ('chunk', color, size, alpha)
                    surf_chunk = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.rect(surf_chunk, (*color, alpha), (0, 0, size*2, size*2))
                    self.cached_surfaces[key_chunk] = surf_chunk
    
    def get_cached_surface(self, shape, color, size, alpha):
        color_key = min([(160,0,0), (80,0,0), (180,90,100), (200,20,20)], 
                        key=lambda c: sum((a-b)**2 for a,b in zip(c, color)))
        size_key = min([2, 3, 4, 5, 6, 8, 10, 12, 16], key=lambda s: abs(s - size))
        alpha_key = min([50, 100, 150, 200, 255], key=lambda a: abs(a - alpha))
        return self.cached_surfaces.get((shape, color_key, size_key, alpha_key))
    
    def get(self, x, y, color, size, lifetime, velocity, gravity=0, friction=0.9, 
            is_chunk=False, is_liquid=True):
        """Obtiene la siguiente partícula del buffer circular, sobrescribiendo si es necesario"""
        
        # Tomamos la partícula en el índice actual
        p = self.pool[self.next_index]
        
        # Avanzamos el índice (si llegamos al final, volvemos al principio)
        self.next_index = (self.next_index + 1) % self.capacity
        
        # Reinicializamos la partícula (reciclaje forzoso)
        p.x = x
        p.y = y
        p.color = color
        p.size = size
        p.original_size = size
        p.lifetime = lifetime
        p.max_lifetime = lifetime
        p.is_alive = True
        p.vel_x, p.vel_y = velocity
        p.gravity = gravity
        p.friction = friction
        p.is_chunk = is_chunk
        p.is_liquid = is_liquid
        
        return p

    def update_all(self, dt):
        """Actualiza solo las vivas. Iterar una lista fija es muy rápido en Python."""
        for p in self.pool:
            if p.is_alive:
                p.update(dt)
    
    def render_all(self, screen, camera):
        """Renderizado optimizado con Batch Blitting y Culling"""
        blit_sequence = []
        cam_x = camera.offset_x
        cam_y = camera.offset_y
        margin = 50 
        
        for p in self.pool:
            if not p.is_alive:
                continue
            
            # 1. Culling
            screen_x = p.x + cam_x
            screen_y = p.y + cam_y
            
            if not (-margin < screen_x < WINDOW_WIDTH + margin and 
                    -margin < screen_y < WINDOW_HEIGHT + margin):
                continue

            # 2. Visual
            life_ratio = p.lifetime / p.max_lifetime
            if life_ratio <= 0: continue
            
            alpha = int(255 * life_ratio)
            if alpha < 5: continue

            if p.is_liquid and not p.is_chunk and abs(p.vel_x) < 0.1 and abs(p.vel_y) < 0.1:
                current_size = p.size
            else:
                current_size = max(1, int(p.original_size * life_ratio))
            
            shape = 'chunk' if p.is_chunk else 'circle'
            surf = self.get_cached_surface(shape, p.color, current_size, alpha)
            
            if surf:
                dest_x = int(screen_x - surf.get_width() // 2)
                dest_y = int(screen_y - surf.get_height() // 2)
                blit_sequence.append((surf, (dest_x, dest_y)))
            else:
                pygame.draw.circle(screen, (*p.color, alpha), (int(screen_x), int(screen_y)), current_size)

        if blit_sequence:
            screen.blits(blit_sequence)

    def clear(self):
        for p in self.pool:
            p.is_alive = False