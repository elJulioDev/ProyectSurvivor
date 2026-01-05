"""
Clase de enemigos
"""
import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED, ENEMY_COLOR,
    ENEMY_DAMAGE, WINDOW_WIDTH, WINDOW_HEIGHT
)

class Enemy:
    def __init__(self, x, y, speed_multiplier=1.0):
        self.x = x
        self.y = y
        self.size = ENEMY_SIZE
        self.speed = ENEMY_SPEED * speed_multiplier
        self.color = ENEMY_COLOR
        self.damage = ENEMY_DAMAGE
        
        # Estado
        self.is_alive = True
        self.health = 50
        
        # Cooldown de ataque
        self.attack_cooldown = 0
        self.attack_delay = 60  # frames (1 segundo a 60 FPS)
        
        # Hitbox
        self.rect = pygame.Rect(
            self.x - self.size // 2,
            self.y - self.size // 2,
            self.size,
            self.size
        )
    
    def move_towards_player(self, player_pos):
        """Mueve el enemigo hacia el jugador"""
        if not self.is_alive:
            return
        
        # Calcular dirección hacia el jugador
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Normalizar y mover
        if distance > 0:
            dx /= distance
            dy /= distance
            
            self.x += dx * self.speed
            self.y += dy * self.speed
        
        # Actualizar hitbox
        self.rect.x = self.x - self.size // 2
        self.rect.y = self.y - self.size // 2
    
    def update(self):
        """Actualiza el estado del enemigo"""
        if not self.is_alive:
            return
        
        # Reducir cooldown de ataque
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
    
    def can_attack(self):
        """Verifica si puede atacar"""
        return self.attack_cooldown == 0
    
    def attack(self, player):
        """Ataca al jugador si está en rango"""
        if not self.is_alive or not self.can_attack():
            return False
        
        # Verificar colisión con el jugador
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.attack_cooldown = self.attack_delay
            return True
        
        return False
    
    def take_damage(self, damage):
        """Recibe daño"""
        if not self.is_alive:
            return False
        
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True  # Retorna True si murió
        
        return False
    
    def render(self, screen):
        """Renderiza el enemigo"""
        if not self.is_alive:
            return
        
        # Dibujar cuerpo
        pygame.draw.rect(screen, self.color, self.rect)
        
        # Dibujar borde
        pygame.draw.rect(screen, (150, 0, 0), self.rect, 2)
        
        # Dibujar barra de vida pequeña
        if self.health < 50:
            bar_width = self.size
            bar_height = 3
            health_width = (self.health / 50) * bar_width
            
            # Fondo
            pygame.draw.rect(
                screen,
                (100, 0, 0),
                (self.rect.x, self.rect.y - 5, bar_width, bar_height)
            )
            # Vida actual
            pygame.draw.rect(
                screen,
                (255, 0, 0),
                (self.rect.x, self.rect.y - 5, health_width, bar_height)
            )
    
    @staticmethod
    def spawn_random(speed_multiplier=1.0):
        """Genera un enemigo en una posición aleatoria del borde de la pantalla"""
        side = random.choice(['top', 'bottom', 'left', 'right'])
        
        if side == 'top':
            x = random.randint(0, WINDOW_WIDTH)
            y = -ENEMY_SIZE
        elif side == 'bottom':
            x = random.randint(0, WINDOW_WIDTH)
            y = WINDOW_HEIGHT + ENEMY_SIZE
        elif side == 'left':
            x = -ENEMY_SIZE
            y = random.randint(0, WINDOW_HEIGHT)
        else:  # right
            x = WINDOW_WIDTH + ENEMY_SIZE
            y = random.randint(0, WINDOW_HEIGHT)
        
        return Enemy(x, y, speed_multiplier)