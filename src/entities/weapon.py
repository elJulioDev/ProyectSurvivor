"""
Sistema de armas con soporte completo para multiplicadores del jugador.

NUEVAS ARMAS (Vampire Survivors style):
  - NovaWeapon:      Explosión de 8 proyectiles en todas direcciones (auto-disparo).
                     Perforan infinitamente → ideal contra hordas de +1000 enemigos.
  - OrbitalWeapon:   3 orbes girando alrededor del jugador. Daño por contacto +
                     retroceso fuerte. Sin pool de proyectiles — siempre activo.
  - BoomerangWeapon: Proyectil que perfora infinitamente, vira al llegar a X distancia
                     y regresa. Daña a los mismos enemigos en ambas pasadas.

BASE:
  - Weapon.auto_shoot(dt): Override en armas de disparo pasivo. LevelManager
    lo llama cada frame para que las armas auto-activas gestionen su propio timing.
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
        """
        Override en armas de auto-disparo (Nova, Orbital, etc.).
        LevelManager._update_weapons() lo llama cada frame.
        No hace nada por defecto.
        """
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
            speed=16 * speed_mult,
            damage=final_dmg,
            penetration=1 + extra_pen,
            image_type='circle'
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
                speed=random.uniform(14, 16) * speed_mult,
                damage=final_dmg,
                penetration=3 + extra_pen,
                lifetime=35,
                image_type='square'
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
            speed=19 * speed_mult,
            damage=final_dmg,
            penetration=1 + extra_pen,
            lifetime=60,
            image_type='square'
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
            speed=38 * speed_mult,
            damage=final_dmg,
            penetration=8 + extra_pen,
            lifetime=220,
            image_type='circle'
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
    """
    Nova de Espinas — Auto-disparo circular cada ~3 segundos.

    Lanza 8 proyectiles simultáneos en todas las direcciones con
    penetración infinita. Ideal para limpiar la pantalla cuando estás rodeado.

    · No requiere apuntar — se activa solo.
    · Se beneficia de global_damage_mult, extra_penetration y projectile_speed_mult.
    · El cooldown se reduce con global_cooldown_mult igual que las demás armas.
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=180, damage=30, kickback=0, shake=5.0, spread=0)
        self.num_projectiles = 8

    def auto_shoot(self, dt=1.0):
        """LevelManager llama esto cada frame — dispara cuando el cooldown llega a 0."""
        if self.current_cooldown <= 0 and self.projectile_pool:
            if self.activate():
                self.current_cooldown = self.cooldown
                # Shake de cámara al explotar
                if hasattr(self.owner, 'weapons'):
                    pass  # shake se aplica dentro de activate via _apply_physics si queremos

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
                speed=9 * speed_mult,
                damage=final_dmg,
                penetration=9999 + extra_pen,   # perfora infinitamente
                lifetime=100,
                image_type='circle'
            )
            p.color = (220, 80, 255)
            p.size  = 9
            self._apply_player_proj_mods(p, base_size=9)

        # Sacudida de cámara
        if camera:
            camera.add_shake(5.0)
        return True


