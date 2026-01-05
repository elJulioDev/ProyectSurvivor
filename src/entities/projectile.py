"""
Clase de proyectiles
"""
import pygame
import math
from settings import YELLOW

class Projectile:
    def __init__(self, x, y, angle, speed=10):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = 5
        self.color = YELLOW
        self.damage = 25
        self.is_alive = True
        
        # Calcular velocidad
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed
        
        # Hitbox
        self.rect = pygame.Rect(
            self.x - self.size // 2,
            self.y - self.size // 2,
            self.size,
            self.size
        )
    
    def update(self):
        """Actualiza la posición del proyectil"""
        if not self.is_alive:
            return
        
        self.x += self.vel_x
        self.y += self.vel_y
        
        # Actualizar hitbox
        self.rect.x = self.x - self.size // 2
        self.rect.y = self.y - self.size // 2
        
        # Eliminar si sale de la pantalla
        from settings import WINDOW_WIDTH, WINDOW_HEIGHT
        if (self.x < -10 or self.x > WINDOW_WIDTH + 10 or
            self.y < -10 or self.y > WINDOW_HEIGHT + 10):
            self.is_alive = False
    
    def check_collision(self, enemies):
        """Verifica colisión con enemigos"""
        if not self.is_alive:
            return None
        
        for enemy in enemies:
            if enemy.is_alive and self.rect.colliderect(enemy.rect):
                self.is_alive = False
                return enemy
        
        return None
    
    def render(self, screen):
        """Renderiza el proyectil"""
        if not self.is_alive:
            return
        
        pygame.draw.circle(
            screen,
            self.color,
            (int(self.x), int(self.y)),
            self.size
        )
        
        # Efecto de brillo
        pygame.draw.circle(
            screen,
            (255, 255, 200),
            (int(self.x), int(self.y)),
            self.size // 2
        )