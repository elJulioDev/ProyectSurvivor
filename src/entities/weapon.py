"""
Sistema de armas optimizado con Object Pooling y Grid Espacial
"""
import math
import random
import pygame

class Weapon:
    def __init__(self, owner, cooldown=60, damage=10):
        self.owner = owner
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.damage = damage
        self.level = 1
        self.projectile_pool = None  # Se asigna desde GameplayScene

    def set_projectile_pool(self, pool):
        """Asigna el pool de proyectiles"""
        self.projectile_pool = pool

    def update(self, target_list, projectile_list=None, particle_system=None, dt=1.0):
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * dt
            return 0

        if self.activate(target_list, projectile_list):
            self.current_cooldown = self.cooldown
        
        return 0 

    def activate(self, target_list, projectile_list):
        return False

class WandWeapon(Weapon):
    """Dispara al enemigo más cercano usando distancia al cuadrado"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=35, damage=30)
        
    def activate(self, target_list, projectile_list):
        if not target_list or not self.projectile_pool:
            return False
        
        # OPTIMIZACIÓN: Buscar enemigo más cercano con distancia al cuadrado
        closest_enemy = None
        min_dist_sq = float('inf')
        
        px, py = self.owner.x, self.owner.y
        
        for enemy in target_list:
            dx = enemy.x - px
            dy = enemy.y - py
            dist_sq = dx*dx + dy*dy  # Sin sqrt!
            
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                closest_enemy = enemy
        
        if closest_enemy:
            angle = math.atan2(closest_enemy.y - py, closest_enemy.x - px)
            
            # USAR POOL en lugar de crear instancia nueva
            p = self.projectile_pool.get(px, py, angle, speed=9, damage=self.damage, penetration=1)
            p.color = (0, 255, 255)
            return True
        return False

class ShotgunWeapon(Weapon):
    """Dispara múltiples proyectiles en abanico"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=90, damage=15)
        self.pellets = 5
        
    def activate(self, target_list, projectile_list):
        if not self.projectile_pool:
            return False
        
        base_angle = self.owner.angle
        spread = 0.5
        
        for i in range(self.pellets):
            offset = (i - self.pellets // 2) * (spread / self.pellets)
            
            # USAR POOL
            p = self.projectile_pool.get(
                self.owner.x, self.owner.y, 
                base_angle + offset, 
                speed=12, 
                damage=self.damage, 
                penetration=2, 
                lifetime=40, 
                image_type='square'
            )
            p.color = (255, 100, 0)
        return True

class OrbitalWeapon(Weapon):
    """Orbe que gira alrededor del jugador con colisiones optimizadas"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=5)
        self.angle = 0
        self.radius = 70
        self.speed = 0.05
        self.orbit_rect = pygame.Rect(0, 0, 20, 20)
        
    def update(self, target_list, projectile_list=None, particle_system=None, dt=1.0):
        self.angle += self.speed * dt
        cx = self.owner.x + math.cos(self.angle) * self.radius
        cy = self.owner.y + math.sin(self.angle) * self.radius
        self.orbit_rect.center = (int(cx), int(cy))
        
        points_gained = 0
        
        # OPTIMIZACIÓN: Solo verificar enemigos que estén cerca del orbe
        for enemy in target_list:
            if not enemy.is_alive:
                continue
            
            # Verificar distancia al cuadrado antes de rect collision
            dx = enemy.x - cx
            dy = enemy.y - cy
            dist_sq = dx*dx + dy*dy
            
            # Solo hacer rect collision si está cerca (radio + margen)
            if dist_sq < (self.radius + enemy.size) ** 2:
                if self.orbit_rect.colliderect(enemy.rect):
                    if enemy.take_damage(1):
                        points_gained += enemy.points
                        if particle_system:
                            particle_system.create_viscera_explosion(enemy.x, enemy.y)
                    elif particle_system and random.random() < 0.2:
                        angle_to_enemy = math.atan2(enemy.y - self.owner.y, enemy.x - self.owner.x)
                        dir_x = math.cos(angle_to_enemy)
                        dir_y = math.sin(angle_to_enemy)
                        
                        particle_system.create_blood_splatter(
                            enemy.x, enemy.y, 
                            direction_vector=(dir_x, dir_y),
                            count=4
                        )
                    
        return points_gained

    def render(self, screen, camera):
        center_pos = camera.apply_coords(self.orbit_rect.centerx, self.orbit_rect.centery)
        owner_pos = camera.apply_coords(self.owner.x, self.owner.y)
        
        pygame.draw.circle(screen, (100, 100, 255), center_pos, 10)
        pygame.draw.line(screen, (50, 50, 150), owner_pos, center_pos, 2)

class LaserWeapon(Weapon):
    """Láser optimizado con verificación de distancia"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=4) 
        self.max_range = 800
        self.hit_interval = 1
        self.enemy_hit_timers = {}
        
    def update(self, target_list, projectile_list=None, particle_system=None, dt=1.0):
        start_pos = (self.owner.x, self.owner.y)
        end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        end_pos = (end_x, end_y)
        
        points_gained = 0
        
        # Decrementar timers
        for enemy_id in list(self.enemy_hit_timers.keys()):
            self.enemy_hit_timers[enemy_id] -= 1 * dt
            if self.enemy_hit_timers[enemy_id] <= 0:
                del self.enemy_hit_timers[enemy_id]
        
        for enemy in target_list:
            if not enemy.is_alive:
                continue
            
            # OPTIMIZACIÓN: Verificar si está en rango con distancia al cuadrado primero
            dx = enemy.x - self.owner.x
            dy = enemy.y - self.owner.y
            dist_sq = dx*dx + dy*dy
            
            if dist_sq > self.max_range * self.max_range:
                continue  # Muy lejos, skip
            
            # Solo hacer clipline si está en rango
            clip = enemy.rect.clipline(start_pos, end_pos)
            if clip:
                enemy_id = id(enemy)
                
                if enemy_id not in self.enemy_hit_timers or self.enemy_hit_timers[enemy_id] <= 0:
                    if enemy.take_damage(self.damage):
                        points_gained += enemy.points
                        if particle_system:
                             particle_system.create_viscera_explosion(enemy.x, enemy.y)
                    else:
                        dir_x = math.cos(self.owner.angle)
                        dir_y = math.sin(self.owner.angle)
                        if particle_system:
                            particle_system.create_blood_splatter(
                                clip[0][0], clip[0][1], 
                                direction_vector=(dir_x, dir_y),
                                count=3
                            )
                    
                    self.enemy_hit_timers[enemy_id] = self.hit_interval
        
        return points_gained

    def render(self, screen, camera):
        world_start_x = self.owner.x
        world_start_y = self.owner.y
        world_end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        world_end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        
        start_pos = camera.apply_coords(world_start_x, world_start_y)
        end_pos = camera.apply_coords(world_end_x, world_end_y)
        
        pygame.draw.line(screen, (0, 100, 100), start_pos, end_pos, 15)
        pygame.draw.line(screen, (0, 255, 255), start_pos, end_pos, 7)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)