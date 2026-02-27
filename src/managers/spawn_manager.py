"""
SpawnManager con sistema de reciclaje de enemigos estilo Vampire Survivors.

Lógica clave:
- Los enemigos muertos se guardan en un 'dead_pool' en lugar de eliminarse.
- Al necesitar un nuevo enemigo, se recicla uno del dead_pool (recycle()) en vez
  de instanciar un objeto nuevo. Esto reduce drásticamente el garbage collection.
- Los spawns ocurren alrededor de la vista de la cámara, no en los bordes del mundo.
- Enemigos vivos que se alejen demasiado se TELETRANSPORTAN con teleport_to(),
  que preserva su vida y estadísticas actuales. NO se hace recycle().
"""

import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT, WINDOW_WIDTH, WINDOW_HEIGHT


# Distancia fuera de la pantalla donde aparecen los enemigos (en píxeles de mundo)
SPAWN_MARGIN_MIN = 80    # Mínimo alejamiento del borde de pantalla
SPAWN_MARGIN_MAX = 200   # Máximo alejamiento del borde de pantalla

# Si un enemigo vivo supera esta distancia de la CÁMARA, se teletransporta
# (no del jugador, sino del centro de la ventana visible)
TELEPORT_DISTANCE = 1800


class SpawnManager:
    def __init__(self):
        self.game_time = 0          # Tiempo en frames
        self.spawn_timer = 0
        self.difficulty_level = 1

        self.base_spawn_rate = 60   # Frames entre spawns
        self.min_spawn_rate = 5     # Mínimo (late game: ~12 enemigos/segundo)

        # Pool de enemigos muertos listos para ser reciclados
        self.dead_pool: list[Enemy] = []

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def add_to_dead_pool(self, enemy: Enemy):
        """Recibe un enemigo muerto para reutilizarlo más adelante."""
        self.dead_pool.append(enemy)

    def update(self, dt, current_enemy_count, camera_offset=(0, 0)):
        """
        Actualiza el timer y spawna un enemigo si corresponde.

        Returns:
            Enemy reciclado/nuevo listo para agregar a la lista activa, o None
        """
        self.game_time += dt
        self.spawn_timer -= dt

        minutes_passed = (self.game_time / 60) / 60
        self.difficulty_level = 1 + (minutes_passed * 0.5)

        # Límite dinámico de enemigos simultáneos
        max_enemies = min(400, 50 + int(self.game_time / 30))

        if current_enemy_count >= max_enemies:
            return None

        if self.spawn_timer <= 0:
            current_rate = max(
                self.min_spawn_rate,
                self.base_spawn_rate - (minutes_passed * 10)
            )
            self.spawn_timer = current_rate
            return self._spawn_enemy(camera_offset)

        return None

    def try_teleport_distant_enemies(self, enemies: list, camera_offset=(0, 0)):
        """
        Revisa enemigos vivos que se hayan alejado demasiado de la cámara y los
        teletransporta a una posición válida de spawn alrededor de la pantalla.

        IMPORTANTE: Usa enemy.teleport_to() para preservar vida y estadísticas.
        NO llama a recycle() para no resetear al enemigo.

        Returns:
            Número de enemigos teletransportados
        """
        # Centro visible en coordenadas de mundo
        cam_center_x = -camera_offset[0] + WINDOW_WIDTH / 2
        cam_center_y = -camera_offset[1] + WINDOW_HEIGHT / 2
        teleport_sq = TELEPORT_DISTANCE * TELEPORT_DISTANCE

        teleported = 0
        for enemy in enemies:
            if not enemy.is_alive:
                continue
            dx = enemy.x - cam_center_x
            dy = enemy.y - cam_center_y
            if dx * dx + dy * dy > teleport_sq:
                nx, ny = self._get_spawn_position(camera_offset)
                # ── Solo reposicionar, SIN resetear vida ni stats ─────
                enemy.teleport_to(nx, ny)
                teleported += 1
        return teleported

    def get_time_string(self):
        seconds_total = int(self.game_time / 60)
        mins = seconds_total // 60
        secs = seconds_total % 60
        return f"{mins:02d}:{secs:02d}"

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _spawn_enemy(self, camera_offset=(0, 0)):
        """Genera (o recicla) un enemigo en los bordes del viewport."""
        enemy_type = self._pick_enemy_type()
        speed_mult = 1.0 + (self.difficulty_level * 0.1)
        x, y = self._get_spawn_position(camera_offset)

        if self.dead_pool:
            # ── Reciclar enemigo muerto (sí resetea vida, es un spawn nuevo) ──
            enemy = self.dead_pool.pop()
            enemy.recycle(x, y, speed_multiplier=speed_mult, enemy_type=enemy_type)
            return enemy
        else:
            # ── Crear uno nuevo (solo al inicio o si el pool está vacío) ──
            return Enemy(x, y, speed_multiplier=speed_mult, enemy_type=enemy_type)

    def _get_spawn_position(self, camera_offset=(0, 0)):
        """
        Calcula una posición de spawn justo fuera del viewport actual,
        dentro de los límites del mundo.
        """
        cam_left   = -camera_offset[0]
        cam_top    = -camera_offset[1]
        cam_right  = cam_left + WINDOW_WIDTH
        cam_bottom = cam_top  + WINDOW_HEIGHT

        margin = random.randint(SPAWN_MARGIN_MIN, SPAWN_MARGIN_MAX)

        side = random.choice(['top', 'bottom', 'left', 'right'])

        if side == 'top':
            x = random.uniform(cam_left, cam_right)
            y = cam_top - margin
        elif side == 'bottom':
            x = random.uniform(cam_left, cam_right)
            y = cam_bottom + margin
        elif side == 'left':
            x = cam_left - margin
            y = random.uniform(cam_top, cam_bottom)
        else:  # right
            x = cam_right + margin
            y = random.uniform(cam_top, cam_bottom)

        # Clamping dentro del mundo para evitar spawns fuera del mapa
        x = max(-200, min(WORLD_WIDTH + 200, x))
        y = max(-200, min(WORLD_HEIGHT + 200, y))

        return x, y

    def _pick_enemy_type(self):
        """Elige un tipo de enemigo según el tiempo de juego."""
        seconds = self.game_time / 60

        weights = {'small': 60, 'normal': 30, 'large': 10, 'tank': 0}

        if seconds > 60:
            weights['normal'] += 20
            weights['small'] -= 10
        if seconds > 180:
            weights['large'] += 20
            weights['tank'] += 5
            weights['small'] -= 20
        if seconds > 300:
            weights['tank'] += 15
            weights['normal'] -= 10

        for k in weights:
            weights[k] = max(0, weights[k])

        choices      = list(weights.keys())
        probabilities = list(weights.values())
        return random.choices(choices, weights=probabilities, k=1)[0]