"""
SpawnManager — Vampire Survivors style
  · Spawn CIRCULAR alrededor del jugador desde TODAS las direcciones
  · Cap dinámico: de 200 a 2000+ en ~20 minutos (PC) / 80-680 en móvil
  · Spawn en lotes (batch) para simular la densidad de VS
  · Tipos nuevos: exploder, spitter  (aparecen progresivamente)
  · Escalado de vida proporcional al tiempo
  · Reciclaje sin GC (dead_pool)

PARCHE 3: Cap de enemigos reducido en Android/móvil:
  · PC:     200 + (minutes * 120)  → hasta ~2000 a los 15 min
  · Móvil:   80 + (minutes * 40)  → hasta  ~680 a los 15 min
"""

import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT

# Radio de spawn alrededor del jugador (en píxeles de mundo).
SPAWN_RADIUS_MIN = 650
SPAWN_RADIUS_MAX = 1100

# Si un enemigo vivo supera esta distancia del jugador se teletransporta
TELEPORT_DISTANCE = 1200

class SpawnManager:
    def __init__(self, mobile=False):
        self.game_time        = 0       # en frames (60 fps → 1s = 60)
        self.spawn_timer      = 0
        self.difficulty_level = 1.0

        self.base_spawn_rate = 20       # frames entre spawns al inicio
        self.min_spawn_rate  = 1        # late game (~60 enemigos/s)

        # PARCHE 3: guardar flag de plataforma
        self._is_mobile = mobile

        self.dead_pool: list[Enemy] = []

    def add_to_dead_pool(self, enemy: Enemy):
        self.dead_pool.append(enemy)

    def update(self, dt, current_enemy_count, camera_offset=(0, 0), player_pos=None):
        self.game_time  += dt
        self.spawn_timer -= dt

        minutes = (self.game_time / 60) / 60
        self.difficulty_level = 1.0 + (minutes * 0.15)

        # PARCHE 3: cap dinámico diferente según plataforma
        if self._is_mobile:
            max_enemies = int(80 + (minutes * 40))    # máx ~680 a los 15 min
        else:
            max_enemies = int(200 + (minutes * 120))  # máx ~2000 a los 15 min

        if current_enemy_count >= max_enemies:
            return []

        if self.spawn_timer > 0:
            return []

        # Tasa de spawn
        current_rate = max(
            self.min_spawn_rate,
            self.base_spawn_rate - (minutes * 0.9)
        )
        self.spawn_timer = current_rate

        # BATCH: cuántos enemigos nacen por tick
        room = max_enemies - current_enemy_count
        if minutes < 2:
            batch = 1
        elif minutes < 5:
            batch = random.randint(1, 2)
        elif minutes < 10:
            batch = random.randint(2, 4)
        elif minutes < 20:
            batch = random.randint(3, 6)
        else:
            batch = random.randint(5, 10)

        batch = min(batch, room)
        if batch <= 0:
            return []

        spawned = []
        for _ in range(batch):
            e = self._spawn_enemy(camera_offset, player_pos)
            if e:
                spawned.append(e)
        return spawned

    def try_teleport_distant_enemies(self, enemies: list,
                                     camera_offset=(0, 0), player_pos=None):
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
        if player_pos:
            cx, cy = player_pos
        else:
            cx = -camera_offset[0] + WINDOW_WIDTH  / 2
            cy = -camera_offset[1] + WINDOW_HEIGHT / 2

        for _ in range(15):
            angle  = random.uniform(0, math.pi * 2)
            radius = random.uniform(SPAWN_RADIUS_MIN, SPAWN_RADIUS_MAX)

            x = cx + math.cos(angle) * radius
            y = cy + math.sin(angle) * radius

            if -250 <= x <= WORLD_WIDTH + 250 and -250 <= y <= WORLD_HEIGHT + 250:
                return x, y

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

        if minutes > 3:
            w['normal']   += 15
            w['small']    -= 15
            w['exploder'] += 5

        if minutes > 7:
            w['large']    += 15
            w['spitter']  += 5
            w['small']    -= 20

        if minutes > 13:
            w['spitter']  += 10
            w['exploder'] += 5
            w['large']    += 10
            w['normal']   -= 15

        if minutes > 20:
            w['tank']     += 5
            w['large']    += 10
            w['small']     = 0

        if minutes > 25:
            w['tank']     += 10
            w['exploder'] += 5
            w['normal']   -= 10

        for k in w:
            w[k] = max(0, w[k])

        choices = list(w.keys())
        probs   = list(w.values())
        return random.choices(choices, weights=probs, k=1)[0]