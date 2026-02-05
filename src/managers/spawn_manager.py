import random
import math
from entities.enemy import Enemy
from settings import WORLD_WIDTH, WORLD_HEIGHT

class SpawnManager:
    def __init__(self):
        self.game_time = 0 # Tiempo en frames
        self.spawn_timer = 0
        self.difficulty_level = 1
        
        # Configuración inicial
        self.base_spawn_rate = 60 # Frames entre spawns (1 segundo al inicio)
        self.min_spawn_rate = 5   # Mínimo 5 frames (12 enemigos por segundo en late game)
        
    def update(self, dt, current_enemy_count):
        self.game_time += dt
        self.spawn_timer -= dt
        
        # Calcular dificultad basada en el tiempo (cada 600 frames = 10 seg aumenta dificultad)
        minutes_passed = (self.game_time / 60) / 60
        self.difficulty_level = 1 + (minutes_passed * 0.5)
        
        # Limite de enemigos para rendimiento (Sube con el tiempo)
        max_enemies = 50 + int(self.game_time / 30) 
        if max_enemies > 400: max_enemies = 400
        
        if current_enemy_count >= max_enemies:
            return None

        if self.spawn_timer <= 0:
            # Reset timer: Mientras más tiempo pasa, más rápido aparecen
            current_rate = max(self.min_spawn_rate, self.base_spawn_rate - (minutes_passed * 10))
            self.spawn_timer = current_rate
            
            return self._spawn_enemy()
            
        return None

    def _spawn_enemy(self):
        # Lógica de probabilidad de enemigos según tiempo de juego
        seconds = self.game_time / 60
        
        # Probabilidades base
        weights = {
            'small': 60,
            'normal': 30,
            'large': 10,
            'tank': 0
        }
        
        # Ajuste dinámico
        if seconds > 60: # Minuto 1
            weights['normal'] += 20
            weights['small'] -= 10
        if seconds > 180: # Minuto 3
            weights['large'] += 20
            weights['tank'] += 5
            weights['small'] -= 20
        if seconds > 300: # Minuto 5
            weights['tank'] += 15
            weights['normal'] -= 10
            
        # Normalizar pesos negativos
        for k in weights: weights[k] = max(0, weights[k])
            
        # Selección
        choices = list(weights.keys())
        probabilities = list(weights.values())
        enemy_type = random.choices(choices, weights=probabilities, k=1)[0]
        
        # Spawn fuera de cámara (implementación simplificada en bordes del mundo)
        # Para VS style real, debería ser relativo a la cámara, pero usaremos bordes del mapa por ahora
        side = random.choice(['top', 'bottom', 'left', 'right'])
        x, y = 0, 0
        padding = 50
        
        if side == 'top': x, y = random.randint(0, WORLD_WIDTH), -padding
        elif side == 'bottom': x, y = random.randint(0, WORLD_WIDTH), WORLD_HEIGHT + padding
        elif side == 'left': x, y = -padding, random.randint(0, WORLD_HEIGHT)
        elif side == 'right': x, y = WORLD_WIDTH + padding, random.randint(0, WORLD_HEIGHT)
        
        # Multiplicador de velocidad global por dificultad
        speed_mult = 1.0 + (self.difficulty_level * 0.1)
        
        return Enemy(x, y, speed_multiplier=speed_mult, enemy_type=enemy_type)

    def get_time_string(self):
        seconds_total = int(self.game_time / 60)
        mins = seconds_total // 60
        secs = seconds_total % 60
        return f"{mins:02d}:{secs:02d}"