"""
Sistema de armas.

OrbitalWeapon v2:
  · Empieza con 1 orbe (era 3).
  · orb_radius=10 (era 15) — hitbox más pequeño y justo.
  · Variables de instancia (orbit_speed, hit_cooldown_max) en vez de clase.
  · Métodos de mejora: add_orb(), increase_speed(), increase_orbit_radius(),
    increase_damage_mult() — llamados desde UpgradeScene._apply_upgrade().
  · _rebuild_glow() reconstruye la caché solo cuando cambia el radio del orbe.
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

    def _apply_player_proj_mods(self, projectile, base_size=6):
        size_mult = getattr(self.owner, 'projectile_size_mult', 1.0)
        projectile.size = max(3, int(base_size * size_mult))

    def activate(self, camera=None):
        return False

    def auto_shoot(self, dt=1.0):
        pass

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
            speed=16 * speed_mult, damage=final_dmg,
            penetration=1 + extra_pen, image_type='circle'
        )
        p.color = (0, 255, 255)
        self._apply_player_proj_mods(p, base_size=6)
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
                speed=random.uniform(14, 16) * speed_mult, damage=final_dmg,
                penetration=3 + extra_pen, lifetime=35, image_type='square'
            )
            p.color = (255, random.randint(100, 150), 0)
            self._apply_player_proj_mods(p, base_size=7)
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
            speed=19 * speed_mult, damage=final_dmg,
            penetration=1 + extra_pen, lifetime=60, image_type='square'
        )
        p.color = (255, 230, 100)
        self._apply_player_proj_mods(p, base_size=7)
        self.current_spread = min(self.current_spread + 0.04, self.max_spread)
        return True

class SniperWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=100, damage=110, kickback=14.0, shake=9.0, spread=0.0)
        self.shoot_sound = load_sound("pistol_fire.wav")
        self._muzzle_flash = 0

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
        angle = owner.angle
        px = owner.x + math.cos(angle) * 28
        py = owner.y + math.sin(angle) * 28
        p = self.projectile_pool.get(
            px, py, angle,
            speed=38 * speed_mult, damage=final_dmg,
            penetration=8 + extra_pen, lifetime=220, image_type='circle'
        )
        p.color   = (255, 30, 180)
        p.size    = 5
        self._apply_player_proj_mods(p, base_size=5)
        self._muzzle_flash = 8
        return True

    def render(self, screen, camera):
        owner = self.owner
        try:
            is_active = owner.weapons[owner.current_weapon_index] is self
        except (IndexError, AttributeError):
            is_active = False
        angle  = owner.angle
        sp     = camera.apply_coords(owner.x, owner.y)
        sx, sy = int(sp[0]), int(sp[1])
        if is_active:
            scope_len = 950
            ex = int(sx + math.cos(angle) * scope_len)
            ey = int(sy + math.sin(angle) * scope_len)
            pygame.draw.line(screen, (100, 0, 0),   (sx, sy), (ex, ey), 3)
            pygame.draw.line(screen, (200, 15, 15), (sx, sy), (ex, ey), 2)
            pygame.draw.line(screen, (255, 40, 40), (sx, sy), (ex, ey), 1)
            pygame.draw.circle(screen, (180, 0, 0),   (ex, ey), 6, 1)
            pygame.draw.circle(screen, (255, 80, 80), (ex, ey), 3)
            pygame.draw.circle(screen, (255, 200, 200), (ex, ey), 1)
        if self._muzzle_flash <= 0:
            return
        prog = self._muzzle_flash / 8.0
        end_x = int(sx + math.cos(angle) * 500 * prog)
        end_y = int(sy + math.sin(angle) * 500 * prog)
        pygame.draw.line(screen, (255, 30, 180), (sx, sy), (end_x, end_y), 2)
        flash_r = int(14 * prog)
        if flash_r > 1:
            muz_x = int(sx + math.cos(angle) * 28)
            muz_y = int(sy + math.sin(angle) * 28)
            fs = pygame.Surface((flash_r * 2, flash_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(fs, (255, 220, 255, int(prog * 220)),
                               (flash_r, flash_r), flash_r)
            screen.blit(fs, (muz_x - flash_r, muz_y - flash_r))

class NovaWeapon(Weapon):
    """Auto-disparo circular cada ~3 segundos. 8 proyectiles, penetración infinita."""
    def __init__(self, owner):
        super().__init__(owner, cooldown=180, damage=30, kickback=0, shake=5.0, spread=0)
        self.num_projectiles = 8

    def auto_shoot(self, dt=1.0):
        if self.current_cooldown <= 0 and self.projectile_pool:
            if self.activate():
                self.current_cooldown = self.cooldown

    def activate(self, camera=None):
        if not self.projectile_pool:
            return False
        owner       = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)
        num         = self.num_projectiles
        for i in range(num):
            angle = (math.pi * 2 / num) * i
            px = owner.x + math.cos(angle) * 18
            py = owner.y + math.sin(angle) * 18
            p = self.projectile_pool.get(
                px, py, angle,
                speed=9 * speed_mult, damage=final_dmg,
                penetration=9999 + extra_pen, lifetime=100, image_type='circle'
            )
            p.color = (220, 80, 255)
            p.size  = 9
            self._apply_player_proj_mods(p, base_size=9)
        if camera:
            camera.add_shake(5.0)
        return True


class OrbitalWeapon(Weapon):
    """
    Orbes Orbitales — empieza con 1 orbe, mejoras añaden más y los potencian.

    · No usa projectile_pool — los orbes son entidades lógicas propias.
    · Hitbox pequeño (orb_radius=10) y ajustable con mejoras.
    · Variables de instancia: orbit_speed, orb_radius, hit_cooldown_max.
    · Métodos de mejora llamados desde UpgradeScene:
        add_orb()              → +1 orbe (máx 4)
        increase_speed(mult)   → velocidad de rotación
        increase_orbit_radius(v)→ radio de la órbita
        increase_damage_mult(m) → daño base

    OPTIMIZACIÓN: _glow_surf pre-allocada, reconstruida solo si cambia orb_radius.
    """

    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=45, kickback=0, shake=0, spread=0)
        self.num_orbs         = 1       # empieza con 1 orbe
        self.orbit_radius     = 95      # radio de la órbita (px)
        self.orb_radius       = 10      # radio visual + hitbox del orbe (era 15)
        self.orbit_speed      = 0.05    # rad/frame
        self.hit_cooldown_max = 35      # frames entre golpes al mismo enemigo
        self._angle           = 0.0
        self._hit_cd: dict[int, float] = {}

        self._rebuild_glow()

    def _rebuild_glow(self):
        """Reconstruye la surface de glow. Llamar solo cuando cambia orb_radius."""
        gs = self.orb_radius * 3
        self._glow_surf = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._glow_surf, (50, 180, 255, 55), (gs, gs), gs)
        self._glow_size = gs

    # ── Métodos de mejora (llamados desde UpgradeScene) ─────────────────
    def add_orb(self):
        """Añade 1 orbe orbital. Máximo 4 en total."""
        self.num_orbs = min(4, self.num_orbs + 1)

    def increase_speed(self, mult: float):
        """Multiplica la velocidad angular. Máximo 0.18 rad/frame."""
        self.orbit_speed = min(0.18, self.orbit_speed * mult)

    def increase_orbit_radius(self, amount: float):
        """Amplía el radio de la órbita en px."""
        self.orbit_radius += amount

    def increase_damage_mult(self, mult: float):
        """Multiplica el daño base de los orbes."""
        self.damage = int(self.damage * mult)

    def increase_orb_size(self, amount: float):
        """Aumenta el radio visual del orbe y reconstruye el glow."""
        self.orb_radius = min(20, self.orb_radius + amount)
        self._rebuild_glow()

    # ── Lógica ──────────────────────────────────────────────────────────
    def update(self, dt=1.0):
        super().update(dt)
        self._angle += self.orbit_speed * dt
        # Decrementar cooldowns de golpe (limpieza eficiente)
        expired = [k for k, v in self._hit_cd.items() if v <= dt]
        for k in expired:
            del self._hit_cd[k]
        for k in list(self._hit_cd):
            if k in self._hit_cd:
                self._hit_cd[k] -= dt

    def get_orb_positions(self):
        owner = self.owner
        n     = self.num_orbs
        angle = self._angle
        r     = self.orbit_radius
        tau_n = math.pi * 2 / n
        return [
            (
                owner.x + math.cos(angle + tau_n * i) * r,
                owner.y + math.sin(angle + tau_n * i) * r,
            )
            for i in range(n)
        ]

    def check_hits(self, enemies, knockback_mult=1.0):
        """
        Detecta colisiones orbe-enemigo → [(enemy, damage)].
        Hitbox = orb_radius + 10px de margen (ajustable con mejoras de tamaño).
        """
        positions   = self.get_orb_positions()
        damage_mult = getattr(self.owner, 'global_damage_mult', 1.0)
        final_dmg   = self.damage * damage_mult
        # Margen menor que antes (era +14) → hitbox más justo
        hit_r_sq    = (self.orb_radius + 10) ** 2

        hits = []
        for ox, oy in positions:
            for enemy in enemies:
                if not enemy.is_alive:
                    continue
                eid = id(enemy)
                if eid in self._hit_cd:
                    continue
                dx = enemy.x - ox
                dy = enemy.y - oy
                if dx * dx + dy * dy <= hit_r_sq:
                    self._hit_cd[eid] = self.hit_cooldown_max
                    enemy.apply_knockback(ox, oy, force=9 * knockback_mult)
                    hits.append((enemy, final_dmg))
        return hits

    def activate(self, camera=None):
        return True   # siempre activo

    def render(self, screen, camera):
        gs = self._glow_size
        r  = self.orb_radius

        for ox, oy in self.get_orb_positions():
            sp = camera.apply_coords(ox, oy)
            cx, cy = int(sp[0]), int(sp[1])

            # Glow pre-allocado (sin crear Surface por frame)
            screen.blit(self._glow_surf, (cx - gs, cy - gs))
            pygame.draw.circle(screen, (100, 210, 255), (cx, cy), r)
            pygame.draw.circle(screen, (220, 245, 255), (cx, cy), max(1, r // 2))
            pygame.draw.circle(screen, (180, 230, 255), (cx, cy), r, 2)


class BoomerangWeapon(Weapon):
    """Boomerang Arcano — proyectil de ida y vuelta con pierce infinito."""

    MAX_DIST = 400

    def __init__(self, owner):
        super().__init__(owner, cooldown=80, damage=60, kickback=0, shake=3.0, spread=0)
        self._proj      = None
        self._start_x   = 0.0
        self._start_y   = 0.0
        self._returning = False

    def update(self, dt=1.0):
        super().update(dt)
        p = self._proj
        if p:
            if p.is_alive:
                if not self._returning:
                    dx = p.x - self._start_x
                    dy = p.y - self._start_y
                    if dx * dx + dy * dy >= self.MAX_DIST ** 2:
                        p.vel_x  = -p.vel_x
                        p.vel_y  = -p.vel_y
                        p.hit_enemies.clear()
                        p.color  = (255, 140, 30)
                        self._returning = True
                else:
                    owner = self.owner
                    dx = p.x - owner.x
                    dy = p.y - owner.y
                    if dx * dx + dy * dy < 45 ** 2:
                        p.is_alive = False
                        self._proj      = None
                        self._returning = False
                    elif dx * dx + dy * dy > 1500 ** 2:
                        p.is_alive = False
                        self._proj      = None
                        self._returning = False
            else:
                if self.current_cooldown <= 0:
                    self.current_cooldown = self.cooldown
                self._proj      = None
                self._returning = False

    def auto_shoot(self, dt=1.0):
        if self.current_cooldown <= 0 and self.projectile_pool:
            if self._fire_boomerang():
                self.current_cooldown = self.cooldown

    def activate(self, camera=None):
        return False

    def _fire_boomerang(self):
        if self._proj and self._proj.is_alive:
            return False
        if not self.projectile_pool:
            return False
        owner       = self.owner
        speed_mult  = getattr(owner, 'projectile_speed_mult', 1.0)
        extra_pen   = getattr(owner, 'extra_penetration', 0)
        damage_mult = getattr(owner, 'global_damage_mult', 1.0)
        final_dmg   = int(self.damage * damage_mult)
        angle = owner.angle
        px = owner.x + math.cos(angle) * 24
        py = owner.y + math.sin(angle) * 24
        p = self.projectile_pool.get(
            px, py, angle,
            speed=15 * speed_mult, damage=final_dmg,
            penetration=9999 + extra_pen, lifetime=800, image_type='square'
        )
        p.color         = (255, 220, 60)
        self._apply_player_proj_mods(p, base_size=11)
        self._proj      = p
        self._start_x   = owner.x
        self._start_y   = owner.y
        self._returning = False
        return True