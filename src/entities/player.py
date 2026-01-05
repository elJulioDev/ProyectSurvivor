"""
Clase del jugador mejorada
"""
import pygame
import math
from settings import (
    PLAYER_SIZE, PLAYER_SPEED, WHITE,
    WINDOW_WIDTH, WINDOW_HEIGHT
)
from entities.weapon import WandWeapon, ShotgunWeapon, OrbitalWeapon, LaserWeapon

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

        # Armas
        self.weapons = []
        self.weapons.append(ShotgunWeapon(self)) 
        
        # Hitbox (más pequeña que el sprite visual)
        hitbox_size = self.size - 4
        self.rect = pygame.Rect(
            self.x - hitbox_size // 2,
            self.y - hitbox_size // 2,
            hitbox_size,
            hitbox_size
        )

        # DASH
        self.dash_active = False
        self.dash_timer = 0
        self.dash_duration = 10     # Cuantos frames dura el dash
        self.dash_cooldown = 40     # Cuantos frames esperar para el siguiente
        self.dash_cooldown_timer = 0
        self.dash_speed = 20        # Velocidad durante el dash
        self.dash_vector = (0, 0)
        
        # Variables para detectar doble pulsación
        self.last_key_pressed = None
        self.last_key_time = 0
        self.double_tap_threshold = 250 # Milisegundos para considerar doble tap
    

    def handle_event(self, event):
        """Maneja eventos únicos (para el Dash)"""
        if event.type == pygame.KEYDOWN:
            current_time = pygame.time.get_ticks()
            
            # Detectar Doble Tap
            if (event.key == self.last_key_pressed and 
                current_time - self.last_key_time < self.double_tap_threshold):
                
                # Intentar hacer Dash
                self._attempt_dash(event.key)
                self.last_key_pressed = None # Resetear para evitar triple dash raro
            else:
                self.last_key_pressed = event.key
                self.last_key_time = current_time

    def _attempt_dash(self, key):
        if self.dash_cooldown_timer > 0:
            return
            
        dx, dy = 0, 0
        if key == pygame.K_w or key == pygame.K_UP: dy = -1
        elif key == pygame.K_s or key == pygame.K_DOWN: dy = 1
        elif key == pygame.K_a or key == pygame.K_LEFT: dx = -1
        elif key == pygame.K_d or key == pygame.K_RIGHT: dx = 1
        
        if dx != 0 or dy != 0:
            self.dash_active = True
            self.dash_timer = self.dash_duration
            self.dash_cooldown_timer = self.dash_cooldown
            self.dash_vector = (dx, dy)
            # CORRECCIÓN: Ya no activamos invulnerable_frames aquí para evitar parpadeo y barra de escudo
            # La inmunidad se gestiona en take_damage

    def handle_input(self, keys):
        """Maneja el movimiento normal"""
        # Si estamos en dash, ignoramos el input normal
        if self.dash_active:
            return

        self.vel_x = 0
        self.vel_y = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]: self.vel_y = -self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: self.vel_y = self.speed
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: self.vel_x = -self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: self.vel_x = self.speed
        
        if self.vel_x != 0 and self.vel_y != 0:
            self.vel_x *= 0.7071
            self.vel_y *= 0.7071
    
    def update_rotation(self, mouse_pos):
        """Actualiza rotación hacia el mouse"""
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        self.angle = math.atan2(dy, dx)
    
    def update(self, dt=1):
        if not self.is_alive: return
        
        # --- Lógica de Dash ---
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1
            
        if self.dash_active:
            # Movimiento de dash
            self.x += self.dash_vector[0] * self.dash_speed * dt
            self.y += self.dash_vector[1] * self.dash_speed * dt
            
            self.dash_timer -= 1
            if self.dash_timer <= 0:
                self.dash_active = False
        else:
            # Movimiento normal
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt
        
        # Límites
        self.x = max(self.size, min(WINDOW_WIDTH - self.size, self.x))
        self.y = max(self.size, min(WINDOW_HEIGHT - self.size, self.y))
        
        # Hitbox
        hitbox_size = self.size - 4
        self.rect.x = self.x - hitbox_size // 2
        self.rect.y = self.y - hitbox_size // 2
        
        if self.damage_flash > 0: self.damage_flash -= 1
        if self.invulnerable_frames > 0: self.invulnerable_frames -= 1
    
    def take_damage(self, damage):
        # CORRECCIÓN: Añadimos "or self.dash_active" a la inmunidad
        if not self.is_alive or self.invulnerable_frames > 0 or self.dash_active:
            return
            
        self.health -= damage
        self.damage_flash = 15
        self.invulnerable_frames = 60 # Solo invulnerabilidad por daño
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
    
    def heal(self, amount):
        """Cura al jugador"""
        self.health = min(self.max_health, self.health + amount)
    
    def shoot(self):
        """Dispara proyectil (Legacy)"""
        from entities.projectile import Projectile
        return Projectile(self.x, self.y, self.angle)
    
    def render(self, screen):
        """Renderiza el jugador como pixel blanco con efectos"""
        if not self.is_alive:
            return
        
        # Parpadeo SÓLO durante invulnerabilidad por daño
        if self.invulnerable_frames > 0 and self.invulnerable_frames % 6 < 3:
            return
        
        # Efecto visual del Dash (Estela - se mantiene igual)
        if self.dash_active:
            for i in range(3):
                ghost_alpha = 100 - i * 30
                ghost_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                ghost_surf.fill((*self.color[:3], ghost_alpha))
                offset_x = -self.dash_vector[0] * (i+1) * 10
                offset_y = -self.dash_vector[1] * (i+1) * 10
                screen.blit(ghost_surf, (self.x - self.size//2 + offset_x, self.y - self.size//2 + offset_y))

        # Color con flash de daño
        render_color = self.color
        if self.damage_flash > 0:
            flash = int(255 * (self.damage_flash / 15))
            render_color = (255, max(0, 255 - flash), max(0, 255 - flash))
        
        # Cuerpo principal
        main_rect = pygame.Rect(self.x - self.size//2, self.y - self.size//2, self.size, self.size)
        pygame.draw.rect(screen, render_color, main_rect)
        pygame.draw.rect(screen, (200, 200, 200), main_rect, 1)
        
        # Línea de dirección (cañón)
        end_x = self.x + math.cos(self.angle) * (self.size * 1.2)
        end_y = self.y + math.sin(self.angle) * (self.size * 1.2)
        pygame.draw.line(screen, render_color, (self.x, self.y), (end_x, end_y), 3)
    
    def get_position(self):
        return (self.x, self.y)
    
    def get_direction(self):
        return (math.cos(self.angle), math.sin(self.angle))