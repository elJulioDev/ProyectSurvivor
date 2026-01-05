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

    def update(self, target_list, projectile_list):
        if self.current_cooldown > 0:
            self.current_cooldown -= 1
            return

        if self.activate(target_list, projectile_list):
            self.current_cooldown = self.cooldown

    def activate(self, target_list, projectile_list):
        return False

class WandWeapon(Weapon):
    """Dispara al enemigo más cercano"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=45, damage=25)
        
    def activate(self, target_list, projectile_list):
        if not target_list:
            return False
            
        # Buscar enemigo más cercano
        closest_enemy = None
        min_dist = float('inf')
        
        px, py = self.owner.x, self.owner.y
        
        for enemy in target_list:
            dist = math.hypot(enemy.x - px, enemy.y - py)
            if dist < min_dist:
                min_dist = dist
                closest_enemy = enemy
        
        if closest_enemy:
            # Calcular ángulo
            angle = math.atan2(closest_enemy.y - py, closest_enemy.x - px)
            
            # Crear proyectil
            p = Projectile(px, py, angle, speed=7, damage=self.damage, penetration=1)
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
        # Dispara hacia donde mira el jugador (o hacia el mouse si prefieres)
        mouse_pos = pygame.mouse.get_pos()
        base_angle = math.atan2(mouse_pos[1] - self.owner.y, mouse_pos[0] - self.owner.x)
        
        spread = 0.5 # 30 grados aprox
        
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
            p.color = (255, 100, 0) # Naranja
            projectile_list.append(p)
        return True

class OrbitalWeapon(Weapon):
    """Orbe que gira alrededor del jugador (Escudo)"""
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=5) # Cooldown 0 porque siempre está activo
        self.angle = 0
        self.radius = 70
        self.speed = 0.05
        # Este arma gestiona su propio "proyectil" interno o hitbox
        self.orbit_rect = pygame.Rect(0, 0, 20, 20)
        
    def update(self, target_list, particle_system=None):
        # Actualizar posición
        self.angle += self.speed
        cx = self.owner.x + math.cos(self.angle) * self.radius
        cy = self.owner.y + math.sin(self.angle) * self.radius
        
        self.orbit_rect.center = (int(cx), int(cy))
        
        # Colisiones
        for enemy in target_list:
            if enemy.is_alive and self.orbit_rect.colliderect(enemy.rect):
                if enemy.take_damage(1): # Daño pequeño pero constante
                     if particle_system:
                         particle_system.create_impact_particles(enemy.x, enemy.y, (100, 100, 255), 2)

    def render(self, screen):
        pygame.draw.circle(screen, (100, 100, 255), self.orbit_rect.center, 10)
        pygame.draw.line(screen, (50, 50, 150), (self.owner.x, self.owner.y), self.orbit_rect.center, 2)


class LaserWeapon(Weapon):
    """
    Láser estilo Metal Slug:
    - Dispara en la dirección que apunta el jugador
    - Atraviesa TODOS los enemigos en la línea
    - Daño por 'tick' (intervalo)
    """
    def __init__(self, owner):
        # Cooldown bajo para que haga daño rápido, pero no cada frame (sería demasiado op)
        super().__init__(owner, cooldown=0, damage=4) 
        self.max_range = 800  # Largo del láser
        self.hit_interval = 1  # Frames entre golpes al mismo enemigo
        self.enemy_hit_timers = {}  # Diccionario para controlar el daño por enemigo
        
        # Audio (opcional, placeholder)
        self.firing = False

    def update(self, target_list, particle_system=None):
        # Limpiar temporizadores de enemigos muertos o fuera de rango
        current_time = pygame.time.get_ticks()
        
        # Calcular inicio y fin del láser basado en el ángulo del jugador
        start_pos = (self.owner.x, self.owner.y)
        end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        end_pos = (end_x, end_y)
        
        # Detectar colisiones
        for enemy in target_list:
            if not enemy.is_alive:
                continue
                
            # clipline devuelve los puntos donde la línea entra y sale del rect
            # si devuelve algo, es que el láser tocó al enemigo
            clip = enemy.rect.clipline(start_pos, end_pos)
            
            if clip:
                # Verificar si podemos dañar a este enemigo (Tick rate)
                enemy_id = id(enemy)
                if enemy_id not in self.enemy_hit_timers:
                    self.enemy_hit_timers[enemy_id] = 0
                
                if self.enemy_hit_timers[enemy_id] <= 0:
                    # APLICAR DAÑO
                    enemy.take_damage(self.damage)
                    self.enemy_hit_timers[enemy_id] = self.hit_interval
                    
                    # Efectos visuales en el punto de impacto
                    # clip[0] es el primer punto de contacto
                    if particle_system:
                        particle_system.create_impact_particles(clip[0][0], clip[0][1], (200, 255, 255), count=3)
                else:
                    self.enemy_hit_timers[enemy_id] -= 1

    def render(self, screen):
        # Calcular coordenadas (igual que en update)
        start_pos = (self.owner.x, self.owner.y)
        end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
        end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
        end_pos = (end_x, end_y)

        # Dibujar el láser con efecto de "brillo" (varias líneas de diferente grosor)
        
        # 1. Brillo exterior (Transparente/Difuso)
        # Para hacer transparencia en líneas necesitamos una superficie auxiliar o usar colores con alpha simulado
        # Pygame draw.line no soporta alpha directamente bien, así que usaremos colores oscuros para el borde
        pygame.draw.line(screen, (0, 100, 100), start_pos, end_pos, 15) # Cyan oscuro grueso
        
        # 2. Cuerpo del láser (Cyan brillante)
        pygame.draw.line(screen, (0, 255, 255), start_pos, end_pos, 7)
        
        # 3. Núcleo de energía (Blanco)
        pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, 3)