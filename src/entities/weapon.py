"""
Sistema de armas con soporte completo para multiplicadores del jugador:
  - global_damage_mult      → afecta a TODAS las armas (incluyendo láser)
  - global_cooldown_mult    → velocidad de disparo global
  - projectile_speed_mult   → velocidad de proyectiles
  - projectile_size_mult    → tamaño de hitbox de proyectiles
  - extra_penetration       → penetración adicional

NUEVAS ARMAS:
  - SniperWeapon: Rifle de Caza — máxima penetración (8 base), daño masivo (110),
    disparo lento (100 frames). Proyectil fucsia ultrarrápido (38px/frame).
"""
import math, random, pygame, os
from utils.paths import resource_path

def load_sound(filename):
    path = resource_path(os.path.join("assets", "sounds", filename))
    if not os.path.exists(path):
        print(f"Error: sonido no encontrado en: {path}")
        return None
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(0.2)
        return sound
    except Exception as e:
        print(f"Advertencia: no se pudo cargar {filename}. Error: {e}")
        return None

class Weapon:
    def __init__(self, owner, cooldown=60, damage=10, kickback=0, shake=0, spread=0):
        self.owner = owner
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.damage = damage
        self.projectile_pool = None
        self.kickback = kickback
        self.shake_amount = shake
        self.base_spread = spread
        self.current_spread = spread
        self.shoot_sound = None

    def set_projectile_pool(self, pool):
        self.projectile_pool = pool

    def update(self, dt=1.0):
        if self.current_cooldown > 0:
            cooldown_mult = getattr(self.owner, 'global_cooldown_mult', 1.0)
            self.current_cooldown -= 1 * dt / cooldown_mult

        if self.current_spread > self.base_spread:
            self.current_spread -= 0.01 * dt
            if self.current_spread < self.base_spread:
                self.current_spread = self.base_spread

    def shoot(self, camera=None):
        if self.current_cooldown <= 0:
            if self.activate(camera):
                self.current_cooldown = self.cooldown
                self._apply_physics(camera)
                if self.shoot_sound:
                    self.shoot_sound.play()
                return True
        return False

    def _apply_physics(self, camera):
        if self.kickback > 0:
            angle = self.owner.angle
            self.owner.vel_x += -math.cos(angle) * self.kickback
            self.owner.vel_y += -math.sin(angle) * self.kickback
        if camera and self.shake_amount > 0:
            camera.add_shake(self.shake_amount)

    def _apply_player_proj_mods(self, projectile):
        """
        Aplica los modificadores del jugador al proyectil recién creado.
        projectile_size_mult afecta SOLO el tamaño VISUAL (self.size).
        La hitbox no cambia para evitar colisiones fantasma a distancia.
        """
        size_mult = getattr(self.owner, 'projectile_size_mult', 1.0)
        if size_mult != 1.0:
            projectile.size = max(3, int(projectile.size * size_mult))

    def activate(self, camera=None):
        return False

class PistolWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=12, damage=12, kickback=0, shake=2.0, spread=0.02)
        self.shoot_sound = load_sound("pistol_fire.wav")

    def activate(self, camera=None):
        if not self.projectile_pool:
            return False

        owner = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)

        angle = owner.angle + random.uniform(-self.current_spread, self.current_spread)
        spawn_dist = 18
        px = owner.x + math.cos(angle) * spawn_dist
        py = owner.y + math.sin(angle) * spawn_dist

        p = self.projectile_pool.get(
            px, py, angle,
            speed=16 * speed_mult,
            damage=final_dmg,
            penetration=1 + extra_pen,
            image_type='circle'
        )
        p.color = (0, 255, 255)
        self._apply_player_proj_mods(p)

        self.current_spread = min(self.current_spread + 0.05, 0.15)
        return True

class ShotgunWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=50, damage=18, kickback=12.0, shake=8.0, spread=0.4)
        self.pellets = 8
        self.shoot_sound = load_sound("shotgun_fire.wav")

    def activate(self, camera=None):
        if not self.projectile_pool:
            return False

        owner = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)
        base_angle  = owner.angle

        for i in range(self.pellets):
            factor = i / (self.pellets - 1) if self.pellets > 1 else 0.5
            offset = (factor - 0.5) * self.base_spread
            angle  = base_angle + offset + random.uniform(-0.05, 0.05)

            px = owner.x + math.cos(base_angle) * 15
            py = owner.y + math.sin(base_angle) * 15

            p = self.projectile_pool.get(
                px, py, angle,
                speed=random.uniform(14, 16) * speed_mult,
                damage=final_dmg,
                penetration=3 + extra_pen,
                lifetime=35,
                image_type='square'
            )
            p.color = (255, random.randint(100, 150), 0)
            self._apply_player_proj_mods(p)

        return True

class LaserWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=30, kickback=0, shake=1.0, spread=0)
        self.max_range = 1500
        self.duration = 10
        self.draw_timer = 0

    def update(self, dt=1.0):
        super().update(dt)
        if self.draw_timer > 0:
            self.draw_timer -= 1 * dt

    def activate(self, camera=None):
        self.draw_timer = self.duration
        return True

    def get_beam_info(self):
        if self.draw_timer > 0:
            owner = self.owner
            end_x = owner.x + math.cos(owner.angle) * self.max_range
            end_y = owner.y + math.sin(owner.angle) * self.max_range
            return (owner.x, owner.y), (end_x, end_y)
        return None

    def get_damage_per_second(self):
        """Daño por segundo del láser incluyendo global_damage_mult del jugador"""
        damage_mult = getattr(self.owner, 'global_damage_mult', 1.0)
        return self.damage * damage_mult * 6

    def render(self, screen, camera):
        if self.draw_timer > 0:
            owner = self.owner
            start = camera.apply_coords(owner.x, owner.y)

            end_x = owner.x + math.cos(owner.angle) * self.max_range
            end_y = owner.y + math.sin(owner.angle) * self.max_range

            jitter = 2
            end_x += random.uniform(-jitter, jitter)
            end_y += random.uniform(-jitter, jitter)
            end = camera.apply_coords(end_x, end_y)

            progress = self.draw_timer / self.duration
            width = max(2, int(10 * progress))

            pygame.draw.line(screen, (0, 200, 255), start, end, width + 4)
            pygame.draw.line(screen, (255, 255, 255), start, end, width)

class AssaultRifleWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=8, damage=20, kickback=0.5, shake=2.0, spread=0.05)
        self.max_spread = 0.35
        self.shoot_sound = load_sound("rifle_fire.wav")

    def activate(self, camera=None):
        if not self.projectile_pool:
            return False

        owner = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)

        angle = owner.angle + random.uniform(-self.current_spread, self.current_spread)
        px = owner.x + math.cos(angle) * 22
        py = owner.y + math.sin(angle) * 22

        p = self.projectile_pool.get(
            px, py, angle,
            speed=19 * speed_mult,
            damage=final_dmg,
            penetration=1 + extra_pen,
            lifetime=60,
            image_type='square'
        )
        p.color = (255, 230, 100)
        self._apply_player_proj_mods(p)

        self.current_spread = min(self.current_spread + 0.04, self.max_spread)
        return True


class SniperWeapon(Weapon):
    """
    Rifle de Caza — el arma de mayor penetración del juego.

    Estadísticas base:
      · Daño:        110 (x global_damage_mult)
      · Penetración: 8 base + extra_penetration del jugador
      · Cooldown:    100 frames (~1.67s a 60fps)
      · Velocidad:   38 px/frame — el proyectil más rápido
      · Dispersión:  0.0 — disparo perfectamente preciso

    Visuals distintivos:
      · Proyectil fucsia (255, 30, 180) delgado
      · Destello de cañón blanco-fucsia al disparar
      · Línea de trayectoria fantasma que se desvanece
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=100, damage=110, kickback=14.0, shake=9.0, spread=0.0)
        self.shoot_sound = load_sound("pistol_fire.wav")   # reutiliza hasta tener audio propio
        self._muzzle_flash = 0   # frames de destello de cañón

    def update(self, dt=1.0):
        super().update(dt)
        if self._muzzle_flash > 0:
            self._muzzle_flash -= dt

    def activate(self, camera=None):
        if not self.projectile_pool:
            return False

        owner       = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)

        angle = owner.angle   # sin dispersión — arma de precisión
        px = owner.x + math.cos(angle) * 28
        py = owner.y + math.sin(angle) * 28

        p = self.projectile_pool.get(
            px, py, angle,
            speed=38 * speed_mult,
            damage=final_dmg,
            penetration=8 + extra_pen,
            lifetime=220,
            image_type='circle'
        )
        p.color   = (255, 30, 180)
        p.size    = 5
        self._apply_player_proj_mods(p)
        self._muzzle_flash = 8
        return True

    def render(self, screen, camera):
        """Destello de cañón y línea de trayectoria fantasma al disparar."""
        if self._muzzle_flash <= 0:
            return
        owner  = self.owner
        angle  = owner.angle
        sx, sy = camera.apply_coords(owner.x, owner.y)
        prog   = self._muzzle_flash / 8.0

        # Línea de trayectoria (trazo fantasma)
        end_x = sx + math.cos(angle) * 500 * prog
        end_y = sy + math.sin(angle) * 500 * prog
        alpha  = int(prog * 180)
        line_surf = pygame.Surface(
            (int(abs(end_x - sx)) + 4, int(abs(end_y - sy)) + 4),
            pygame.SRCALPHA
        )
        pygame.draw.line(screen, (255, 30, 180, alpha),
                         (int(sx), int(sy)), (int(end_x), int(end_y)), 2)

        # Flash blanco en boca de cañón
        flash_r = int(14 * prog)
        if flash_r > 1:
            cx = int(sx + math.cos(angle) * 28)
            cy = int(sy + math.sin(angle) * 28)
            fs = pygame.Surface((flash_r * 2, flash_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fs, (255, 220, 255, int(prog * 220)),
                               (flash_r, flash_r), flash_r)
            screen.blit(fs, (cx - flash_r, cy - flash_r))