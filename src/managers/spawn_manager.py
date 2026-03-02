"""
SpawnManager — Vampire Survivors style (v2)

SISTEMA DE CAPS PROGRESIVOS:
  El juego empieza con pocos enemigos (30 PC / 20 móvil) y escala
  agresivamente hasta un hard cap absoluto (~2000 PC / 680 móvil).

  La curva tiene tres fases:
    · Fase 1  (0–3 min)   : Cap bajo, spawn lento  → "aprendizaje"
    · Fase 2  (3–12 min)  : Cap sube rápido         → presión creciente
    · Fase 3  (12+ min)   : Cap máximo alcanzado     → horda sostenida

RECICLAJE ESTRICTO (Object Pooling):
  · Al iniciar, se pre-alojan N instancias de Enemy inactivas en dead_pool.
    Esto evita tirones del GC al crear objetos durante la partida.
  · Cuando el cap actual > enemigos vivos, el SpawnManager rellena el
    déficit casi instantáneamente con enemigos del pool.
  · Si el pool está vacío y hace falta un enemigo nuevo, se instancia
    uno (solo ocurre en late-game si el pool se agota).

ILUSIÓN DEL ENJAMBRE:
  · try_teleport_distant_enemies() mueve enemigos lejanos frente al jugador
    → con 400 enemigos todos concentrados alrededor de la cámara, el juego
    se ve tan "lleno" como si hubiera 2000 repartidos por el mapa.

PARCHE 3: Cap diferente según plataforma (mobile flag).
"""

import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT

# Spawn circular alrededor del jugador
SPAWN_RADIUS_MIN = 650
SPAWN_RADIUS_MAX = 1100

# Enemigos más allá de esta distancia se teletransportan al frente del jugador
TELEPORT_DISTANCE = 1050   # reducido de 1200 para mayor densidad aparente

# Hard caps absolutos (RAM nunca supera estos valores)
_HARD_CAP_PC     = 2000
_HARD_CAP_MOBILE = 680

# Pool inicial pre-alocado
# No instanciamos el hard cap completo (alargaría la carga),
# sino suficientes para los primeros minutos sin ningún tirón.
_INITIAL_POOL_PC     = 150
_INITIAL_POOL_MOBILE = 80


class SpawnManager:
    def __init__(self, mobile=False):
        self.game_time        = 0       # en frames (60 fps → 1 s = 60)
        self.spawn_timer      = 0
        self.difficulty_level = 1.0

        self._is_mobile = mobile

        # ── Dead pool (Object Pool)
        self.dead_pool: list[Enemy] = []

        # Pre-alojar enemigos inactivos para evitar GC al inicio
        initial_pool = _INITIAL_POOL_MOBILE if mobile else _INITIAL_POOL_PC
        for _ in range(initial_pool):
            e = Enemy(-2000, -2000, enemy_type='small')
            e.is_alive = False
            self.dead_pool.append(e)

        # Hard cap absoluto (nunca se superará)
        self.absolute_max = _HARD_CAP_MOBILE if mobile else _HARD_CAP_PC

    def add_to_dead_pool(self, enemy: Enemy):
        self.dead_pool.append(enemy)

    def update(self, dt, current_enemy_count, camera_offset=(0, 0), player_pos=None):
        self.game_time  += dt
        self.spawn_timer -= dt

        minutes = (self.game_time / 60) / 60
        self.difficulty_level = 1.0 + (minutes * 0.15)

        # Curva de cap progresiva
        #
        #   Fase 1  (0–3 min):  cap sube muy lento   → sensación de inicio
        #   Fase 2  (3–12 min): cap sube agresivo     → horda en crecimiento
        #   Fase 3  (12+ min):  cap se acerca al hard cap
        #
        #   PC:     min0 → 35  |  min3 → 100  |  min12 → 1500  |  min15+ → 2000
        #   Móvil:  min0 → 20  |  min3 →  45  |  min12 →  550  |  min15+ →  680

        if self._is_mobile:
            if minutes < 3:
                current_cap = int(20 + minutes * 8)           # 20 → 44
            elif minutes < 12:
                current_cap = int(44 + (minutes - 3) * 55)    # 44 → 539
            else:
                current_cap = int(539 + (minutes - 12) * 47)  # 539 → hard cap
        else:
            if minutes < 3:
                current_cap = int(35 + minutes * 21)           # 35 → 98
            elif minutes < 12:
                current_cap = int(98 + (minutes - 3) * 155)    # 98 → 1493
            else:
                current_cap = int(1493 + (minutes - 12) * 169) # 1493 → hard cap

        # Nunca superar el hard cap absoluto
        current_cap = min(current_cap, self.absolute_max)

        # Comprobar si hay margen para más enemigos
        if current_enemy_count >= current_cap:
            return []

        if self.spawn_timer > 0:
            return []

        # Tasa de spawn dinámica
        # Si el déficit es grande (principio de partida o tras una muerte
        # masiva), rellenamos rápido. Si ya estamos cerca del cap, frenamos.
        deficit = current_cap - current_enemy_count

        if deficit > 30:
            # Relleno agresivo: llenar la pantalla casi instantáneamente
            self.spawn_timer = 1
        elif deficit > 10:
            self.spawn_timer = max(1, int(8 - minutes * 0.3))
        else:
            # Cerca del cap: goteo lento (solo rellena los recién muertos)
            self.spawn_timer = max(1, int(18 - minutes * 0.5))

        # Batch size dinámico
        # Escala con el déficit y el tiempo de juego
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

        # Generar enemigos
        spawned = []
        for _ in range(batch):
            e = self._spawn_enemy(camera_offset, player_pos)
            if e:
                spawned.append(e)
        return spawned

    def try_teleport_distant_enemies(self, enemies: list,
                                     camera_offset=(0, 0), player_pos=None):
        """
        Teletransporta enemigos lejanos frente al jugador.
        Con TELEPORT_DISTANCE reducido a 1050, los enemigos que salen del
        borde visible reaparecen mucho más rápido → mayor densidad aparente
        sin crear nuevas instancias.
        """
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
            # Reciclar instancia existente (sin GC)
            enemy = self.dead_pool.pop()
            enemy.recycle(x, y, speed_multiplier=speed_mult,
                          enemy_type=enemy_type, health_mult=health_mult)
            return enemy
        else:
            # Solo instanciar cuando el pool está vacío
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