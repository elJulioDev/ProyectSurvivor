"""
Clase de proyectiles mejorada
"""
import pygame
import math
from settings import YELLOW, WORLD_WIDTH, WORLD_HEIGHT # <--- CAMBIO IMPORTANTE

class Projectile:
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
    
    def update(self):
        if not self.is_alive:
            return
        
        self.x += self.vel_x
        self.y += self.vel_y
        
        self.rect.x = int(self.x - self.size // 2)
        self.rect.y = int(self.y - self.size // 2)
        
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.is_alive = False
            
        # --- CORRECCIÓN: Usar límites del MUNDO, no de la ventana ---
        if (self.x < -50 or self.x > WORLD_WIDTH + 50 or
            self.y < -50 or self.y > WORLD_HEIGHT + 50):
            self.is_alive = False
    
    def check_collision(self, enemies):
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
            screen.blit(rotated_surf, (screen_pos[0] - rotated_surf.get_width()//2, screen_pos[1] - rotated_surf.get_height()//2))