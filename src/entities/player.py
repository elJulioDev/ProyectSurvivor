"""
Clase del jugador
"""
import pygame
import math
from settings import (
    PLAYER_SIZE, PLAYER_SPEED, PLAYER_COLOR,
    WINDOW_WIDTH, WINDOW_HEIGHT
)

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = PLAYER_SIZE
        self.speed = PLAYER_SPEED
        self.color = PLAYER_COLOR
        
        # Velocidad actual
        self.vel_x = 0
        self.vel_y = 0
        
        # Ángulo de rotación (hacia donde mira el jugador)
        self.angle = 0
        
        # Estadísticas
        self.health = 100
        self.max_health = 100
        self.is_alive = True
        
        # Hitbox (rectángulo de colisión)
        self.rect = pygame.Rect(
            self.x - self.size // 2,
            self.y - self.size // 2,
            self.size,
            self.size
        )
    
    def handle_input(self, keys):
        """Maneja la entrada del teclado para movimiento"""
        # Resetear velocidad
        self.vel_x = 0
        self.vel_y = 0
        
        # Movimiento WASD o flechas
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.vel_y = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.vel_y = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vel_x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vel_x = self.speed
        
        # Normalizar velocidad diagonal para que no sea más rápida
        if self.vel_x != 0 and self.vel_y != 0:
            self.vel_x *= 0.7071  # 1/sqrt(2)
            self.vel_y *= 0.7071
    
    def update_rotation(self, mouse_pos):
        """Actualiza la rotación del jugador hacia el mouse"""
        # Calcular ángulo entre el jugador y el mouse
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        self.angle = math.atan2(dy, dx)
    
    def update(self, dt=1):
        """Actualiza la posición del jugador"""
        if not self.is_alive:
            return
        
        # Actualizar posición
        self.x += self.vel_x * dt
        self.y += self.vel_y * dt
        
        # Limitar al área de la pantalla
        self.x = max(self.size, min(WINDOW_WIDTH - self.size, self.x))
        self.y = max(self.size, min(WINDOW_HEIGHT - self.size, self.y))
        
        # Actualizar hitbox
        self.rect.x = self.x - self.size // 2
        self.rect.y = self.y - self.size // 2
    
    def take_damage(self, damage):
        """Recibe daño"""
        if not self.is_alive:
            return
        
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
    
    def heal(self, amount):
        """Cura al jugador"""
        self.health = min(self.max_health, self.health + amount)
    
    def render(self, screen):
        """Renderiza el jugador"""
        if not self.is_alive:
            return
        
        # Dibujar cuerpo (cuadrado)
        pygame.draw.rect(screen, self.color, self.rect)
        
        # Dibujar dirección (línea que indica hacia donde mira)
        end_x = self.x + math.cos(self.angle) * (self.size * 0.8)
        end_y = self.y + math.sin(self.angle) * (self.size * 0.8)
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (self.x, self.y),
            (end_x, end_y),
            3
        )
        
        # Dibujar borde para mejor visibilidad
        pygame.draw.rect(screen, (255, 255, 255), self.rect, 2)
    
    def get_position(self):
        """Retorna la posición actual"""
        return (self.x, self.y)
    
    def get_direction(self):
        """Retorna la dirección actual como vector"""
        return (math.cos(self.angle), math.sin(self.angle))