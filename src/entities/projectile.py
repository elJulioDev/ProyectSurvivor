"""
Módulo de proyectiles — jugador + enemigos
"""
import pygame
import math
from settings import YELLOW, WORLD_WIDTH, WORLD_HEIGHT


class Projectile:
    __slots__ = (
        'x', 'y', 'angle', 'speed', 'size', 'color', 'damage',
        'penetration', 'lifetime', 'is_alive', 'image_type',
        'hit_enemies', 'vel_x', 'vel_y', 'rect', 'hitbox_size'
    )

    def __init__(self, x, y, angle, speed=10, damage=25, penetration=1,
                 lifetime=120, image_type='circle'):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.size = 6
        self.hitbox_size = 20
        self.color = YELLOW
        self.damage = damage
        self.penetration = penetration
        self.lifetime = lifetime
        self.is_alive = True
        self.image_type = image_type
        self.hit_enemies = []
        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed

        self.rect = pygame.Rect(
            int(self.x - self.hitbox_size // 2),
            int(self.y - self.hitbox_size // 2),
            self.hitbox_size,
            self.hitbox_size
        )

    def update(self, dt=1.0):
        if not self.is_alive:
            return

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

        self.rect.x = int(self.x - self.hitbox_size // 2)
        self.rect.y = int(self.y - self.hitbox_size // 2)

        self.lifetime -= 1 * dt
        if self.lifetime <= 0:
            self.is_alive = False

        if (self.x < -50 or self.x > WORLD_WIDTH + 50 or
                self.y < -50 or self.y > WORLD_HEIGHT + 50):
            self.is_alive = False

    def check_collision_grid(self, spatial_grid):
        if not self.is_alive:
            return None

        nearby_enemies = spatial_grid.get_nearby(self.x, self.y, radius=1)

        for enemy in nearby_enemies:
            if enemy.is_alive and enemy not in self.hit_enemies:
                if self.rect.colliderect(enemy.rect):
                    self.hit_enemies.append(enemy)
                    self.penetration -= 1
                    if self.penetration <= 0:
                        self.is_alive = False
                    return enemy
        return None

    def render(self, screen, camera):
        if not self.is_alive:
            return

        screen_pos = camera.apply_coords(self.x, self.y)
        try:
            center = (int(screen_pos[0]), int(screen_pos[1]))
        except Exception:
            return

        if self.image_type == 'circle':
            pygame.draw.circle(screen, self.color, center, self.size)
            pygame.draw.circle(screen, (255, 255, 200), center,
                               max(1, self.size // 2))
        elif self.image_type == 'square':
            rect_surf = pygame.Surface((self.size * 2, self.size * 2),
                                       pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, self.color,
                             (0, 0, self.size * 2, self.size * 2))
            rotated_surf = pygame.transform.rotate(rect_surf,
                                                    self.lifetime * 10)
            screen.blit(rotated_surf,
                        (screen_pos[0] - rotated_surf.get_width() // 2,
                         screen_pos[1] - rotated_surf.get_height() // 2))

class EnemyProjectile:
    """
    Proyectil disparado por un enemigo que daña al jugador.
    proj_type: 'acid' | 'rock'
    """
    __slots__ = (
        'x', 'y', 'vel_x', 'vel_y', 'speed', 'damage',
        'lifetime', 'is_alive', 'color', 'radius', 'proj_type', 'rect'
    )

    def __init__(self, x, y, angle, speed, damage, lifetime,
                 color, radius, proj_type='acid'):
        self.x = x
        self.y = y
        self.speed = speed
        self.damage = damage
        self.lifetime = lifetime
        self.is_alive = True
        self.color = color
        self.radius = radius
        self.proj_type = proj_type

        self.vel_x = math.cos(angle) * speed
        self.vel_y = math.sin(angle) * speed

        hs = radius + 4
        self.rect = pygame.Rect(
            int(x - hs), int(y - hs), hs * 2, hs * 2
        )

    def update(self, dt=1.0):
        if not self.is_alive:
            return

        self.x += self.vel_x * dt
        self.y += self.vel_y * dt

        hs = self.radius + 4
        self.rect.x = int(self.x - hs)
        self.rect.y = int(self.y - hs)

        self.lifetime -= 1 * dt
        if self.lifetime <= 0:
            self.is_alive = False

        if (self.x < -100 or self.x > WORLD_WIDTH + 100 or
                self.y < -100 or self.y > WORLD_HEIGHT + 100):
            self.is_alive = False

    def check_player_collision(self, player):
        if not self.is_alive:
            return False
        if self.rect.colliderect(player.rect):
            player.take_damage(self.damage)
            self.is_alive = False
            return True
        return False

    def render(self, screen, camera):
        if not self.is_alive:
            return

        screen_pos = camera.apply_coords(self.x, self.y)
        cx = int(screen_pos[0])
        cy = int(screen_pos[1])

        if self.proj_type == 'acid':
            # Círculo verde pulsante
            progress = max(0.0, self.lifetime / 175)
            alpha_val = int(200 * progress + 55)
            r = self.radius

            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (60, 230, 20, min(120, alpha_val // 2)),
                               (r * 2, r * 2), r * 2)
            screen.blit(glow, (cx - r * 2, cy - r * 2))

            pygame.draw.circle(screen, self.color, (cx, cy), r)
            pygame.draw.circle(screen, (150, 255, 80), (cx, cy), max(2, r // 2))

        elif self.proj_type == 'rock':
            r = self.radius
            # Cuadrado rotado (roca)
            angle_deg = (self.lifetime * 6) % 360
            rock_surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.rect(rock_surf, self.color,
                             (2, 2, r * 2, r * 2))
            pygame.draw.rect(rock_surf, (200, 180, 140),
                             (2, 2, r * 2, r * 2), 2)
            rotated = pygame.transform.rotate(rock_surf, angle_deg)
            screen.blit(rotated,
                        (cx - rotated.get_width() // 2,
                         cy - rotated.get_height() // 2))