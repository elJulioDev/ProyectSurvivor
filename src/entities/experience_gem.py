import pygame
import math
import random

class ExperienceGem:
    TYPES = {
        'blue':   {'xp': 10,  'color': (50, 150, 255), 'radius': 4},
        'green':  {'xp': 25,  'color': (50, 255, 50),  'radius': 5},
        'purple': {'xp': 100, 'color': (200, 50, 255), 'radius': 6},
        'gold':   {'xp': 500, 'color': (255, 215, 0),  'radius': 8}
    }

    def __init__(self, x, y, xp_amount=10):
        self.x = x
        self.y = y

        if xp_amount >= 500:   self.type = 'gold'
        elif xp_amount >= 100: self.type = 'purple'
        elif xp_amount >= 25:  self.type = 'green'
        else:                  self.type = 'blue'

        data = self.TYPES[self.type]
        self.xp_value = xp_amount
        self.color = data['color']
        self.radius = data['radius']

        # Física de salto inicial
        self.z = 10
        self.vz = 4
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)

        # Magnetismo
        self.is_magnetized = False
        self.magnet_speed = 0
        self.acceleration = 0.5

        self.rect = pygame.Rect(x, y, self.radius * 2, self.radius * 2)

    def update(self, player_pos, dt=1.0, magnet_range_mult=1.0, magnet_speed_mult=1.0):
        """
        magnet_range_mult:  multiplica el radio en que la gema empieza a magnetizarse
        magnet_speed_mult:  multiplica la velocidad máxima de acercamiento
        """
        # 1. Animación de caída inicial
        if self.z > 0:
            self.vz -= 0.5 * dt
            self.z += self.vz * dt
            self.x += self.vx * dt
            self.y += self.vy * dt
            if self.z <= 0:
                self.z = 0
                self.vx = 0
                self.vy = 0
            return  # No se puede recoger mientras cae

        # 2. Lógica de magnetismo
        dx = player_pos[0] - self.x
        dy = player_pos[1] - self.y
        dist_sq = dx * dx + dy * dy

        base_magnet_radius = 150
        magnet_radius = base_magnet_radius * magnet_range_mult

        if dist_sq < magnet_radius ** 2:
            self.is_magnetized = True

        if self.is_magnetized:
            self.magnet_speed += self.acceleration * dt
            max_speed = 25 * magnet_speed_mult
            if self.magnet_speed > max_speed:
                self.magnet_speed = max_speed

            angle = math.atan2(dy, dx)
            self.x += math.cos(angle) * self.magnet_speed * dt
            self.y += math.sin(angle) * self.magnet_speed * dt

        # Actualizar rect
        self.rect.x = int(self.x - self.radius)
        self.rect.y = int(self.y - self.radius)

    def render(self, screen, camera):
        if not camera.is_on_screen(self.rect):
            return

        screen_pos = camera.apply_coords(self.x, self.y - self.z)

        if self.z > 0:
            shadow_pos = camera.apply_coords(self.x, self.y)
            pygame.draw.circle(screen, (0, 0, 0, 100),
                               (int(shadow_pos[0]), int(shadow_pos[1])), self.radius)

        pygame.draw.circle(screen, (255, 255, 255),
                           (int(screen_pos[0]), int(screen_pos[1])), self.radius + 1)
        pygame.draw.circle(screen, self.color,
                           (int(screen_pos[0]), int(screen_pos[1])), self.radius)