"""
Sistema de armas optimizado para Disparo Manual (Top-Down Shooter)
Estructura limpia: Pistola, Escopeta y Láser.
"""
import math, random, pygame, os

def load_sound(filename):
    path = os.path.join("assets", "sounds", filename)
    if not os.path.exists(path):
        path = os.path.join("..", "assets", "sounds", filename)
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(0.2)
        return sound
    except Exception as e:
        print(f"Advertencia: No se pudo cargar el sonido {filename}. Error: {e}")
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
        """Asigna el pool de proyectiles"""
        self.projectile_pool = pool

    def update(self, dt=1.0):
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * dt

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
        """Aplica retroceso físico al jugador y temblor a la cámara"""
        if self.kickback > 0:
            angle = self.owner.angle
            recoil_x = -math.cos(angle) * self.kickback
            recoil_y = -math.sin(angle) * self.kickback
            
            self.owner.vel_x += recoil_x
            self.owner.vel_y += recoil_y

        if camera and self.shake_amount > 0:
            camera.add_shake(self.shake_amount)

    def activate(self, camera=None):
        return False

class PistolWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=12, damage=12, kickback=0, shake=2.0, spread=0.02)
        self.shoot_sound = load_sound("pistol_fire.wav")
    def activate(self, camera=None):
        if not self.projectile_pool: return False
        
        angle = self.owner.angle + random.uniform(-self.current_spread, self.current_spread)
        
        spawn_dist = 18
        px = self.owner.x + math.cos(angle) * spawn_dist
        py = self.owner.y + math.sin(angle) * spawn_dist
        
        p = self.projectile_pool.get(
            px, py, angle, speed=16, damage=self.damage, 
            penetration=1, image_type='circle'
        )
        p.color = (0, 255, 255)
        
        self.current_spread = min(self.current_spread + 0.05, 0.15)
        return True

class ShotgunWeapon(Weapon):
    def __init__(self, owner):
        super().__init__(owner, cooldown=55, damage=18, kickback=12.0, shake=8.0, spread=0.4)
        self.pellets = 8
        self.shoot_sound = load_sound("shotgun_fire.wav")
    def activate(self, camera=None):
        if not self.projectile_pool: return False
        
        base_angle = self.owner.angle
        
        for i in range(self.pellets):
            factor = i / (self.pellets - 1) if self.pellets > 1 else 0.5
            offset = (factor - 0.5) * self.base_spread
            angle = base_angle + offset + random.uniform(-0.05, 0.05)
            
            px = self.owner.x + math.cos(base_angle) * 15
            py = self.owner.y + math.sin(base_angle) * 15
            
            p = self.projectile_pool.get(
                px, py, angle, speed=random.uniform(14, 16), 
                damage=self.damage, penetration=3, lifetime=35, image_type='square'
            )
            p.color = (255, random.randint(100, 150), 0)
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
            end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
            end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
            return (self.owner.x, self.owner.y), (end_x, end_y)
        return None

    def render(self, screen, camera):
        if self.draw_timer > 0:
            start = camera.apply_coords(self.owner.x, self.owner.y)
            
            end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
            end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
            
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
        if not self.projectile_pool: return False

        angle = self.owner.angle + random.uniform(-self.current_spread, self.current_spread)

        px = self.owner.x + math.cos(angle) * 22
        py = self.owner.y + math.sin(angle) * 22

        p = self.projectile_pool.get(
            px, py, angle, speed=19, damage=self.damage, 
            penetration=1, lifetime=60, image_type='square'
        )
        p.color = (255, 230, 100)
        
        self.current_spread = min(self.current_spread + 0.04, self.max_spread)
        return True