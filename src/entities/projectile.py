"""
Proyectiles optimizados con DeltaTime y colisiones por grid
"""
import pygame
import math
from settings import YELLOW, WORLD_WIDTH, WORLD_HEIGHT

class Projectile:
    __slots__ = (
        'x', 'y', 'angle', 'speed', 'size', 'color', 'damage', 
        'penetration', 'lifetime', 'is_alive', 'image_type', 
        'hit_enemies', 'vel_x', 'vel_y', 'rect'
    )
    def __init__(self, x, y, angle, speed=10, damage=25, penetration=1, lifetime=120, image_type='circle'):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = 6
        self.color = YELLOW
        self.damage = damage
        self.penetration = penetration
        self.lifetime = lifetime
        self.is_alive = True
        self.image_type = image_type
        
        self.hit_enemies = []
        
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed
        
        self.rect = pygame.Rect(
            self.x - self.size // 2, self.y - self.size // 2,
            self.size, self.size
        )
    
    def update(self, dt=1.0):
        """Actualización con DeltaTime"""
        if not self.is_alive:
            return
        
        # Movimiento escalado por dt
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        self.rect.x = int(self.x - self.size // 2)
        self.rect.y = int(self.y - self.size // 2)
        
        self.lifetime -= 1 * dt
        if self.lifetime <= 0:
            self.is_alive = False
            
        # Límites del mundo
        if (self.x < -50 or self.x > WORLD_WIDTH + 50 or
            self.y < -50 or self.y > WORLD_HEIGHT + 50):
            self.is_alive = False
    
    def check_collision_grid(self, spatial_grid):
        """
        Colisión optimizada usando grid espacial.
        En lugar de verificar TODOS los enemigos (O(N)),
        solo verifica los que están cerca (O(1) promedio).
        """
        if not self.is_alive:
            return None
        
        # Obtener solo los enemigos cercanos
        nearby_enemies = spatial_grid.get_nearby(self.x, self.y, radius=0)
        
        for enemy in nearby_enemies:
            if enemy.is_alive and enemy not in self.hit_enemies:
                if self.rect.colliderect(enemy.rect):
                    self.hit_enemies.append(enemy)
                    self.penetration -= 1
                    
                    if self.penetration <= 0:
                        self.is_alive = False
                    
                    return enemy
        return None
    
    def check_collision(self, enemies):
        """Método legacy para compatibilidad (NO USAR, usar check_collision_grid)"""
        if not self.is_alive:
            return None
        
        for enemy in enemies:
            if enemy.is_alive and enemy not in self.hit_enemies:
                if self.rect.colliderect(enemy.rect):
                    self.hit_enemies.append(enemy)
                    self.penetration -= 1
                    
                    if self.penetration <= 0:
                        self.is_alive = False
                    
                    return enemy
        return None
    
    def render(self, screen, camera):
        if not self.is_alive:
            return
            
        screen_pos = camera.apply_coords(self.x, self.y)
        pos = (int(screen_pos[0]), int(screen_pos[1]))
        
        if self.image_type == 'circle':
            pygame.draw.circle(screen, self.color, pos, self.size)
            pygame.draw.circle(screen, (255, 255, 200), pos, max(1, self.size // 2))
            
        elif self.image_type == 'square':
            rect_surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, self.color, (0, 0, self.size*2, self.size*2))
            rotated_surf = pygame.transform.rotate(rect_surf, self.lifetime * 10)
            screen.blit(rotated_surf, (screen_pos[0] - rotated_surf.get_width()//2, 
                                      screen_pos[1] - rotated_surf.get_height()//2))