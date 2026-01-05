"""
Sistema de armas tipo Vampire Survivors
"""
import math
import random
import pygame
from entities.projectile import Projectile

class Weapon:
    def __init__(self, owner, cooldown=60, damage=10):
        self.owner = owner
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.damage = damage
        self.level = 1

    def update(self, target_list, projectile_list=None, particle_system=None):
        if self.current_cooldown > 0:
            self.current_cooldown -= 1
            return 0  # Retorna 0 puntos

        if self.activate(target_list, projectile_list):
            self.current_cooldown = self.cooldown
        
        return 0 

    def activate(self, target_list, projectile_list):
        return False

class WandWeapon(Weapon):
    """Dispara al enemigo más cercano (Pistola)"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=35, damage=30)
        
    def activate(self, target_list, projectile_list):
        if not target_list:
            return False
        
        # Buscar enemigo más cercano
        closest_enemy = None
        min_dist = float('inf')
        
        px, py = self.owner.x, self.owner.y
        
        for enemy in target_list:
            # Ambos están en coordenadas de mundo, así que math.hypot funciona bien
            dist = math.hypot(enemy.x - px, enemy.y - py)
            if dist < min_dist:
                min_dist = dist
                closest_enemy = enemy
        
        if closest_enemy:
            angle = math.atan2(closest_enemy.y - py, closest_enemy.x - px)
            p = Projectile(px, py, angle, speed=9, damage=self.damage, penetration=1)
            p.color = (0, 255, 255) # Cyan
            projectile_list.append(p)
            return True
        return False

class ShotgunWeapon(Weapon):
    """Dispara múltiples proyectiles en abanico"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=90, damage=15)
        self.pellets = 5
        
    def activate(self, target_list, projectile_list):
        # Usamos self.owner.angle, que el Jugador ya calculó correctamente usando la cámara.
        base_angle = self.owner.angle
        
        spread = 0.5 # ~30 grados
        
        for i in range(self.pellets):
            offset = (i - self.pellets // 2) * (spread / self.pellets)
            p = Projectile(
                self.owner.x, self.owner.y, 
                base_angle + offset, 
                speed=12, 
                damage=self.damage, 
                penetration=2, 
                lifetime=40, 
                image_type='square'
            )
            p.color = (255, 100, 0)
            projectile_list.append(p)
        return True

class OrbitalWeapon(Weapon):
    """Orbe que gira alrededor del jugador (Escudo)"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=5)
        self.angle = 0
        self.radius = 70
        self.speed = 0.05
        self.orbit_rect = pygame.Rect(0, 0, 20, 20)
        
    def update(self, target_list, projectile_list=None, particle_system=None):
        self.angle += self.speed
        cx = self.owner.x + math.cos(self.angle) * self.radius
        cy = self.owner.y + math.sin(self.angle) * self.radius
        self.orbit_rect.center = (int(cx), int(cy))
        
        points_gained = 0
        
        for enemy in target_list:
            if enemy.is_alive and self.orbit_rect.colliderect(enemy.rect):
                if enemy.take_damage(1):
                    points_gained += enemy.points
                    if particle_system:
                        # Muerte: Explosión de vísceras
                        particle_system.create_viscera_explosion(enemy.x, enemy.y)
                elif particle_system and random.random() < 0.2:
                    # Daño: Sangrado direccional (hacia afuera del jugador)
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
        # Aplicar cámara para renderizar en el lugar correcto de la pantalla
        center_pos = camera.apply_coords(self.orbit_rect.centerx, self.orbit_rect.centery)
        owner_pos = camera.apply_coords(self.owner.x, self.owner.y)
        
        pygame.draw.circle(screen, (100, 100, 255), center_pos, 10)
        pygame.draw.line(screen, (50, 50, 150), owner_pos, center_pos, 2)

class LaserWeapon(Weapon):
    """Láser estilo Metal Slug"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=4) 
        self.max_range = 800
        self.hit_interval = 1
        self.enemy_hit_timers = {}
        
    def update(self, target_list, projectile_list=None, particle_system=None):
        # Lógica en coordenadas de MUNDO (correcto)
        start_pos = (self.owner.x, self.owner.y)
        end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        end_pos = (end_x, end_y)
        
        points_gained = 0
        
        for enemy in target_list:
            if not enemy.is_alive: continue
            
            # clipline funciona bien porque enemy.rect y el láser están ambos en coords de mundo
            clip = enemy.rect.clipline(start_pos, end_pos)
            if clip:
                enemy_id = id(enemy)
                if enemy_id not in self.enemy_hit_timers: self.enemy_hit_timers[enemy_id] = 0
                
                if self.enemy_hit_timers[enemy_id] <= 0:
                    if enemy.take_damage(self.damage):
                        points_gained += enemy.points
                        if particle_system:
                             # Muerte: Vísceras
                             particle_system.create_viscera_explosion(enemy.x, enemy.y)
                    else:
                        # DAÑO LÁSER: Salpicadura pequeña en el punto de impacto
                        # Usamos la dirección del láser para el chorro de sangre
                        dir_x = math.cos(self.owner.angle)
                        dir_y = math.sin(self.owner.angle)
                        if particle_system:
                            particle_system.create_blood_splatter(
                                clip[0][0], clip[0][1], 
                                direction_vector=(dir_x, dir_y),
                                count=3
                            )
                    
                    self.enemy_hit_timers[enemy_id] = self.hit_interval
                else:
                    self.enemy_hit_timers[enemy_id] -= 1
        
        return points_gained

    def render(self, screen, camera):
        # Calculamos inicio y fin en coordenadas de MUNDO
        world_start_x = self.owner.x
        world_start_y = self.owner.y
        world_end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        world_end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        
        # Convertimos a coordenadas de PANTALLA
        start_pos = camera.apply_coords(world_start_x, world_start_y)
        end_pos = camera.apply_coords(world_end_x, world_end_y)
        
        # Dibujamos usando las coordenadas de pantalla
        pygame.draw.line(screen, (0, 100, 100), start_pos, end_pos, 15)
        pygame.draw.line(screen, (0, 255, 255), start_pos, end_pos, 7)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)