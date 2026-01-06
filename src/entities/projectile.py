import pygame
import math
from settings import YELLOW, WORLD_WIDTH, WORLD_HEIGHT

class Projectile:
    __slots__ = (
        'x', 'y', 'angle', 'speed', 'size', 'color', 'damage', 
        'penetration', 'lifetime', 'is_alive', 'image_type', 
        'hit_enemies', 'vel_x', 'vel_y', 'rect', 'hitbox_size'
    )
    def __init__(self, x, y, angle, speed=10, damage=25, penetration=1, lifetime=120, image_type='circle'):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = 6
        self.hitbox_size = 20
        self.color = YELLOW
        self.damage = damage
        self.penetration = penetration
        self.lifetime = lifetime
        self.is_alive = True
        self.image_type = image_type
        self.hit_enemies = []
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed
        
        # La hitbox usa el tamaño grande
        self.rect = pygame.Rect(
            int(self.x - self.hitbox_size // 2), 
            int(self.y - self.hitbox_size // 2),
            self.hitbox_size, 
            self.hitbox_size
        )
    
    def update(self, dt=1.0):
        if not self.is_alive:
            return
        
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        # Actualizar rect con el tamaño grande
        self.rect.x = int(self.x - self.hitbox_size // 2)
        self.rect.y = int(self.y - self.hitbox_size // 2)
        
        self.lifetime -= 1 * dt
        if self.lifetime <= 0:
            self.is_alive = False
            
        if (self.x < -50 or self.x > WORLD_WIDTH + 50 or
            self.y < -50 or self.y > WORLD_HEIGHT + 50):
            self.is_alive = False
    
    def check_collision_grid(self, spatial_grid):
        if not self.is_alive:
            return None
        
        # Buscamos enemigos cercanos (radio un poco mayor por si acaso)
        nearby_enemies = spatial_grid.get_nearby(self.x, self.y, radius=1)
        
        for enemy in nearby_enemies:
            if enemy.is_alive and enemy not in self.hit_enemies:
                # La colisión ya usa self.rect que es GRANDE (20px)
                if self.rect.colliderect(enemy.rect):
                    self.hit_enemies.append(enemy)
                    self.penetration -= 1
                    if self.penetration <= 0:
                        self.is_alive = False
                    return enemy
        return None

    # (El resto de métodos check_collision y render se mantienen igual, 
    #  render usará self.size así que visualmente no cambia nada)
    def render(self, screen, camera):
        if not self.is_alive:
            return
            
        screen_pos = camera.apply_coords(self.x, self.y)
        try:
            center = (int(screen_pos[0]), int(screen_pos[1]))
        except:
            return

        if self.image_type == 'circle':
            # Dibuja usando self.size (6px) para que se vea nítido
            pygame.draw.circle(screen, self.color, center, self.size)
            pygame.draw.circle(screen, (255, 255, 200), center, max(1, self.size // 2))
        elif self.image_type == 'square':
            # Dibuja el cuadrado visual
            rect_surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, self.color, (0, 0, self.size*2, self.size*2))
            rotated_surf = pygame.transform.rotate(rect_surf, self.lifetime * 10)
            screen.blit(rotated_surf, (screen_pos[0] - rotated_surf.get_width()//2, 
                                      screen_pos[1] - rotated_surf.get_height()//2))