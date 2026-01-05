"""
Clase de proyectiles mejorada
"""
import pygame
import math
from settings import YELLOW, WINDOW_WIDTH, WINDOW_HEIGHT

class Projectile:
    def __init__(self, x, y, angle, speed=10, damage=25, penetration=1, lifetime=120, image_type='circle'):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = 6
        self.color = YELLOW
        self.damage = damage
        self.penetration = penetration  # Cuántos enemigos puede golpear
        self.lifetime = lifetime        # Cuánto tiempo dura (frames)
        self.is_alive = True
        self.image_type = image_type    # 'circle', 'square', etc.
        
        # Lista de enemigos ya golpeados para no dañarlos cada frame
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
        
        # Reducir vida útil
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.is_alive = False
            
        # Límites de pantalla (con margen)
        if (self.x < -50 or self.x > WINDOW_WIDTH + 50 or
            self.y < -50 or self.y > WINDOW_HEIGHT + 50):
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
                    
                    return enemy # Retorna el enemigo golpeado
        return None
    
    def render(self, screen):
        if not self.is_alive:
            return
            
        pos = (int(self.x), int(self.y))
        
        if self.image_type == 'circle':
            pygame.draw.circle(screen, self.color, pos, self.size)
            # Brillo
            pygame.draw.circle(screen, (255, 255, 200), pos, max(1, self.size // 2))
            
        elif self.image_type == 'square':
            # Efecto de rotación simple
            rect_surf = pygame.Surface((self.size*2, self.size*2), pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, self.color, (0, 0, self.size*2, self.size*2))
            rotated_surf = pygame.transform.rotate(rect_surf, self.lifetime * 10)
            screen.blit(rotated_surf, (self.x - rotated_surf.get_width()//2, self.y - rotated_surf.get_height()//2))