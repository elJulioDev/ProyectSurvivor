import pygame
import math
import random
from settings import (
    ENEMY_SIZE, ENEMY_SPEED, ENEMY_COLOR,
    ENEMY_DAMAGE, WORLD_WIDTH, WORLD_HEIGHT,
)

class Enemy:
    TYPES = {
        'small': {'size_mult': 0.7, 'health': 30, 'speed_mult': 1.1, 'damage': 5, 'color': (255, 100, 100), 'points': 5},
        'normal': {'size_mult': 1.0, 'health': 50, 'speed_mult': 1.0, 'damage': 10, 'color': (255, 50, 50), 'points': 10},
        'large': {'size_mult': 1.5, 'health': 80, 'speed_mult': 0.7, 'damage': 15, 'color': (200, 0, 0), 'points': 20},
        'tank': {'size_mult': 2.0, 'health': 150, 'speed_mult': 0.5, 'damage': 20, 'color': (150, 0, 0), 'points': 30}
    }
    
    def __init__(self, x, y, speed_multiplier=1.0, enemy_type='normal'):
        self.x = x
        self.y = y
        self.enemy_type = enemy_type
        type_data = self.TYPES[enemy_type]
        
        self.size = int(ENEMY_SIZE * type_data['size_mult'])
        self.speed = ENEMY_SPEED * speed_multiplier * type_data['speed_mult']
        self.color = type_data['color']
        self.damage = type_data['damage']
        self.max_health = type_data['health']
        self.health = self.max_health
        self.points = type_data['points']

        self.hitbox_padding = 10
        hitbox_total = self.size + self.hitbox_padding
        
        self.bleed_intensity = 0.0
        self.bleed_decay = 0.3
        self.bleed_drip_cooldown = 0
        self.is_alive = True
        
        self.attack_cooldown = 0
        self.attack_delay = 60
        
        self.knockback_x = 0
        self.knockback_y = 0
        self.knockback_decay = 0.88
        
        self.damage_flash = 0
        
        self.rect = pygame.Rect(
            self.x - hitbox_total // 2,
            self.y - hitbox_total // 2,
            hitbox_total,
            hitbox_total
        )
        
        self.bleed_drip_cooldown = 0
        
        # AJUSTES DE FÍSICA SOLIDA
        # Radio físico real (un poco menos que el visual para permitir solapamiento leve)
        self.radius = self.size * 0.45 
        
        # Pequeña variación de velocidad para romper filas perfectas
        self.speed_variance = random.uniform(0.9, 1.1)

    def move_towards_player(self, player_pos, spatial_grid=None, dt=1.0):
        if not self.is_alive:
            return

        # MOVIMIENTO BASE (Perseguir)
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx*dx + dy*dy
        dist_to_player = math.sqrt(dist_sq) if dist_sq > 0 else 0.001
        
        # Normalizamos vector hacia jugador
        dir_x = dx / dist_to_player
        dir_y = dy / dist_to_player

        # Si estamos MUY cerca (rango de ataque), dejamos de caminar.
        # Esto elimina el efecto de "rodear como insectos".
        # Simplemente se detienen y atacan.
        attack_range = self.size * 0.6 + 10
        
        move_speed = 0
        if dist_to_player > attack_range:
            move_speed = self.speed * self.speed_variance
        
        # COLISIÓN ENTRE ENEMIGOS (Repulsión)
        push_x = 0
        push_y = 0
        
        if spatial_grid:
            # radius=1 busca solo vecinos inmediatos.
            neighbors = spatial_grid.get_nearby(self.x, self.y, radius=1)
            
            # Solo nos importa si están tocándose físicamente
            collision_radius_sq = (self.radius * 2) ** 2 
            
            for other in neighbors:
                if other is self or not other.is_alive:
                    continue
                
                odx = self.x - other.x
                ody = self.y - other.y
                odist_sq = odx*odx + ody*ody
                
                # Si se superponen...
                if 0 < odist_sq < collision_radius_sq:
                    odist = math.sqrt(odist_sq)
                    
                    # Fuerza de empuje proporcional a qué tan metidos están uno en el otro.
                    # Es una fuerza física dura, no una sugerencia de dirección.
                    overlap = (self.radius * 2) - odist
                    push_strength = overlap * 0.5 # Factor de rigidez
                    
                    # Normalizamos y aplicamos fuerza
                    push_x += (odx / odist) * push_strength
                    push_y += (ody / odist) * push_strength

        # APLICAR MOVIMIENTO FINAL

        # Movimiento voluntario (hacia jugador) + Empuje de otros (física)
        final_dx = (dir_x * move_speed) + push_x
        final_dy = (dir_y * move_speed) + push_y
        
        # Aplicamos al mundo
        self.x += (final_dx + self.knockback_x) * dt
        self.y += (final_dy + self.knockback_y) * dt
        
        # Knockback decay
        if abs(self.knockback_x) > 0.01 or abs(self.knockback_y) > 0.01:
            self.knockback_x *= self.knockback_decay ** dt
            self.knockback_y *= self.knockback_decay ** dt
            if abs(self.knockback_x) < 0.1: self.knockback_x = 0
            if abs(self.knockback_y) < 0.1: self.knockback_y = 0
            
        # Actualizar Rect
        self.rect.centerx = int(self.x)
        self.rect.centery = int(self.y)


    def get_distance_squared_to(self, x, y):
        return (self.x - x)**2 + (self.y - y)**2
    
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
    
    def update(self, particle_system=None, dt=1.0):
        """
        Actualización con sangrado DRÁSTICAMENTE REDUCIDO
        """
        if not self.is_alive:
            return
        
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1 * dt
        if self.damage_flash > 0:
            self.damage_flash -= 1 * dt
        
        # --- MODIFICADO: Lógica de Sangrado Dinámico ---
        if self.bleed_intensity > 0:
            # 1. Decaimiento de la intensidad con el tiempo
            self.bleed_intensity -= self.bleed_decay * dt
            if self.bleed_intensity < 0:
                self.bleed_intensity = 0
            
            # 2. Gestión del goteo
            if self.bleed_drip_cooldown > 0:
                self.bleed_drip_cooldown -= 1 * dt
            
            if self.bleed_drip_cooldown <= 0 and particle_system:
                # La frecuencia del goteo depende de la intensidad
                # Mucha sangre = gotea muy rápido (cooldown bajo)
                # Poca sangre = gotea lento (cooldown alto)
                
                # Fórmula inversa: A más intensidad, menos espera.
                delay = max(2, 20 - (self.bleed_intensity * 0.8))
                
                # Llamamos a la nueva función pasando la intensidad actual
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
        
        # Aumentar intensidad al recibir daño
        self.bleed_intensity += damage 
        if self.bleed_intensity > 40: 
            self.bleed_intensity = 40
            
        if self.health <= 0:
            self.health = 0
            self.is_alive = False
            return True
        return False

    def render(self, screen, camera):
        if not self.is_alive:
            return
        
        screen_rect = camera.apply_rect(self.rect)
        
        render_color = self.color
        if self.damage_flash > 0:
            flash_intensity = int(255 * (self.damage_flash / 10))
            render_color = (min(255, self.color[0] + flash_intensity), 
                          min(255, self.color[1] + flash_intensity), 
                          min(255, self.color[2] + flash_intensity))
        
        pygame.draw.rect(screen, render_color, screen_rect)
        
        border_color = tuple(max(0, c - 50) for c in self.color)
        pygame.draw.rect(screen, border_color, screen_rect, 2) 
        
        center_size = max(2, self.size // 3)
        center_x = screen_rect.centerx - center_size // 2
        center_y = screen_rect.centery - center_size // 2
        pygame.draw.rect(screen, border_color, (center_x, center_y, center_size, center_size))
        
        if self.health < self.max_health:
            bar_width = self.size
            bar_height = 4
            health_width = (self.health / self.max_health) * bar_width
            
            pygame.draw.rect(screen, (60, 0, 0), (screen_rect.x, screen_rect.y - 7, bar_width, bar_height))
            
            health_color = (255, 0, 0) if self.health < self.max_health * 0.3 else (255, 100, 0)
            pygame.draw.rect(screen, health_color, (screen_rect.x, screen_rect.y - 7, health_width, bar_height))

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