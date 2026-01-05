"""
Sistema de Object Pooling para reutilizar objetos costosos
"""
import pygame
from entities.projectile import Projectile
from entities.particle import Particle
from settings import WINDOW_HEIGHT, WINDOW_WIDTH

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
    def __init__(self, initial_size=2000):
        self.pool = []
        self.active = []
        
        # CACHE DE SUPERFICIES
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
                    
                    # Cuadrados (chunks) - NO rotados (rotar en tiempo real es caro)
                    # Si quieres rotación barata, pre-renderiza 4 ángulos fijos aquí.
                    key_chunk = ('chunk', color, size, alpha)
                    surf_chunk = pygame.Surface((size*2, size*2), pygame.SRCALPHA)
                    pygame.draw.rect(surf_chunk, (*color, alpha), (0, 0, size*2, size*2))
                    self.cached_surfaces[key_chunk] = surf_chunk
    
    def get_cached_surface(self, shape, color, size, alpha):
        """Obtiene superficie pre-renderizada o None si no existe"""
        # Encontrar color más cercano
        color_key = min([(160,0,0), (80,0,0), (180,90,100), (200,20,20)], 
                        key=lambda c: sum((a-b)**2 for a,b in zip(c, color)))
        size_key = min([2, 3, 4, 5, 6, 8, 10, 12, 16], key=lambda s: abs(s - size))
        alpha_key = min([50, 100, 150, 200, 255], key=lambda a: abs(a - alpha))
        key = (shape, color_key, size_key, alpha_key)
        return self.cached_surfaces.get(key)
    
    def get(self, x, y, color, size, lifetime, velocity, gravity=0, friction=0.9, 
            is_chunk=False, is_liquid=True):
        if self.pool:
            p = self.pool.pop()
        else:
            # Si el pool se vacía, no creamos más para proteger FPS
            # O devolvemos None, o reciclamos la más antigua.
            # Por ahora, creamos una nueva pero con cuidado.
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
        p.angle = 0 # Eliminamos rotación aleatoria inicial para simplificar caché
        
        self.active.append(p)
        return p
    
    def return_to_pool(self, particle):
        if particle in self.active:
            self.active.remove(particle)
            particle.is_alive = False
            self.pool.append(particle)
    
    def update_all(self, dt):
        # Iterar sobre una copia o indice inverso para poder borrar seguro
        for i in range(len(self.active) - 1, -1, -1):
            p = self.active[i]
            p.update(dt)
            if not p.is_alive:
                self.return_to_pool(p)
    
    def render_all(self, screen, camera):
        """
        OPTIMIZACIÓN CRÍTICA:
        1. Culling: No dibujar si está fuera de pantalla.
        2. Batch Blits: Usar screen.blits() en lugar de blit() individual.
        3. Evitar rotaciones en tiempo real.
        """
        blit_sequence = []
        
        # Pre-cálculo de límites de cámara para Culling rápido
        cam_x = camera.offset_x
        cam_y = camera.offset_y
        
        # Margen para no cortar partículas en el borde
        margin = 50 
        
        for p in self.active:
            # 1. CAMERA CULLING (Lo más importante)
            # Calculamos posición en pantalla
            screen_x = p.x + cam_x
            screen_y = p.y + cam_y
            
            # Si está fuera de la pantalla, saltar (continue)
            if not (-margin < screen_x < WINDOW_WIDTH + margin and 
                    -margin < screen_y < WINDOW_HEIGHT + margin):
                continue

            # 2. Lógica visual
            life_ratio = p.lifetime / p.max_lifetime
            alpha = int(255 * life_ratio)
            
            # Optimización: si es casi transparente, no dibujar
            if alpha < 5: 
                continue

            # Determinar tamaño
            # Pequeña optimización: evitar sqrt en el bucle de render si es posible
            if p.is_liquid and not p.is_chunk and abs(p.vel_x) < 0.1 and abs(p.vel_y) < 0.1:
                current_size = p.size
            else:
                current_size = max(1, int(p.original_size * life_ratio))
            
            # 3. Obtener Superficie Cacheada
            shape = 'chunk' if p.is_chunk else 'circle'
            surf = self.get_cached_surface(shape, p.color, current_size, alpha)
            
            if surf:
                # OPTIMIZACIÓN: Eliminé la rotación en tiempo real para los chunks.
                # Rotar 2000 sprites por frame mata la CPU. 
                # Si necesitas rotación, pre-renderiza 4 ángulos en el init.
                
                # Centrar
                dest_x = int(screen_x - surf.get_width() // 2)
                dest_y = int(screen_y - surf.get_height() // 2)
                
                # Añadir a la lista de dibujo masivo
                blit_sequence.append((surf, (dest_x, dest_y)))
            else:
                # Fallback simple (dibujo directo, lento pero seguro)
                pygame.draw.circle(screen, (*p.color, alpha), (int(screen_x), int(screen_y)), current_size)

        # 4. BATCH DRAW (La magia de Pygame 2)
        # Dibuja miles de partículas en una sola llamada a C
        if blit_sequence:
            screen.blits(blit_sequence)

    def clear(self):
        for p in self.active[:]:
            self.return_to_pool(p)