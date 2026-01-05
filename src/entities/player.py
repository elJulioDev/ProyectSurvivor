"""
Clase del jugador mejorada
"""
import pygame
import math
from settings import (
    PLAYER_SIZE, PLAYER_SPEED, WHITE,
    WINDOW_WIDTH, WINDOW_HEIGHT
)

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = PLAYER_SIZE
        self.speed = PLAYER_SPEED
        self.color = WHITE
        
        # Velocidad actual
        self.vel_x = 0
        self.vel_y = 0
        
        # Ángulo de rotación
        self.angle = 0
        
        # Estadísticas
        self.health = 100
        self.max_health = 100
        self.is_alive = True
        
        # Efecto de daño
        self.damage_flash = 0
        self.invulnerable_frames = 0
        
        # Hitbox (más pequeña que el sprite visual)
        hitbox_size = self.size - 4
        self.rect = pygame.Rect(
            self.x - hitbox_size // 2,
            self.y - hitbox_size // 2,
            hitbox_size,
            hitbox_size
        )
    
    def handle_input(self, keys):
        """Maneja la entrada del teclado"""
        self.vel_x = 0
        self.vel_y = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.vel_y = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.vel_y = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vel_x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vel_x = self.speed
        
        # Normalizar diagonal
        if self.vel_x != 0 and self.vel_y != 0:
            self.vel_x *= 0.7071
            self.vel_y *= 0.7071
    
    def update_rotation(self, mouse_pos):
        """Actualiza rotación hacia el mouse"""
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        self.angle = math.atan2(dy, dx)
    
    def update(self, dt=1):
        """Actualiza el jugador"""
        if not self.is_alive:
            return
        
        # Actualizar posición
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        # Límites
        self.x = max(self.size, min(WINDOW_WIDTH - self.size, self.x))
        self.y = max(self.size, min(WINDOW_HEIGHT - self.size, self.y))
        
        # Actualizar hitbox
        hitbox_size = self.size - 4
        self.rect.x = self.x - hitbox_size // 2
        self.rect.y = self.y - hitbox_size // 2
        
        # Actualizar efectos
        if self.damage_flash > 0:
            self.damage_flash -= 1
        if self.invulnerable_frames > 0:
            self.invulnerable_frames -= 1
    
    def take_damage(self, damage):
        """Recibe daño con invulnerabilidad temporal"""
        if not self.is_alive or self.invulnerable_frames > 0:
            return
        
        self.health -= damage
        self.damage_flash = 15
        self.invulnerable_frames = 60  # 1 segundo de invulnerabilidad
        
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
    
    def heal(self, amount):
        """Cura al jugador"""
        self.health = min(self.max_health, self.health + amount)
    
    def shoot(self):
        """Dispara proyectil"""
        from entities.projectile import Projectile
        return Projectile(self.x, self.y, self.angle)
    
    def render(self, screen):
        """Renderiza el jugador como pixel blanco con efectos"""
        if not self.is_alive:
            return
        
        # Parpadeo durante invulnerabilidad
        if self.invulnerable_frames > 0 and self.invulnerable_frames % 6 < 3:
            return
        
        # Color con flash de daño
        render_color = self.color
        if self.damage_flash > 0:
            flash = int(255 * (self.damage_flash / 15))
            render_color = (255, max(0, 255 - flash), max(0, 255 - flash))
        
        # Cuerpo principal (pixel blanco)
        main_rect = pygame.Rect(
            self.x - self.size // 2,
            self.y - self.size // 2,
            self.size,
            self.size
        )
        pygame.draw.rect(screen, render_color, main_rect)
        
        # Borde para mejor visibilidad
        pygame.draw.rect(screen, (200, 200, 200), main_rect, 1)
        
        # Línea de dirección (cañón)
        end_x = self.x + math.cos(self.angle) * (self.size * 1.2)
        end_y = self.y + math.sin(self.angle) * (self.size * 1.2)
        pygame.draw.line(
            screen,
            render_color,
            (self.x, self.y),
            (end_x, end_y),
            3
        )
    
    def get_position(self):
        return (self.x, self.y)
    
    def get_direction(self):
        return (math.cos(self.angle), math.sin(self.angle))