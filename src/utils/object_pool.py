import pygame
import math
from entities.projectile import Projectile
from entities.particle import Particle
from settings import WINDOW_HEIGHT, WINDOW_WIDTH

# Colores para el cache
BLOOD_RED = (160, 0, 0)
DARK_BLOOD = (80, 0, 0)
GUTS_PINK = (180, 90, 100)
BRIGHT_RED = (200, 20, 20)

class ProjectilePool:
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
    Pool de partículas ULTRA OPTIMIZADO
    Adaptado para soportar la nueva paleta de colores Gore
    """
    def __init__(self, capacity=800):
        self.capacity = capacity
        self.pool = [Particle(0, 0, (0,0,0), 0, 0, (0,0)) for _ in range(capacity)]
        for p in self.pool: 
            p.is_alive = False
        
        self.next_index = 0
        self.cached_surfaces = {}
        self._generate_surface_cache()
    
    def _generate_surface_cache(self):
        """Generamos caché para los 4 colores gore"""
        colors = [BLOOD_RED, DARK_BLOOD, GUTS_PINK, BRIGHT_RED]
        sizes = [2, 3, 4, 6, 8, 12, 16] # Añadido 16 para charcos grandes
        alphas = [100, 180, 255]
        
        for color in colors:
            for size in sizes:
                for alpha in alphas:
                    # Circular (gotas)
                    key = ('circle', color, size, alpha)
                    surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                    self.cached_surfaces[key] = surf
                    
                    # Chunk (trozos de carne)
                    key_chunk = ('chunk', color, size, alpha)
                    surf_chunk = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.rect(surf_chunk, (*color, alpha), (0, 0, size*2, size*2))
                    self.cached_surfaces[key_chunk] = surf_chunk
    
    def get_cached_surface(self, shape, color, size, alpha):
        """Busca la superficie pre-renderizada más cercana"""
        # Mapeo aproximado de color para usar el caché
        color_key = DARK_BLOOD # Default
        if color == GUTS_PINK: color_key = GUTS_PINK
        elif color == BRIGHT_RED: color_key = BRIGHT_RED
        elif color[0] > 140: color_key = BLOOD_RED
        
        size_key = min([2, 3, 4, 6, 8, 12, 16], key=lambda s: abs(s - size))
        alpha_key = min([100, 180, 255], key=lambda a: abs(a - alpha))
        
        return self.cached_surfaces.get((shape, color_key, size_key, alpha_key))
    
    def get(self, x, y, color, size, lifetime, velocity, gravity=0, friction=0.9, 
            is_chunk=False, is_liquid=True):
        p = self.pool[self.next_index]
        self.next_index = (self.next_index + 1) % self.capacity
        
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
        p.angle = 0 # Reset angle
        
        return p

    def update_all(self, dt):
        for p in self.pool:
            if p.is_alive:
                p.update(dt)
    
    def render_all(self, screen, camera):
        rendered_count = 0 # Contador de lo que realmente se dibuja
        blit_sequence = []
        cam_x = camera.offset_x
        cam_y = camera.offset_y
        
        # Margen para que no desaparezcan de golpe al salir
        margin = 50
        min_x = -margin
        max_x = WINDOW_WIDTH + margin
        min_y = -margin
        max_y = WINDOW_HEIGHT + margin
        
        for p in self.pool:
            if not p.is_alive:
                continue
            
            screen_x = p.x + cam_x
            screen_y = p.y + cam_y
            
            # --- CULLING (Optimización) ---
            # Si está fuera de los límites de la pantalla, saltamos al siguiente
            if not (min_x < screen_x < max_x and min_y < screen_y < max_y):
                continue

            # Si pasa el filtro, contamos y preparamos para dibujar
            rendered_count += 1

            life_ratio = p.lifetime / p.max_lifetime
            if life_ratio <= 0: continue
            
            alpha = int(255 * life_ratio)
            if alpha < 10: continue

            # Lógica visual mejorada: Los líquidos estáticos no se encogen
            is_static_liquid = (p.is_liquid and not p.is_chunk and abs(p.vel_x) < 0.1 and abs(p.vel_y) < 0.1)
            
            if is_static_liquid:
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
                pygame.draw.circle(screen, p.color, (int(screen_x), int(screen_y)), current_size)

        if blit_sequence:
            screen.blits(blit_sequence)
            
        return rendered_count # Retornamos la cantidad real dibujada

    def clear(self):
        for p in self.pool:
            p.is_alive = False