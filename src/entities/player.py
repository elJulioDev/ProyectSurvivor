"""
Jugador optimizado con DeltaTime + Sistema de Dash Profesional
"""

import pygame, math

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
        
        # SISTEMA DE DASH MEJORADO
        self.dash_active = False
        self.dash_timer = 0
        self.dash_duration = 12  # Frames
        self.dash_cooldown = 45  # Frames
        self.dash_cooldown_timer = 0
        self.dash_speed = 24  # Más rápido para mejor sensación
        self.dash_vector = (0, 0)
        
        # Input buffering para dash
        self.dash_buffer_timer = 0
        self.dash_buffer_duration = 9  # 150ms a 60fps
        
        # Ghost trail para efectos visuales
        self.ghost_positions = []
        self.max_ghosts = 5
        
        self.last_shot_time = 0
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
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
            
            # DASH CON TECLA DEDICADA (CTRL)
            elif event.key in [pygame.K_LCTRL, pygame.K_RCTRL]:
                self._attempt_dash()
    
    def _attempt_dash(self):
        """Intenta ejecutar el dash con sistema de buffering"""
        # Si está en cooldown, activar buffer
        if self.dash_cooldown_timer > 0:
            self.dash_buffer_timer = self.dash_buffer_duration
            return
        
        # Ejecutar dash inmediatamente
        self._execute_dash()
    
    def _execute_dash(self):
        """Ejecuta el dash calculando la dirección correcta"""
        # Obtener input actual del teclado
        keys = pygame.key.get_pressed()
        
        dash_dx = 0
        dash_dy = 0
        
        # 1. PRIORIDAD: Dirección basada en teclas presionadas (8 direcciones)
        input_x = 0
        input_y = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]: input_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: input_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: input_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: input_x += 1
        
        # Si hay input de teclado, usarlo
        if input_x != 0 or input_y != 0:
            # Normalizar dirección diagonal
            magnitude = math.sqrt(input_x * input_x + input_y * input_y)
            dash_dx = input_x / magnitude
            dash_dy = input_y / magnitude
        else:
            # 2. FALLBACK: Si no hay teclas, hacer dash hacia el mouse
            dash_dx = math.cos(self.angle)
            dash_dy = math.sin(self.angle)
        
        # Activar dash
        self.dash_active = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown_timer = self.dash_cooldown
        self.dash_vector = (dash_dx, dash_dy)
        self.dash_buffer_timer = 0  # Reset buffer
        
        # Limpiar ghosts para nuevo trail
        self.ghost_positions = []
        
    def handle_input(self, keys, dt=1.0):
        """Maneja el movimiento del jugador"""
        # Durante dash, no permitir control (opcional: puedes permitirlo para más control)
        if self.dash_active:
            return
        
        input_x = 0
        input_y = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]: input_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]: input_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]: input_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: input_x += 1
        
        # Normalizar input diagonal
        if input_x != 0 and input_y != 0:
            input_x *= 0.7071
            input_y *= 0.7071
        
        # Aplicar aceleración
        self.vel_x += input_x * self.accel * dt
        self.vel_y += input_y * self.accel * dt
        
        # Aplicar fricción
        friction_factor = self.friction ** dt
        self.vel_x *= friction_factor
        self.vel_y *= friction_factor
        
        # Limitar velocidad máxima
        speed_sq = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        max_speed_sq = self.max_speed * self.max_speed
        
        if speed_sq > max_speed_sq:
            scale = self.max_speed / math.sqrt(speed_sq)
            self.vel_x *= scale
            self.vel_y *= scale
        
        # Snap a 0 si muy lento
        if abs(self.vel_x) < 0.1: self.vel_x = 0
        if abs(self.vel_y) < 0.1: self.vel_y = 0
    
    def update_rotation(self, mouse_pos, camera_offset=(0, 0)):
        """Actualiza la rotación hacia el mouse"""
        screen_player_x = self.x + camera_offset[0]
        screen_player_y = self.y + camera_offset[1]
        
        dx = mouse_pos[0] - screen_player_x
        dy = mouse_pos[1] - screen_player_y
        
        self.angle = math.atan2(dy, dx)
    
    def update(self, dt=1.0):
        """Actualiza el estado del jugador"""
        if not self.is_alive:
            return
        
        # Actualizar cooldown del dash
        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1 * dt
            
            # Sistema de buffering: Si el cooldown termina y hay buffer activo, ejecutar dash
            if self.dash_cooldown_timer <= 0 and self.dash_buffer_timer > 0:
                self._execute_dash()
        
        # Actualizar buffer timer
        if self.dash_buffer_timer > 0:
            self.dash_buffer_timer -= 1 * dt
        
        # Movimiento durante dash
        if self.dash_active:
            # Guardar posición para ghost trail
            if len(self.ghost_positions) < self.max_ghosts:
                self.ghost_positions.append((self.x, self.y, self.angle))
            else:
                # Rotar lista (FIFO)
                self.ghost_positions.pop(0)
                self.ghost_positions.append((self.x, self.y, self.angle))
            
            # Aplicar movimiento de dash
            self.x += self.dash_vector[0] * self.dash_speed * dt
            self.y += self.dash_vector[1] * self.dash_speed * dt
            
            # Mantener momentum en la dirección del dash
            self.vel_x = self.dash_vector[0] * self.max_speed * 0.8
            self.vel_y = self.dash_vector[1] * self.max_speed * 0.8
            
            # Decrementar timer
            self.dash_timer -= 1 * dt
            if self.dash_timer <= 0:
                self.dash_active = False
                self.ghost_positions = []  # Limpiar ghosts al terminar
        else:
            # Movimiento normal
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt
        
        # Colisiones con bordes del mundo
        if self.x < self.size: 
            self.x = self.size
            self.vel_x = 0
        elif self.x > WORLD_WIDTH - self.size: 
            self.x = WORLD_WIDTH - self.size
            self.vel_x = 0
            
        if self.y < self.size: 
            self.y = self.size
            self.vel_y = 0
        elif self.y > WORLD_HEIGHT - self.size: 
            self.y = WORLD_HEIGHT - self.size
            self.vel_y = 0
        
        # Actualizar hitbox
        hitbox_size = self.size - 4
        self.rect.x = self.x - hitbox_size // 2
        self.rect.y = self.y - hitbox_size // 2
        
        # Actualizar efectos visuales
        if self.damage_flash > 0: 
            self.damage_flash -= 1 * dt
        if self.invulnerable_frames > 0: 
            self.invulnerable_frames -= 1 * dt
    
    def take_damage(self, damage):
        """Recibe daño con invulnerabilidad durante dash"""
        if not self.is_alive or self.invulnerable_frames > 0 or self.dash_active:
            return
        
        self.health -= damage
        self.damage_flash = 15
        self.invulnerable_frames = 60
        
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
    
    def heal(self, amount):
        """Cura al jugador"""
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        if self.health > old_health:
            print(f"Curado: +{amount} HP (Total: {self.health})")
    
    def attack(self, camera=None):
        """Dispara el arma actual"""
        if not self.is_alive or self.dash_active:
            return False
        
        current_weapon = self.weapons[self.current_weapon_index]
        did_shoot = current_weapon.shoot(camera)
        
        if did_shoot:
            self.last_shot_time = pygame.time.get_ticks()
        
        return did_shoot
    
    def render(self, screen, camera):
        """Renderiza el jugador con efectos mejorados"""
        if not self.is_alive:
            return
        
        screen_pos = camera.apply_coords(self.x, self.y)
        screen_x, screen_y = int(screen_pos[0]), int(screen_pos[1])
        
        # Parpadeo de invulnerabilidad
        if self.invulnerable_frames > 0 and int(self.invulnerable_frames) % 6 < 3:
            return
        
        # Efectos de dash con ghost trail mejorado
        if self.dash_active and len(self.ghost_positions) > 0:
            for i, (gx, gy, gangle) in enumerate(self.ghost_positions):
                # Alpha decreciente
                alpha = int(180 * (i / max(1, len(self.ghost_positions))))
                
                ghost_screen = camera.apply_coords(gx, gy)
                gsx, gsy = int(ghost_screen[0]), int(ghost_screen[1])
                
                # Superficie ghost
                ghost_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                ghost_surf.fill((255, 255, 255, alpha))
                
                screen.blit(ghost_surf, (gsx - self.size//2, gsy - self.size//2))
                
                # Línea de dirección ghost
                if alpha > 50:
                    end_x = gsx + math.cos(gangle) * (self.size * 1.2)
                    end_y = gsy + math.sin(gangle) * (self.size * 1.2)
                    pygame.draw.line(screen, (255, 255, 255, alpha), 
                                   (gsx, gsy), (end_x, end_y), 2)
        
        # Color del jugador
        render_color = self.color
        if self.damage_flash > 0:
            flash = int(255 * (self.damage_flash / 15))
            render_color = (255, max(0, 255 - flash), max(0, 255 - flash))
        
        # Dibujar jugador
        pygame.draw.rect(screen, render_color, 
                        (screen_x - self.size//2, screen_y - self.size//2, 
                         self.size, self.size))
        
        # Línea de dirección
        end_x = screen_x + math.cos(self.angle) * (self.size * 1.2)
        end_y = screen_y + math.sin(self.angle) * (self.size * 1.2)
        pygame.draw.line(screen, render_color, (screen_x, screen_y), 
                        (end_x, end_y), 3)
    
    def get_position(self):
        return (self.x, self.y)
