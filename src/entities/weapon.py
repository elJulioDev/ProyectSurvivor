"""
Sistema de armas optimizado para Disparo Manual (Top-Down Shooter)
Estructura limpia: Pistola, Escopeta y Láser.
"""
import math, random, pygame

class Weapon:
    def __init__(self, owner, cooldown=60, damage=10):
        self.owner = owner
        self.cooldown = cooldown
        self.current_cooldown = 0
        self.damage = damage
        self.projectile_pool = None

    def set_projectile_pool(self, pool):
        """Asigna el pool de proyectiles"""
        self.projectile_pool = pool

    def update(self, dt=1.0):
        """Gestiona el enfriamiento (Cooldown)"""
        if self.current_cooldown > 0:
            self.current_cooldown -= 1 * dt
            return 0
        return 0

    def shoot(self):
        """
        Intenta disparar si el cooldown lo permite.
        Se llama al hacer clic izquierdo.
        """
        if self.current_cooldown <= 0:
            if self.activate():
                self.current_cooldown = self.cooldown
                return True
        return False

    def activate(self):
        """Lógica específica del disparo (a implementar por los hijos)"""
        return False

class PistolWeapon(Weapon):
    """
    Arma básica (anteriormente WandWeapon).
    Dispara un solo proyectil preciso hacia el cursor.
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=15, damage=8)
        
    def activate(self):
        if not self.projectile_pool:
            return False
        
        angle = self.owner.angle
        
        # Calcular posición de salida (un poco en frente del jugador)
        spawn_dist = 15
        px = self.owner.x + math.cos(angle) * spawn_dist
        py = self.owner.y + math.sin(angle) * spawn_dist
        
        # Solicitar proyectil al pool
        p = self.projectile_pool.get(
            px, py, 
            angle, 
            speed=14,
            damage=self.damage, 
            penetration=1,
            image_type='circle'
        )
        p.color = (0, 255, 255)
        return True

class ShotgunWeapon(Weapon):
    """
    Escopeta: Dispara abanico de proyectiles.
    Mejorada para mayor consistencia en los impactos.
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=50, damage=20)
        self.pellets = 8
        self.spread = 0.5
        
    def activate(self):
        if not self.projectile_pool:
            return False
        
        base_angle = self.owner.angle
        # Pequeña variación aleatoria en el ángulo base para realismo
        base_angle += random.uniform(-0.05, 0.05)
        
        for i in range(self.pellets):
            # Calcular ángulo de cada perdigón distribuido uniformemente
            # (i / (self.pellets - 1)) va de 0 a 1
            if self.pellets > 1:
                factor = i / (self.pellets - 1)
                offset = (factor - 0.5) * self.spread
            else:
                offset = 0
            
            angle = base_angle + offset
            
            # Ajuste de posición de salida
            spawn_dist = 10
            px = self.owner.x + math.cos(base_angle) * spawn_dist
            py = self.owner.y + math.sin(base_angle) * spawn_dist
            
            p = self.projectile_pool.get(
                px, py, 
                angle, 
                speed=15,
                damage=self.damage, 
                penetration=2,
                lifetime=45,
                image_type='square'
            )
            p.color = (255, 100 + random.randint(-20, 20), 0)
        return True

class LaserWeapon(Weapon):
    """
    Láser: Dispara un rayo instantáneo (Hitscan).
    Visualmente impactante y daño inmediato.
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=0, damage=30)
        self.max_range = 1500
        self.duration = 10
        self.draw_timer = 0
        
    def update(self, dt=1.0):
        super().update(dt)
        # Reducir temporizador visual
        if self.draw_timer > 0:
            self.draw_timer -= 1 * dt

    def activate(self):
        # Reiniciar temporizador visual
        self.draw_timer = self.duration
        return True # Devuelve True para confirmar que disparó

    def get_beam_info(self):
        """
        Retorna la tupla (start_pos, end_pos) si el láser está activo.
        Usado por GameplayScene para calcular colisiones tipo Raycast.
        """
        if self.draw_timer > 0:
            end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
            end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
            return (self.owner.x, self.owner.y), (end_x, end_y)
        return None

    def render(self, screen, camera):
        """Renderizado del efecto visual del láser"""
        if self.draw_timer > 0:
            # Calcular posiciones en pantalla
            world_start_x = self.owner.x
            world_start_y = self.owner.y
            world_end_x = self.owner.x + math.cos(self.owner.angle) * self.max_range
            world_end_y = self.owner.y + math.sin(self.owner.angle) * self.max_range
            
            start_pos = camera.apply_coords(world_start_x, world_start_y)
            end_pos = camera.apply_coords(world_end_x, world_end_y)
            
            # Efecto de desvanecimiento (el ancho disminuye con el tiempo)
            progress = self.draw_timer / self.duration
            width_core = max(1, int(4 * progress))
            width_glow = max(2, int(10 * progress))
            
            # Dibujar brillo exterior y núcleo interior
            # Color: Cyan eléctrico / Blanco
            pygame.draw.line(screen, (0, 100, 100), start_pos, end_pos, width_glow + 4) # Aura oscura
            pygame.draw.line(screen, (0, 255, 255), start_pos, end_pos, width_glow)     # Brillo
            pygame.draw.line(screen, (255, 255, 255), start_pos, end_pos, width_core)   # Núcleo

class AssaultRifleWeapon(Weapon):
    """
    Rifle de Asalto (AK-47 / M4).
    Disparo automático rápido con ligera dispersión.
    """
    def __init__(self, owner):
        super().__init__(owner, cooldown=8, damage=20)
        self.spread = 0.1

    def activate(self):
        if not self.projectile_pool:
            return False

        # Ángulo base + pequeña variación aleatoria (retroceso)
        angle = self.owner.angle + random.uniform(-self.spread, self.spread)

        # Posición de salida (cañón del arma)
        spawn_dist = 20
        px = self.owner.x + math.cos(angle) * spawn_dist
        py = self.owner.y + math.sin(angle) * spawn_dist

        # Solicitar proyectil
        p = self.projectile_pool.get(
            px, py,
            angle,
            speed=17,
            damage=self.damage,
            penetration=1,
            lifetime=50,
            image_type='square'
        )
        
        # Color dorado/amarillo bala
        p.color = (255, 215, 0) 
        return True