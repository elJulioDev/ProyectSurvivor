"""
Clase de enemigos con variaciones y retroceso corregido
"""
import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED, ENEMY_COLOR,
    ENEMY_DAMAGE, WINDOW_WIDTH, WINDOW_HEIGHT
)

class Enemy:
    # Tipos de enemigos
    TYPES = {
        'small': {'size_mult': 0.7, 'health': 30, 'speed_mult': 1.3, 'damage': 5, 'color': (255, 100, 100), 'points': 5},
        'normal': {'size_mult': 1.0, 'health': 50, 'speed_mult': 1.0, 'damage': 10, 'color': (255, 50, 50), 'points': 10},
        'large': {'size_mult': 1.5, 'health': 80, 'speed_mult': 0.7, 'damage': 15, 'color': (200, 0, 0), 'points': 20},
        'tank': {'size_mult': 2.0, 'health': 150, 'speed_mult': 0.5, 'damage': 20, 'color': (150, 0, 0), 'points': 30}
    }
    
    def __init__(self, x, y, speed_multiplier=1.0, enemy_type='normal'):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        type_data = self.TYPES[enemy_type]
        
        # Propiedades basadas en tipo
        self.size = int(ENEMY_SIZE * type_data['size_mult'])
        self.speed = ENEMY_SPEED * speed_multiplier * type_data['speed_mult']
        self.color = type_data['color']
        self.damage = type_data['damage']
        self.max_health = type_data['health']
        self.health = self.max_health
        self.points = type_data['points']
        
        # Estado
        self.is_alive = True
        
        # Cooldown de ataque
        self.attack_cooldown = 0
        self.attack_delay = 60
        
        # Efectos de retroceso
        self.knockback_x = 0
        self.knockback_y = 0
        self.knockback_decay = 0.88
        
        # Efecto de daño visual
        self.damage_flash = 0
        
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
            
            # Aplicar movimiento normal + knockback
            self.x += dx * self.speed + self.knockback_x
            self.y += dy * self.speed + self.knockback_y
        
        # Aplicar decay al knockback
        self.knockback_x *= self.knockback_decay
        self.knockback_y *= self.knockback_decay
        
        # Si el knockback es muy pequeño, eliminarlo
        if abs(self.knockback_x) < 0.1:
            self.knockback_x = 0
        if abs(self.knockback_y) < 0.1:
            self.knockback_y = 0
        
        # Actualizar hitbox
        self.rect.x = self.x - self.size // 2
        self.rect.y = self.y - self.size // 2
    
    def apply_knockback(self, projectile_x, projectile_y, force=5):
        """Aplica retroceso al enemigo desde la posición del proyectil"""
        # Calcular dirección desde el proyectil hacia el enemigo
        dx = self.x - projectile_x
        dy = self.y - projectile_y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > 0:
            # Normalizar dirección
            dx /= distance
            dy /= distance
            
            # Aplicar fuerza ajustada por tamaño (enemigos grandes retroceden menos)
            size_factor = 1.0 / self.TYPES[self.enemy_type]['size_mult']
            self.knockback_x = dx * force * size_factor
            self.knockback_y = dy * force * size_factor
    
    def update(self):
        """Actualiza el estado del enemigo"""
        if not self.is_alive:
            return
        
        # Reducir cooldown de ataque
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        
        # Reducir efecto de flash de daño
        if self.damage_flash > 0:
            self.damage_flash -= 1
    
    def can_attack(self):
        """Verifica si puede atacar"""
        return self.attack_cooldown == 0
    
    def attack(self, player):
        """Ataca al jugador si está en rango"""
        if not self.is_alive or not self.can_attack():
            return False
        
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
        self.damage_flash = 10
        
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True
        
        return False
    
    def render(self, screen):
        """Renderiza el enemigo con efectos"""
        if not self.is_alive:
            return
        
        # Color con efecto de flash cuando recibe daño
        render_color = self.color
        if self.damage_flash > 0:
            flash_intensity = int(255 * (self.damage_flash / 10))
            render_color = (
                min(255, self.color[0] + flash_intensity),
                min(255, self.color[1] + flash_intensity),
                min(255, self.color[2] + flash_intensity)
            )
        
        # Dibujar cuerpo
        pygame.draw.rect(screen, render_color, self.rect)
        
        # Dibujar borde más oscuro
        border_color = tuple(max(0, c - 50) for c in self.color)
        pygame.draw.rect(screen, border_color, self.rect, 2)
        
        # Dibujar punto central para dar sensación de profundidad
        center_size = max(2, self.size // 3)
        center_rect = pygame.Rect(
            self.rect.centerx - center_size // 2,
            self.rect.centery - center_size // 2,
            center_size,
            center_size
        )
        pygame.draw.rect(screen, border_color, center_rect)
        
        # Barra de vida
        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 4
            health_width = (self.health / self.max_health) * bar_width
            
            # Fondo
            pygame.draw.rect(
                screen,
                (60, 0, 0),
                (self.rect.x, self.rect.y - 7, bar_width, bar_height)
            )
            # Vida actual
            health_color = (255, 0, 0) if self.health < self.max_health * 0.3 else (255, 100, 0)
            pygame.draw.rect(
                screen,
                health_color,
                (self.rect.x, self.rect.y - 7, health_width, bar_height)
            )
    
    @staticmethod
    def spawn_random(speed_multiplier=1.0, wave=1):
        """Genera un enemigo aleatorio basado en la oleada"""
        side = random.choice(['top', 'bottom', 'left', 'right'])
        
        if side == 'top':
            x = random.randint(0, WINDOW_WIDTH)
            y = -30
        elif side == 'bottom':
            x = random.randint(0, WINDOW_WIDTH)
            y = WINDOW_HEIGHT + 30
        elif side == 'left':
            x = -30
            y = random.randint(0, WINDOW_HEIGHT)
        else:
            x = WINDOW_WIDTH + 30
            y = random.randint(0, WINDOW_HEIGHT)
        
        # Determinar tipo basado en oleada
        rand = random.random()
        if wave < 3:
            enemy_type = 'small' if rand < 0.3 else 'normal'
        elif wave < 6:
            if rand < 0.2:
                enemy_type = 'small'
            elif rand < 0.7:
                enemy_type = 'normal'
            else:
                enemy_type = 'large'
        else:
            if rand < 0.15:
                enemy_type = 'small'
            elif rand < 0.5:
                enemy_type = 'normal'
            elif rand < 0.8:
                enemy_type = 'large'
            else:
                enemy_type = 'tank'
        
        return Enemy(x, y, speed_multiplier, enemy_type)