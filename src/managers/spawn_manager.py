"""
SpawnManager — Vampire Survivors style
  · Spawn CIRCULAR alrededor del jugador desde TODAS las direcciones
  · Cap dinámico: de 80 a 800 en ~20 minutos
  · Tipos nuevos: exploder, spitter  (aparecen progresivamente)
  · Escalado de vida proporcional al tiempo
  · Reciclaje sin GC (dead_pool)
"""

import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT

# Radio de spawn alrededor del jugador (en píxeles de mundo).
# La diagonal de pantalla es ≈730px → 420-600px queda justo off-screen.
SPAWN_RADIUS_MIN = 1200
SPAWN_RADIUS_MAX = 1800

# Si un enemigo vivo supera esta distancia del jugador se teletransporta
TELEPORT_DISTANCE = 1900

class SpawnManager:
    def __init__(self):
        self.game_time        = 0       # en frames (60 fps → 1s = 60)
        self.spawn_timer      = 0
        self.difficulty_level = 1.0

        self.base_spawn_rate = 55       # frames entre spawns al inicio
        self.min_spawn_rate  = 4        # late game (~15 enemigos/s)

        self.dead_pool: list[Enemy] = []

    def add_to_dead_pool(self, enemy: Enemy):
        self.dead_pool.append(enemy)

    def update(self, dt, current_enemy_count, camera_offset=(0, 0), player_pos=None):
        self.game_time  += dt
        self.spawn_timer -= dt

        minutes = (self.game_time / 60) / 60
        self.difficulty_level = 1.0 + (minutes * 0.15) # Reducido para que la vida no se dispare tan rápido

        # Cap dinámico: 80 iniciales + 45 por minuto. 
        # A los 30 minutos tendrás alrededor de 1430 enemigos en pantalla.
        max_enemies = int(80 + (minutes * 45))

        if current_enemy_count >= max_enemies:
            return None

        if self.spawn_timer <= 0:
            current_rate = max(
                self.min_spawn_rate,
                self.base_spawn_rate - (minutes * 1.5) # Baja la tasa de spawn más lento
            )
            self.spawn_timer = current_rate
            return self._spawn_enemy(camera_offset, player_pos)

        return None

    def try_teleport_distant_enemies(self, enemies: list,
                                     camera_offset=(0, 0), player_pos=None):
        """
        Teletransporta enemigos que se alejan demasiado al área de spawn.
        Usa teleport_to() para NO resetear vida ni stats.
        """
        # CORRECCIÓN: Usar la posición real del jugador si se proporciona
        if player_pos:
            ref_x, ref_y = player_pos
        else:
            ref_x = -camera_offset[0] + WINDOW_WIDTH  / 2
            ref_y = -camera_offset[1] + WINDOW_HEIGHT / 2

        teleport_sq = TELEPORT_DISTANCE * TELEPORT_DISTANCE
        teleported  = 0

        for enemy in enemies:
            if not enemy.is_alive:
                continue
            dx = enemy.x - ref_x
            dy = enemy.y - ref_y
            if dx * dx + dy * dy > teleport_sq:
                nx, ny = self._get_spawn_position(camera_offset, player_pos)
                enemy.teleport_to(nx, ny)
                teleported += 1

        return teleported

    def get_time_string(self):
        seconds_total = int(self.game_time / 60)
        mins = seconds_total // 60
        secs = seconds_total % 60
        return f"{mins:02d}:{secs:02d}"

    def _spawn_enemy(self, camera_offset=(0, 0), player_pos=None):
        enemy_type  = self._pick_enemy_type()
        speed_mult  = min(2.6, 1.0 + (self.difficulty_level * 0.11))
        health_mult = min(4.5, 1.0 + (self.difficulty_level - 1.0) * 0.32)
        x, y        = self._get_spawn_position(camera_offset, player_pos)

        if self.dead_pool:
            enemy = self.dead_pool.pop()
            enemy.recycle(x, y, speed_multiplier=speed_mult,
                          enemy_type=enemy_type, health_mult=health_mult)
            return enemy
        else:
            return Enemy(x, y, speed_multiplier=speed_mult,
                         enemy_type=enemy_type, health_mult=health_mult)

    def _get_spawn_position(self, camera_offset=(0, 0), player_pos=None):
        """
        Spawn en circunferencia alrededor del jugador (Vampire Survivors).
        Si cae en un lugar inválido (muy fuera de los bordes), re-calcula 
        en lugar de hacer clamping para no meter a los enemigos en la pantalla.
        """
        if player_pos:
            cx, cy = player_pos
        else:
            cx = -camera_offset[0] + WINDOW_WIDTH  / 2
            cy = -camera_offset[1] + WINDOW_HEIGHT / 2

        # Intentar buscar una posición válida hasta 15 veces
        for _ in range(15):
            angle  = random.uniform(0, math.pi * 2)
            radius = random.uniform(SPAWN_RADIUS_MIN, SPAWN_RADIUS_MAX)

            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius

            # Verificamos si la posición está dentro de un rango aceptable del mundo
            if -250 <= x <= WORLD_WIDTH + 250 and -250 <= y <= WORLD_HEIGHT + 250:
                return x, y

        # Fallback de emergencia si el jugador está en una esquina extrema
        # y la mala suerte nos hizo fallar 15 veces. Retornamos la posición 
        # sin importar los límites para garantizar que nazca lejos de la vista.
        angle = random.uniform(0, math.pi * 2)
        radius = random.uniform(SPAWN_RADIUS_MIN, SPAWN_RADIUS_MAX)
        return cx + math.cos(angle) * radius, cy + math.sin(angle) * radius

    def _pick_enemy_type(self):
        minutes = (self.game_time / 60) / 60

        w = {
            'small':    70,
            'normal':   30,
            'large':     0,
            'tank':      0,
            'exploder':  0,
            'spitter':   0,
        }

        # 3 min -> Empieza el desafío, aparecen los primeros exploders
        if minutes > 3:
            w['normal']   += 15
            w['small']    -= 15
            w['exploder'] += 5

        # 7 min -> Aparecen enemigos grandes y los primeros spitters
        if minutes > 7:
            w['large']    += 15
            w['spitter']  += 5
            w['small']    -= 20

        # 13 min -> Transición al mid-game, más peligros a distancia
        if minutes > 13:
            w['spitter']  += 10
            w['exploder'] += 5
            w['large']    += 10
            w['normal']   -= 15

        # 20 min -> Aparecen los Tanks
        if minutes > 20:
            w['tank']     += 5
            w['large']    += 10
            w['small']     = 0
            
        # 25 min -> Horda final pesada
        if minutes > 25:
            w['tank']     += 10
            w['exploder'] += 5
            w['normal']   -= 10

        for k in w:
            w[k] = max(0, w[k])

        choices = list(w.keys())
        probs   = list(w.values())
        return random.choices(choices, weights=probs, k=1)[0]