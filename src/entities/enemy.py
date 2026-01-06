import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED, ENEMY_COLOR,
    WORLD_WIDTH, WORLD_HEIGHT,
)

# Caché visual: Guarda tuplas (imagen_normal, imagen_flash)
SPRITE_CACHE = {}

class Enemy:
    TYPES = {
        'small': {'size_mult': 0.9, 'health': 30, 'speed_mult': 1.1, 'damage': 5, 'color': (255, 100, 100), 'points': 5},
        'normal': {'size_mult': 1.0, 'health': 50, 'speed_mult': 1.0, 'damage': 10, 'color': (255, 50, 50), 'points': 10},
        'large': {'size_mult': 1.5, 'health': 80, 'speed_mult': 0.7, 'damage': 15, 'color': (200, 0, 0), 'points': 20},
        'tank': {'size_mult': 2.0, 'health': 250, 'speed_mult': 0.5, 'damage': 20, 'color': (150, 0, 0), 'points': 30}
    }
    
    def __init__(self, x, y, speed_multiplier=1.0, enemy_type='normal'):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        type_data = self.TYPES[enemy_type]
        
        self.size = int(ENEMY_SIZE * type_data['size_mult'])
        self.base_speed = ENEMY_SPEED * speed_multiplier * type_data['speed_mult']
        self.color = type_data['color']
        self.damage = type_data['damage']
        self.max_health = type_data['health']
        self.health = self.max_health
        self.points = type_data['points']

        # HITBOX Y PADDING
        self.hitbox_padding = 10
        self.hitbox_total = self.size + self.hitbox_padding
        
        # Generamos (o recuperamos) las DOS imágenes
        self.image, self.flash_image = self._get_cached_sprite(self.size, self.hitbox_total, self.color)
        
        self.rect = pygame.Rect(0, 0, self.hitbox_total, self.hitbox_total)
        self.rect.center = (self.x, self.y)
        
        # FÍSICA SUAVE (Radio un poco menor para permitir overlap visual)
        self.radius = self.size * 0.40 
        self.speed_variance = random.uniform(0.9, 1.1)
        
        # Velocidad calculada (Batching)
        self.vx = 0
        self.vy = 0

        # Estado
        self.is_alive = True
        self.attack_cooldown = 0
        self.attack_delay = 60
        
        self.knockback_x = 0
        self.knockback_y = 0
        self.knockback_decay = 0.88
        
        self.damage_flash = 0
        self.bleed_intensity = 0.0
        self.bleed_decay = 0.3
        self.bleed_drip_cooldown = 0

    def _get_cached_sprite(self, size, total_size, color):
        """
        Genera dos sprites:
        1. Normal: Tu diseño original.
        2. Flash: Cuerpo BLANCO, pero bordes y centro oscuros (para el efecto de daño).
        """
        key = (size, total_size, color)
        if key not in SPRITE_CACHE:
            # PREPARACIÓN COMÚN
            offset = (total_size - size) // 2
            draw_rect = pygame.Rect(offset, offset, size, size)
            border_color = tuple(max(0, c - 50) for c in color)
            
            center_size = max(2, size // 3)
            c_pos = offset + (size - center_size) // 2
            center_rect = (c_pos, c_pos, center_size, center_size)

            # IMAGEN NORMAL
            surf = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
            pygame.draw.rect(surf, color, draw_rect)
            pygame.draw.rect(surf, border_color, draw_rect, 2)
            pygame.draw.rect(surf, border_color, center_rect)
            
            # IMAGEN FLASH (DAÑO)
            surf_flash = pygame.Surface((total_size, total_size), pygame.SRCALPHA)
            pygame.draw.rect(surf_flash, (255, 255, 255), draw_rect)
            pygame.draw.rect(surf_flash, border_color, draw_rect, 2)
            pygame.draw.rect(surf_flash, border_color, center_rect)
            
            SPRITE_CACHE[key] = (surf, surf_flash)
            
        return SPRITE_CACHE[key]
    
    def update_ai(self, player_pos, spatial_grid):
        """ LÓGICA DE MOVIMIENTO OPTIMIZADA (TIME SLICING) """
        if not self.is_alive: return

        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx*dx + dy*dy
        dist_to_player = math.sqrt(dist_sq) if dist_sq > 0 else 0.001
        
        dir_x = dx / dist_to_player
        dir_y = dy / dist_to_player

        attack_range = self.size * 0.6 + 10
        current_move_speed = 0
        if dist_to_player > attack_range:
            current_move_speed = self.base_speed * self.speed_variance
            
        push_x, push_y = 0, 0
        
        if spatial_grid:
            neighbors = spatial_grid.get_nearby(self.x, self.y, radius=1)
            collision_radius_sq = (self.radius * 2) ** 2 
            
            count = 0
            for other in neighbors:
                if other is self or not other.is_alive: continue
                if count > 6: break 
                
                odx = self.x - other.x
                ody = self.y - other.y
                odist_sq = odx*odx + ody*ody
                
                if 0 < odist_sq < collision_radius_sq:
                    odist = math.sqrt(odist_sq)
                    overlap = (self.radius * 2) - odist
                    
                    # FUERZA SUAVE (0.05) para permitir enjambre
                    push_strength = overlap * 0.05 
                    
                    push_x += (odx / odist) * push_strength
                    push_y += (ody / odist) * push_strength
                    count += 1
        
        self.vx = (dir_x * current_move_speed) + push_x
        self.vy = (dir_y * current_move_speed) + push_y

    def update_physics(self, dt=1.0):
        if not self.is_alive: return
        
        self.x += (self.vx + self.knockback_x) * dt
        self.y += (self.vy + self.knockback_y) * dt
        
        if abs(self.knockback_x) > 0.01 or abs(self.knockback_y) > 0.01:
            self.knockback_x *= self.knockback_decay ** dt
            self.knockback_y *= self.knockback_decay ** dt
            if abs(self.knockback_x) < 0.1: self.knockback_x = 0
            if abs(self.knockback_y) < 0.1: self.knockback_y = 0
        
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)
        
        if self.attack_cooldown > 0: self.attack_cooldown -= 1 * dt
        if self.damage_flash > 0: self.damage_flash -= 1 * dt

    def update(self, particle_system=None, dt=1.0):
        if not self.is_alive: return
        
        if self.bleed_intensity > 0:
            self.bleed_intensity -= self.bleed_decay * dt
            if self.bleed_intensity < 0: self.bleed_intensity = 0
            
            if self.bleed_drip_cooldown > 0:
                self.bleed_drip_cooldown -= 1 * dt
            
            if self.bleed_drip_cooldown <= 0 and particle_system:
                delay = max(2, 20 - (self.bleed_intensity * 0.8))
                particle_system.create_blood_drip(self.x, self.y, self.bleed_intensity)
                self.bleed_drip_cooldown = delay
    
    def can_attack(self):
        return self.attack_cooldown <= 0
    
    def attack(self, player):
        if not self.is_alive or not self.can_attack():
            return False
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.attack_cooldown = self.attack_delay
            return True
        return False
    
    def take_damage(self, damage):
        if not self.is_alive: return False
        
        self.health -= damage
        self.damage_flash = 10
        self.bleed_intensity += damage 
        if self.bleed_intensity > 40: self.bleed_intensity = 40
            
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True
        return False
    
    def apply_knockback(self, projectile_x, projectile_y, force=5):
        dx = self.x - projectile_x
        dy = self.y - projectile_y
        dist_sq = dx*dx + dy*dy
        if dist_sq > 1:
            inv_dist = 1.0 / math.sqrt(dist_sq)
            dx *= inv_dist
            dy *= inv_dist
            size_factor = 1.0 / self.TYPES[self.enemy_type]['size_mult']
            self.knockback_x = dx * force * size_factor
            self.knockback_y = dy * force * size_factor

    def render(self, screen, camera):
        if not self.is_alive: return
        
        if not camera.is_on_screen(self.rect):
            return

        screen_pos = camera.apply_coords(self.rect.x, self.rect.y)
        
        screen.blit(self.image, screen_pos)
        
        if self.damage_flash > 0:
            alpha = int(min(255, max(0, self.damage_flash * 25.5))) 
            self.flash_image.set_alpha(alpha)
            screen.blit(self.flash_image, screen_pos)

        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 4
            health_width = (self.health / self.max_health) * bar_width
            
            offset = (self.hitbox_total - self.size) // 2
            bar_x = screen_pos[0] + offset
            bar_y = screen_pos[1] + offset - 7
            
            pygame.draw.rect(screen, (60, 0, 0), (bar_x, bar_y, bar_width, bar_height))
            
            health_color = (255, 0, 0) if self.health < self.max_health * 0.3 else (255, 100, 0)
            pygame.draw.rect(screen, health_color, (bar_x, bar_y, health_width, bar_height))

    @staticmethod
    def spawn_random(speed_multiplier=1.0, wave=1):
        side = random.choice(['top', 'bottom', 'left', 'right'])
        
        if side == 'top':
            x = random.randint(0, WORLD_WIDTH)
            y = -30
        elif side == 'bottom':
            x = random.randint(0, WORLD_WIDTH)
            y = WORLD_HEIGHT + 30
        elif side == 'left':
            x = -30
            y = random.randint(0, WORLD_HEIGHT)
        else:
            x = WORLD_WIDTH + 30
            y = random.randint(0, WORLD_HEIGHT)
        
        rand = random.random()
        if wave < 3:
            enemy_type = 'small' if rand < 0.3 else 'normal'
        elif wave < 6:
            if rand < 0.2: enemy_type = 'small'
            elif rand < 0.7: enemy_type = 'normal'
            else: enemy_type = 'large'
        else:
            if rand < 0.15: enemy_type = 'small'
            elif rand < 0.5: enemy_type = 'normal'
            elif rand < 0.8: enemy_type = 'large'
            else: enemy_type = 'tank'
        
        return Enemy(x, y, speed_multiplier, enemy_type)