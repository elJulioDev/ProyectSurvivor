"""
Sistema de Object Pooling para reutilizar objetos costosos
"""
import pygame
from entities.projectile import Projectile
from entities.particle import Particle

class ProjectilePool:
    """Pool de proyectiles pre-instanciados"""
    def __init__(self, initial_size=500):
        self.pool = []
        self.active = []
        
        # Pre-crear proyectiles inactivos
        for _ in range(initial_size):
            p = Projectile(0, 0, 0)
            p.is_alive = False
            self.pool.append(p)
    
    def get(self, x, y, angle, speed=10, damage=25, penetration=1, lifetime=120, image_type='circle'):
        """Obtiene un proyectil del pool o crea uno nuevo si es necesario"""
        if self.pool:
            p = self.pool.pop()
        else:
            # Si el pool está vacío, crear uno nuevo (fallback)
            p = Projectile(0, 0, 0)
        
        # Resetear propiedades
        p.x = x
        p.y = y
        p.angle = angle
        p.speed = speed
        p.damage = damage
        p.penetration = penetration
        p.lifetime = lifetime
        p.image_type = image_type
        p.is_alive = True
        
        # Recalcular velocidades y rect
        import math
        p.vel_x = math.cos(angle) * speed
        p.vel_y = math.sin(angle) * speed
        p.rect.x = int(x - p.size // 2)
        p.rect.y = int(y - p.size // 2)
        p.hit_enemies.clear()
        
        self.active.append(p)
        return p
    
    def return_to_pool(self, projectile):
        """Devuelve un proyectil al pool"""
        if projectile in self.active:
            self.active.remove(projectile)
            projectile.is_alive = False
            projectile.hit_enemies.clear()
            self.pool.append(projectile)
    
    def update_all(self, dt):
        """Actualiza todos los proyectiles activos"""
        for p in self.active[:]:
            p.update(dt)
            if not p.is_alive:
                self.return_to_pool(p)
    
    def clear(self):
        """Limpia todos los proyectiles activos"""
        for p in self.active[:]:
            self.return_to_pool(p)


class ParticlePool:
    """Pool de partículas con superficies pre-renderizadas"""
    def __init__(self, initial_size=1000):
        self.pool = []
        self.active = []
        
        # CACHE DE SUPERFICIES PRE-RENDERIZADAS
        self.cached_surfaces = {}
        self._generate_surface_cache()
        
        # Pre-crear partículas inactivas
        for _ in range(initial_size):
            p = Particle(0, 0, (255, 0, 0), 3, 60, (0, 0))
            p.is_alive = False
            self.pool.append(p)
    
    def _generate_surface_cache(self):
        """Pre-genera superficies de partículas comunes"""
        colors = [
            (160, 0, 0),    # BLOOD_RED
            (80, 0, 0),     # DARK_BLOOD
            (180, 90, 100), # GUTS_PINK
            (200, 20, 20)   # BRIGHT_RED
        ]
        
        sizes = [2, 3, 4, 5, 6, 8, 10, 12, 16]
        alphas = [50, 100, 150, 200, 255]
        
        for color in colors:
            for size in sizes:
                for alpha in alphas:
                    # Círculos (líquido)
                    key = ('circle', color, size, alpha)
                    surf = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.circle(surf, (*color, alpha), (size, size), size)
                    self.cached_surfaces[key] = surf
                    
                    # Cuadrados (chunks)
                    key_chunk = ('chunk', color, size, alpha)
                    surf_chunk = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.rect(surf_chunk, (*color, alpha), (0, 0, size*2, size*2))
                    self.cached_surfaces[key_chunk] = surf_chunk
    
    def get_cached_surface(self, shape, color, size, alpha):
        """Obtiene superficie pre-renderizada o None si no existe"""
        # Encontrar color más cercano
        color_key = min([(160,0,0), (80,0,0), (180,90,100), (200,20,20)], 
                        key=lambda c: sum((a-b)**2 for a,b in zip(c, color)))
        
        # Encontrar tamaño más cercano
        size_key = min([2, 3, 4, 5, 6, 8, 10, 12, 16], key=lambda s: abs(s - size))
        
        # Encontrar alpha más cercano
        alpha_key = min([50, 100, 150, 200, 255], key=lambda a: abs(a - alpha))
        
        key = (shape, color_key, size_key, alpha_key)
        return self.cached_surfaces.get(key)
    
    def get(self, x, y, color, size, lifetime, velocity, gravity=0, friction=0.9, 
            is_chunk=False, is_liquid=True):
        """Obtiene partícula del pool"""
        if self.pool:
            p = self.pool.pop()
        else:
            p = Particle(0, 0, (255,0,0), 3, 60, (0,0))
        
        # Resetear propiedades
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
        
        import random
        p.angle = random.randint(0, 360)
        
        self.active.append(p)
        return p
    
    def return_to_pool(self, particle):
        """Devuelve partícula al pool"""
        if particle in self.active:
            self.active.remove(particle)
            particle.is_alive = False
            self.pool.append(particle)
    
    def update_all(self, dt):
        """Actualiza todas las partículas activas"""
        for p in self.active[:]:
            # DeltaTime aplicado internamente en Particle.update
            p.update(dt)
            if not p.is_alive:
                self.return_to_pool(p)
    
    def render_all(self, screen, camera):
        """Renderiza usando superficies cacheadas cuando sea posible"""
        for p in self.active:
            if not p.is_alive:
                continue
            
            # Calcular transparencia
            life_ratio = p.lifetime / p.max_lifetime
            alpha = int(255 * life_ratio)
            
            # Determinar si es charco estático
            speed_sq = p.vel_x * p.vel_x + p.vel_y * p.vel_y
            is_static_puddle = (speed_sq < 0.01 and p.is_liquid and not p.is_chunk)
            
            if is_static_puddle:
                current_size = p.size
            else:
                current_size = max(1, int(p.original_size * life_ratio))
            
            screen_pos = camera.apply_coords(p.x, p.y)
            
            # Intentar usar superficie cacheada
            shape = 'chunk' if p.is_chunk else 'circle'
            cached = self.get_cached_surface(shape, p.color, current_size, alpha)
            
            if cached:
                # Usar superficie pre-renderizada (MÁS RÁPIDO)
                if p.is_chunk:
                    rotated = pygame.transform.rotate(cached, p.angle)
                    screen.blit(rotated, 
                              (int(screen_pos[0] - rotated.get_width()//2), 
                               int(screen_pos[1] - rotated.get_height()//2)))
                else:
                    screen.blit(cached, 
                              (int(screen_pos[0] - current_size), 
                               int(screen_pos[1] - current_size)))
            else:
                # Fallback: renderizado dinámico (más lento)
                surf = pygame.Surface((current_size * 2, current_size * 2), pygame.SRCALPHA)
                color_with_alpha = (*p.color, alpha)
                
                if p.is_chunk:
                    pygame.draw.rect(surf, color_with_alpha, (0, 0, current_size*2, current_size*2))
                    surf = pygame.transform.rotate(surf, p.angle)
                else:
                    pygame.draw.circle(surf, color_with_alpha, (current_size, current_size), current_size)
                
                screen.blit(surf, (int(screen_pos[0] - current_size), int(screen_pos[1] - current_size)))
    
    def clear(self):
        """Limpia todas las partículas activas"""
        for p in self.active[:]:
            self.return_to_pool(p)