class OrbitalWeapon(Weapon):
    """
    Orbes Orbitales — N orbes girando alrededor del jugador continuamente.

    · No usa la projectile_pool — los orbes son entidades lógicas propias.
    · Al tocar a un enemigo: daño + fuerte retroceso (empuja a la multitud).
    · Cooldown de 0.5 s por enemigo para no spamear daño.
    · Se beneficia de global_damage_mult y knockback_mult.
    · LevelManager._update_weapons() llama check_hits() para resolver colisiones.
    """

    ORB_RADIUS   = 15       # radio visual y de colisión del orbe
    ORBIT_SPEED  = 0.05     # rad/frame
    HIT_COOLDOWN = 35       # frames entre golpes al mismo enemigo

    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=45, kickback=0, shake=0, spread=0)
        self.num_orbs     = 3
        self.orbit_radius = 95
        self._angle       = 0.0
        self._hit_cd: dict[int, float] = {}   # id(enemy) → frames restantes

    def update(self, dt=1.0):
        super().update(dt)
        self._angle += self.ORBIT_SPEED * dt
        # Decrementar cooldowns de golpe
        to_del = [k for k, v in self._hit_cd.items() if v <= dt]
        for k in to_del:
            del self._hit_cd[k]
        for k in list(self._hit_cd):
            if k in self._hit_cd:
                self._hit_cd[k] -= dt

    def get_orb_positions(self):
        owner = self.owner
        n     = self.num_orbs
        return [
            (
                owner.x + math.cos(self._angle + (math.pi * 2 / n) * i) * self.orbit_radius,
                owner.y + math.sin(self._angle + (math.pi * 2 / n) * i) * self.orbit_radius,
            )
            for i in range(n)
        ]

    def check_hits(self, enemies, knockback_mult=1.0):
        """
        Detecta colisiones orbe-enemigo y devuelve lista de (enemy, damage).
        Llamar desde LevelManager._update_weapons() cada frame.
        """
        positions   = self.get_orb_positions()
        damage_mult = getattr(self.owner, 'global_damage_mult', 1.0)
        final_dmg   = self.damage * damage_mult
        hit_r_sq    = (self.ORB_RADIUS + 14) ** 2   # margen para hitbox generosa

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
                    self._hit_cd[eid] = self.HIT_COOLDOWN
                    # Knockback hacia afuera desde el orbe
                    enemy.apply_knockback(ox, oy, force=9 * knockback_mult)
                    hits.append((enemy, final_dmg))
        return hits

    def activate(self, camera=None):
        return True   # siempre activo

    def render(self, screen, camera):
        for ox, oy in self.get_orb_positions():
            sp = camera.apply_coords(ox, oy)
            cx, cy = int(sp[0]), int(sp[1])
            r  = self.ORB_RADIUS

            # Glow exterior suave
            gs = r * 3
            glow = pygame.Surface((gs * 2, gs * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (50, 180, 255, 55), (gs, gs), gs)
            screen.blit(glow, (cx - gs, cy - gs))

            # Cuerpo del orbe
            pygame.draw.circle(screen, (100, 210, 255), (cx, cy), r)
            pygame.draw.circle(screen, (220, 245, 255), (cx, cy), r // 2)
            pygame.draw.circle(screen, (180, 230, 255), (cx, cy), r, 2)


class BoomerangWeapon(Weapon):
    """
    Boomerang Arcano — un único proyectil de ida y vuelta.
    """
    MAX_DIST = 400  # Aumentado el px antes de invertir dirección

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
                        # Invertir dirección y cambiar color para indicar el regreso
                        p.vel_x  = -p.vel_x
                        p.vel_y  = -p.vel_y
                        p.hit_enemies.clear()   # puede volver a dañar en el regreso
                        p.color  = (255, 140, 30)
                        self._returning = True
                else:
                    # Cerca del jugador → el boomerang es recogido
                    owner = self.owner
                    dx = p.x - owner.x
                    dy = p.y - owner.y
                    if dx * dx + dy * dy < 45 ** 2: # Radio de captura más amable
                        p.is_alive = False
                        self._proj      = None
                        self._returning = False
                    elif dx * dx + dy * dy > 1500 ** 2: 
                        # Si no es atrapado, requiere viajar un gran tramo (~1500px) para disiparse
                        p.is_alive = False
                        self._proj      = None
                        self._returning = False
            else:
                # Si el proyectil muere forzosamente (ej. chocó con el límite del mapa)
                # Reseteamos el arma pero aplicamos el cooldown para evitar el "auto-reload rápido"
                if self.current_cooldown <= 0:
                    self.current_cooldown = self.cooldown
                self._proj      = None
                self._returning = False

    def auto_shoot(self, dt=1.0):
        # El LevelManager llama esto en cada frame. Dispara cuando el cooldown llegue a 0.
        if self.current_cooldown <= 0 and self.projectile_pool:
            if self._fire_boomerang():
                self.current_cooldown = self.cooldown

    def activate(self, camera=None):
        # Retorna False para bloquear el disparo manual; así no funciona con el click
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
            speed=15 * speed_mult,
            damage=final_dmg,
            penetration=9999 + extra_pen,   # perfora todo
            lifetime=800, # Aumentamos su lifetime por si viaja tramos muy largos
            image_type='square'
        )
        p.color         = (255, 220, 60)
        self._apply_player_proj_mods(p, base_size=11)

        self._proj      = p
        self._start_x   = owner.x
        self._start_y   = owner.y
        self._returning = False
        return True