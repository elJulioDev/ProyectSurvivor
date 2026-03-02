"""
Jugador optimizado con DeltaTime + Sistema de Dash Profesional
Stats expandidos para el nuevo sistema de mejoras.

NUEVOS STATS:
  aura_damage      → DPS del Aura de Espinas (0 = inactiva)
  aura_radius      → Radio del aura en píxeles (base 80)
  aura_knockback   → Fuerza de retroceso continuo del Aura (0 = sin empuje)
  ninja_dash       → Si True, el dash mata enemigos al atravesarlos
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
        self.passive_weapons = []
        self.weapons = [PistolWeapon(self)]
        self.current_weapon_index = 0
        self.unlocked_weapons = {'PistolWeapon'}

        hitbox_size = self.size - 4
        self.rect = pygame.Rect(
            self.x - hitbox_size // 2,
            self.y - hitbox_size // 2,
            hitbox_size,
            hitbox_size
        )

        # SISTEMA DE DASH
        self.dash_unlocked = False
        self.dash_active = False
        self.dash_timer = 0
        self.dash_duration = 12
        self.dash_cooldown = 45
        self.dash_cooldown_timer = 0
        self.dash_speed = 24
        self.dash_vector = (0, 0)
        self.dash_buffer_timer = 0
        self.dash_buffer_duration = 9
        self.ghost_positions = []
        self.max_ghosts = 5

        self.last_shot_time = 0

        # STATS DE MEJORAS — Globales de armas
        self.global_damage_mult    = 1.0
        self.global_cooldown_mult  = 1.0
        self.projectile_speed_mult = 1.0
        self.projectile_size_mult  = 1.0
        self.extra_penetration     = 0
        self.knockback_mult        = 1.0

        # STATS DE MEJORAS — Supervivencia
        self.health_regen      = 0.0
        self.damage_reduction  = 0.0
        self.lifesteal         = 5
        self.lifesteal_chance  = 0.0
        self.emergency_regen   = 0.0
        self.invulnerable_mult = 1.0

        # STATS DE MEJORAS — Aura de daño
        self.aura_damage    = 0.0       # DPS que inflige a enemigos cercanos
        self.aura_radius    = 80.0      # Radio del aura en píxeles
        self.aura_knockback = 0.0       # Fuerza de empuje continuo del Aura (0 = off)

        # STATS DE MEJORAS — Dash Ninja
        self.ninja_dash = False

        # STATS DE MEJORAS — XP / Gemas
        self.xp_mult           = 1.0
        self.magnet_range_mult = 1.0
        self.magnet_speed_mult = 1.0
        self.xp_on_kill_bonus  = 0

        # SISTEMA DE NIVEL
        self.level = 1
        self.experience = 0
        self.experience_next_level = 50
        self.pending_level_ups = 0

        self.upgrade_counts: dict = {}

    def gain_experience(self, amount):
        if not self.is_alive:
            return False
        modified = max(1, int(amount * self.xp_mult))
        self.experience += modified
        leveled_up = False
        while self.experience >= self.experience_next_level:
            self.experience -= self.experience_next_level
            self.level += 1
            self.pending_level_ups += 1
            self.experience_next_level = int(self.experience_next_level * 1.2)
            leveled_up = True
        return leveled_up

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1 and len(self.weapons) > 0:
                self.current_weapon_index = 0
            elif event.key == pygame.K_2 and len(self.weapons) > 1:
                self.current_weapon_index = 1
            elif event.key == pygame.K_3 and len(self.weapons) > 2:
                self.current_weapon_index = 2
            elif event.key == pygame.K_4 and len(self.weapons) > 3:
                self.current_weapon_index = 3
            elif event.key == pygame.K_5 and len(self.weapons) > 4:
                self.current_weapon_index = 4
            elif event.key == pygame.K_6 and len(self.weapons) > 5:
                self.current_weapon_index = 5
            elif event.key == pygame.K_7 and len(self.weapons) > 6:
                self.current_weapon_index = 6
            elif event.key == pygame.K_h:
                self.heal(10)
                self.damage_flash = 5
            elif event.key in [pygame.K_LCTRL, pygame.K_RCTRL]:
                self._attempt_dash()

            elif event.key == pygame.K_F1:
                xp_faltante = self.experience_next_level - self.experience
                self.gain_experience(xp_faltante)
                print(f"[DEBUG] Subida de nivel forzada. Nivel actual: {self.level}")

            elif event.key == pygame.K_F2:
                print("\n=== [DEBUG] STACKS DE MEJORAS ACTUALES ===")
                if not self.upgrade_counts:
                    print("  Ninguna mejora elegida todavia.")
                else:
                    for key, count in self.upgrade_counts.items():
                        print(f"  > {key}: {count} stack(s)")
                print("==========================================\n")

    def _attempt_dash(self):
        if not self.dash_unlocked:
            return
        if self.dash_cooldown_timer > 0:
            self.dash_buffer_timer = self.dash_buffer_duration
            return
        self._execute_dash()

    def _execute_dash(self):
        keys = pygame.key.get_pressed()
        input_x = 0
        input_y = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    input_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  input_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  input_x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: input_x += 1

        if input_x != 0 or input_y != 0:
            mag = math.sqrt(input_x * input_x + input_y * input_y)
            dash_dx = input_x / mag
            dash_dy = input_y / mag
        else:
            dash_dx = math.cos(self.angle)
            dash_dy = math.sin(self.angle)

        self.dash_active = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown_timer = self.dash_cooldown
        self.dash_vector = (dash_dx, dash_dy)
        self.dash_buffer_timer = 0
        self.ghost_positions = []

    def _execute_dash_with_vector(self, dx: float, dy: float) -> None:
        if not self.dash_unlocked or self.dash_cooldown_timer > 0:
            return

        if math.hypot(dx, dy) > 0.01:
            mag = math.hypot(dx, dy)
            dash_dx, dash_dy = dx / mag, dy / mag
        else:
            dash_dx = math.cos(self.angle)
            dash_dy = math.sin(self.angle)

        self.dash_active = True
        self.dash_timer = self.dash_duration
        self.dash_cooldown_timer = self.dash_cooldown
        self.dash_vector = (dash_dx, dash_dy)
        self.dash_buffer_timer = 0
        self.ghost_positions = []

    def handle_input(self, keys, dt=1.0):
        if self.dash_active:
            return
        input_x = 0
        input_y = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    input_y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  input_y += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  input_x -= 1
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

    def handle_input_mobile(self, dx: float, dy: float, dt: float = 1.0) -> None:
        if self.dash_active:
            return

        self.vel_x += dx * self.accel * dt
        self.vel_y += dy * self.accel * dt

        friction_factor = self.friction ** dt
        self.vel_x *= friction_factor
        self.vel_y *= friction_factor

        speed_sq     = self.vel_x * self.vel_x + self.vel_y * self.vel_y
        max_speed_sq = self.max_speed * self.max_speed
        if speed_sq > max_speed_sq:
            scale     = self.max_speed / math.sqrt(speed_sq)
            self.vel_x *= scale
            self.vel_y *= scale

        if abs(self.vel_x) < 0.1: self.vel_x = 0
        if abs(self.vel_y) < 0.1: self.vel_y = 0

    def update_rotation(self, mouse_pos, camera_offset=(0, 0)):
        screen_player_x = self.x + camera_offset[0]
        screen_player_y = self.y + camera_offset[1]
        dx = mouse_pos[0] - screen_player_x
        dy = mouse_pos[1] - screen_player_y
        self.angle = math.atan2(dy, dx)

    def add_weapon(self, weapon_class, projectile_pool):
        from entities.weapon import (ShotgunWeapon, LaserWeapon, AssaultRifleWeapon,
                                     SniperWeapon, NovaWeapon, OrbitalWeapon,
                                     BoomerangWeapon)
        weapon_map = {
            'ShotgunWeapon':       ShotgunWeapon,
            'AssaultRifleWeapon':  AssaultRifleWeapon,
            'LaserWeapon':         LaserWeapon,
            'SniperWeapon':        SniperWeapon,
            'NovaWeapon':          NovaWeapon,
            'OrbitalWeapon':       OrbitalWeapon,
            'BoomerangWeapon':     BoomerangWeapon,
        }
        if weapon_class in weapon_map and weapon_class not in self.unlocked_weapons:
            new_weapon = weapon_map[weapon_class](self)
            new_weapon.set_projectile_pool(projectile_pool)
            
            # Separar armas pasivas de armas activables
            if weapon_class in ['NovaWeapon', 'OrbitalWeapon', 'BoomerangWeapon']:
                self.passive_weapons.append(new_weapon)
                print(f"✅ Habilidad Pasiva desbloqueada: {weapon_class}")
            else:
                self.weapons.append(new_weapon)
                print(f"✅ Arma desbloqueada: {weapon_class}")
                
            self.unlocked_weapons.add(weapon_class)

    def update(self, dt=1.0):
        if not self.is_alive:
            return

        if self.health_regen > 0 and self.health < self.max_health:
            self.health += self.health_regen * dt / 60.0
            self.health = min(self.health, self.max_health)

        if self.emergency_regen > 0 and self.health < self.max_health * 0.25:
            self.health += self.emergency_regen * dt / 60.0
            self.health = min(self.health, self.max_health)

        if self.dash_cooldown_timer > 0:
            self.dash_cooldown_timer -= 1 * dt
            if self.dash_cooldown_timer <= 0 and self.dash_buffer_timer > 0:
                self._execute_dash()

        if self.dash_buffer_timer > 0:
            self.dash_buffer_timer -= 1 * dt

        if self.dash_active:
            if len(self.ghost_positions) < self.max_ghosts:
                self.ghost_positions.append((self.x, self.y, self.angle))
            else:
                self.ghost_positions.pop(0)
                self.ghost_positions.append((self.x, self.y, self.angle))

            self.x += self.dash_vector[0] * self.dash_speed * dt
            self.y += self.dash_vector[1] * self.dash_speed * dt
            self.vel_x = self.dash_vector[0] * self.max_speed * 0.8
            self.vel_y = self.dash_vector[1] * self.max_speed * 0.8

            self.dash_timer -= 1 * dt
            if self.dash_timer <= 0:
                self.dash_active = False
                self.ghost_positions = []
        else:
            self.x += self.vel_x * dt
            self.y += self.vel_y * dt

        if self.x < self.size:
            self.x = self.size;  self.vel_x = 0
        elif self.x > WORLD_WIDTH - self.size:
            self.x = WORLD_WIDTH - self.size;  self.vel_x = 0
        if self.y < self.size:
            self.y = self.size;  self.vel_y = 0
        elif self.y > WORLD_HEIGHT - self.size:
            self.y = WORLD_HEIGHT - self.size;  self.vel_y = 0

        hitbox_size = self.size - 4
        self.rect.x = self.x - hitbox_size // 2
        self.rect.y = self.y - hitbox_size // 2

        if self.damage_flash > 0:      self.damage_flash -= 1 * dt
        if self.invulnerable_frames > 0: self.invulnerable_frames -= 1 * dt

    def take_damage(self, damage):
        if not self.is_alive or self.invulnerable_frames > 0 or self.dash_active:
            return
        reduced = damage * max(0.0, 1.0 - self.damage_reduction)
        self.health -= reduced
        self.damage_flash = 15
        self.invulnerable_frames = 60 * self.invulnerable_mult
        if self.health <= 0:
            self.health = 0
            self.is_alive = False

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def attack(self, camera=None):
        if not self.is_alive or self.dash_active:
            return False
        if self.current_weapon_index >= len(self.weapons):
            self.current_weapon_index = 0
        if not self.weapons:
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

        if self.dash_active and len(self.ghost_positions) > 0:
            for i, (gx, gy, gangle) in enumerate(self.ghost_positions):
                alpha = int(180 * (i / max(1, len(self.ghost_positions))))
                ghost_screen = camera.apply_coords(gx, gy)
                gsx, gsy = int(ghost_screen[0]), int(ghost_screen[1])

                if self.ninja_dash:
                    ghost_color = (100, 0, 180, alpha)
                else:
                    ghost_color = (255, 255, 255, alpha)

                ghost_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
                ghost_surf.fill(ghost_color)
                screen.blit(ghost_surf, (gsx - self.size//2, gsy - self.size//2))
                if alpha > 50:
                    end_x = gsx + math.cos(gangle) * (self.size * 1.2)
                    end_y = gsy + math.sin(gangle) * (self.size * 1.2)
                    line_color = ghost_color[:3] if len(ghost_color) == 4 else ghost_color
                    pygame.draw.line(screen, line_color,
                                     (gsx, gsy), (end_x, end_y), 2)

        render_color = self.color
        if self.damage_flash > 0:
            flash = int(255 * (self.damage_flash / 15))
            render_color = (255, max(0, 255 - flash), max(0, 255 - flash))

        if self.ninja_dash and self.dash_unlocked:
            pygame.draw.rect(screen, (160, 0, 255),
                             (screen_x - self.size//2 - 2, screen_y - self.size//2 - 2,
                              self.size + 4, self.size + 4))

        pygame.draw.rect(screen, render_color,
                         (screen_x - self.size//2, screen_y - self.size//2,
                          self.size, self.size))

        end_x = screen_x + math.cos(self.angle) * (self.size * 1.2)
        end_y = screen_y + math.sin(self.angle) * (self.size * 1.2)
        pygame.draw.line(screen, render_color, (screen_x, screen_y),
                         (end_x, end_y), 3)

    def get_position(self):
        return (self.x, self.y)