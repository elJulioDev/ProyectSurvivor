"""
Jugador optimizado con DeltaTime + Cambio de Armas + Curación
"""
import pygame
import math
from settings import (
    PLAYER_SIZE, PLAYER_SPEED, PLAYER_ACCEL, PLAYER_FRICTION,
    WHITE, WORLD_WIDTH, WORLD_HEIGHT
)
from entities.weapon import PistolWeapon, ShotgunWeapon, LaserWeapon, AssaultRifleWeapon

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = PLAYER_SIZE
        self.color = WHITE
        
        self.vel_x = 0
        self.vel_y = 0
        self.accel = PLAYER_ACCEL
        self.friction = PLAYER_FRICTION
        self.max_speed = PLAYER_SPEED
        
        self.angle = 0
        
        self.health = 100
        self.max_health = 100
        self.is_alive = True
        
        self.damage_flash = 0
        self.invulnerable_frames = 0

        # SISTEMA DE ARMAS
        self.weapons = [
            PistolWeapon(self),
            ShotgunWeapon(self),
            AssaultRifleWeapon(self),
            LaserWeapon(self)
        ]
        self.current_weapon_index = 0
        
        hitbox_size = self.size - 4
        self.rect = pygame.Rect(
            self.x - hitbox_size // 2,
            self.y - hitbox_size // 2,
            hitbox_size,
            hitbox_size
        )

        # Dash mejorado
        self.dash_active = False
        self.dash_timer = 0
        self.dash_duration = 12
        self.dash_cooldown = 45
        self.dash_cooldown_timer = 0
        self.dash_speed = 22
        self.dash_vector = (0, 0)
        
        self.last_key_pressed = None
        self.last_key_time = 0
        self.double_tap_threshold = 250

        self.last_shot_time = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            current_time = pygame.time.get_ticks()
            
            # CAMBIO DE ARMAS
            if event.key == pygame.K_1:
                self.current_weapon_index = 0
            elif event.key == pygame.K_2:
                self.current_weapon_index = 1
            elif event.key == pygame.K_3:
                self.current_weapon_index = 2
            elif event.key == pygame.K_4:
                self.current_weapon_index = 3
            
            # CURACIÓN
            elif event.key == pygame.K_h:
                self.heal(10)
                self.damage_flash = 5
            
            # DASH
            if (event.key in [pygame.K_w, pygame.K_s, pygame.K_a, pygame.K_d, 
                              pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT]):
                
                if (event.key == self.last_key_pressed and 
                    current_time - self.last_key_time < self.double_tap_threshold):
                    self._attempt_dash()
                    self.last_key_pressed = None
                else:
                    self.last_key_pressed = event.key
                    self.last_key_time = current_time

    def _attempt_dash(self):
        if self.dash_cooldown_timer > 0:
            return
            
        dash_dx = 0
        dash_dy = 0
        
        speed_sq = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        
        if speed_sq > 0.01:
            inv_speed = 1.0 / math.sqrt(speed_sq)
            dash_dx = self.vel_x * inv_speed
            dash_dy = self.vel_y * inv_speed
        else:
            dash_dx = math.cos(self.angle)
            dash_dy = math.sin(self.angle)
        
        self.dash_active = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown_timer = self.dash_cooldown
        self.dash_vector = (dash_dx, dash_dy)

    def handle_input(self, keys, dt=1.0):
        if self.dash_active:
            return

        input_x = 0
        input_y = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]: input_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: input_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: input_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: input_x += 1
        
        if input_x != 0 and input_y != 0:
            input_x *= 0.7071
            input_y *= 0.7071
        
        self.vel_x += input_x * self.accel * dt
        self.vel_y += input_y * self.accel * dt
        
        friction_factor = self.friction ** dt
        self.vel_x *= friction_factor
        self.vel_y *= friction_factor
        
        speed_sq = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        max_speed_sq = self.max_speed * self.max_speed
        
        if speed_sq > max_speed_sq:
            scale = self.max_speed / math.sqrt(speed_sq)
            self.vel_x *= scale
            self.vel_y *= scale
            
        if abs(self.vel_x) < 0.1: self.vel_x = 0
        if abs(self.vel_y) < 0.1: self.vel_y = 0
    
    def update_rotation(self, mouse_pos, camera_offset=(0,0)):
        screen_player_x = self.x + camera_offset[0]
        screen_player_y = self.y + camera_offset[1]
        
        dx = mouse_pos[0] - screen_player_x
        dy = mouse_pos[1] - screen_player_y
        self.angle = math.atan2(dy, dx)
    
    def update(self, dt=1.0):
        if not self.is_alive:
            return
        
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1 * dt
            
        if self.dash_active:
            self.x += self.dash_vector[0] * self.dash_speed * dt
            self.y += self.dash_vector[1] * self.dash_speed * dt
            
            self.vel_x = self.dash_vector[0] * self.max_speed
            self.vel_y = self.dash_vector[1] * self.max_speed
            
            self.dash_timer -= 1 * dt
            if self.dash_timer <= 0:
                self.dash_active = False
        else:
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt
        
        if self.x < self.size: self.x = self.size; self.vel_x = 0
        elif self.x > WORLD_WIDTH - self.size: self.x = WORLD_WIDTH - self.size; self.vel_x = 0
            
        if self.y < self.size: self.y = self.size; self.vel_y = 0
        elif self.y > WORLD_HEIGHT - self.size: self.y = WORLD_HEIGHT - self.size; self.vel_y = 0
        
        hitbox_size = self.size - 4
        self.rect.x = self.x - hitbox_size // 2
        self.rect.y = self.y - hitbox_size // 2
        
        if self.damage_flash > 0: self.damage_flash -= 1 * dt
        if self.invulnerable_frames > 0: self.invulnerable_frames -= 1 * dt
    
    def take_damage(self, damage):
        if not self.is_alive or self.invulnerable_frames > 0 or self.dash_active:
            return
        self.health -= damage
        self.damage_flash = 15
        self.invulnerable_frames = 60
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
    
    def heal(self, amount):
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        if self.health > old_health:
            print(f"Curado: +{amount} HP (Total: {self.health})")

    def attack(self, camera=None):
        """Dispara SOLAMENTE el arma seleccionada"""
        if not self.is_alive or self.dash_active:
            return False

        current_weapon = self.weapons[self.current_weapon_index]
        
        did_shoot = current_weapon.shoot(camera)
        if did_shoot:
            self.last_shot_time = pygame.time.get_ticks()
            
        return did_shoot

    def render(self, screen, camera):
        if not self.is_alive:
            return
        screen_pos = camera.apply_coords(self.x, self.y)
        screen_x, screen_y = int(screen_pos[0]), int(screen_pos[1])

        if self.invulnerable_frames > 0 and int(self.invulnerable_frames) % 6 < 3:
            return
        
        if self.dash_active:
            for i in range(3):
                ghost_alpha = 100 - i * 30
                ghost_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                ghost_surf.fill((*self.color[:3], ghost_alpha))
                ghost_x = screen_x - self.dash_vector[0] * (i+1) * 15
                ghost_y = screen_y - self.dash_vector[1] * (i+1) * 15
                screen.blit(ghost_surf, (int(ghost_x - self.size//2), int(ghost_y - self.size//2)))

        render_color = self.color
        if self.damage_flash > 0:
            flash = int(255 * (self.damage_flash / 15))
            # Rojo si es daño, Verde si nos estamos curando (opcional, aquí sigue siendo rojo por simpleza)
            render_color = (255, max(0, 255 - flash), max(0, 255 - flash))
        
        pygame.draw.rect(screen, render_color, (screen_x - self.size//2, screen_y - self.size//2, self.size, self.size))
        
        # Línea de dirección
        end_x = screen_x + math.cos(self.angle) * (self.size * 1.2)
        end_y = screen_y + math.sin(self.angle) * (self.size * 1.2)
        pygame.draw.line(screen, render_color, (screen_x, screen_y), (end_x, end_y), 3)
    
    def get_position(self):
        return (self.x, self.y)