"""
SpawnManager — Vampire Survivors style (v3)

ESCALA CON NIVEL DEL JUGADOR:
  Además del multiplicador temporal, los enemigos ahora también escalan
  con el nivel del jugador (pasado desde LevelManager):
    · health_mult += 5% por nivel del jugador (desde nivel 2)
    · damage_mult += 4% por nivel del jugador (desde nivel 2)
  Esto asegura que subir de nivel y mejorar al personaje no trivialice
  la dificultad — los enemigos siempre se mantienen competitivos.

  Fórmula (Vampire Survivors style):
    level_factor     = max(0, player_level - 1)
    level_health_m   = 1.0 + level_factor * 0.05
    level_damage_m   = 1.0 + level_factor * 0.04
    health_mult      = min(8.0, time_health_mult * level_health_m)

SISTEMA DE CAPS PROGRESIVOS:
  Fase 1 (0–3 min)  → Cap bajo, spawn lento.
  Fase 2 (3–12 min) → Cap sube rápido.
  Fase 3 (12+ min)  → Cap máximo (horda sostenida).

RECICLAJE ESTRICTO (Object Pooling):
  Dead pool pre-alocado; recycle() evita allocations GC mid-game.
  Enemy.recycle() acepta damage_mult para aplicar la escala por nivel.
"""

import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT

SPAWN_RADIUS_MIN = 650
SPAWN_RADIUS_MAX = 1100
TELEPORT_DISTANCE = 1050

_HARD_CAP_PC     = 2000
_HARD_CAP_MOBILE = 680
_INITIAL_POOL_PC     = 150
_INITIAL_POOL_MOBILE = 80


class SpawnManager:
    def __init__(self, mobile=False):
        self.game_time        = 0
        self.spawn_timer      = 0
        self.difficulty_level = 1.0
        self._is_mobile       = mobile

        self.dead_pool: list[Enemy] = []
        initial_pool = _INITIAL_POOL_MOBILE if mobile else _INITIAL_POOL_PC
        for _ in range(initial_pool):
            e = Enemy(-2000, -2000, enemy_type='small')
            e.is_alive = False
            self.dead_pool.append(e)

        self.absolute_max = _HARD_CAP_MOBILE if mobile else _HARD_CAP_PC

    def add_to_dead_pool(self, enemy: Enemy):
        self.dead_pool.append(enemy)

    def update(self, dt, current_enemy_count, camera_offset=(0, 0),
               player_pos=None, player_level=1):
        self.game_time  += dt
        self.spawn_timer -= dt

        minutes = (self.game_time / 60) / 60
        self.difficulty_level = 1.0 + (minutes * 0.15)

        if self._is_mobile:
            if minutes < 3:
                current_cap = int(20 + minutes * 8)
            elif minutes < 12:
                current_cap = int(44 + (minutes - 3) * 55)
            else:
                current_cap = int(539 + (minutes - 12) * 47)
        else:
            if minutes < 3:
                current_cap = int(35 + minutes * 21)
            elif minutes < 12:
                current_cap = int(98 + (minutes - 3) * 155)
            else:
                current_cap = int(1493 + (minutes - 12) * 169)

        current_cap = min(current_cap, self.absolute_max)

        if current_enemy_count >= current_cap:
            return []
        if self.spawn_timer > 0:
            return []

        deficit = current_cap - current_enemy_count

        if deficit > 30:
            self.spawn_timer = 1
        elif deficit > 10:
            self.spawn_timer = max(1, int(8 - minutes * 0.3))
        else:
            self.spawn_timer = max(1, int(18 - minutes * 0.5))

        if deficit > 50:
            batch = random.randint(5, 12 + int(minutes * 1.5))
        elif deficit > 20:
            batch = random.randint(3, 8 + int(minutes))
        elif minutes < 2:
            batch = 1
        elif minutes < 5:
            batch = random.randint(1, 3)
        elif minutes < 10:
            batch = random.randint(2, 5)
        else:
            batch = random.randint(3, 7)

        batch = min(batch, deficit)
        if batch <= 0:
            return []

        spawned = []
        for _ in range(batch):
            e = self._spawn_enemy(camera_offset, player_pos, player_level)
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

    def _spawn_enemy(self, camera_offset=(0, 0), player_pos=None, player_level=1):
        enemy_type  = self._pick_enemy_type()
        speed_mult  = min(2.6, 1.0 + (self.difficulty_level * 0.11))

        # Escala temporal (tiempo de juego)
        time_health_mult = min(4.5, 1.0 + (self.difficulty_level - 1.0) * 0.32)

        # Escala por nivel del jugador (Vampire Survivors style)
        # +5% HP y +4% daño por cada nivel del jugador a partir del 2
        level_factor      = max(0, player_level - 1)
        level_health_mult = 1.0 + level_factor * 0.05
        level_damage_mult = 1.0 + level_factor * 0.04

        health_mult = min(8.0, time_health_mult * level_health_mult)
        x, y = self._get_spawn_position(camera_offset, player_pos)

        if self.dead_pool:
            enemy = self.dead_pool.pop()
            enemy.recycle(x, y, speed_multiplier=speed_mult,
                          enemy_type=enemy_type, health_mult=health_mult,
                          damage_mult=level_damage_mult)
            return enemy
        else:
            return Enemy(x, y, speed_multiplier=speed_mult,
                         enemy_type=enemy_type, health_mult=health_mult,
                         damage_mult=level_damage_mult)

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