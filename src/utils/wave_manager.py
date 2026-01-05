"""
Gestor de oleadas optimizado
"""
from entities.enemy import Enemy
from settings import ENEMIES_PER_WAVE

class WaveManager:
    def __init__(self):
        self.current_wave = 1
        self.enemies_in_wave = ENEMIES_PER_WAVE
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.spawn_delay = 60
        self.wave_active = False
        self.wave_completed = False
        self.completion_timer = 0  # Para controlar la transición
        
    def start_wave(self):
        """Inicia oleada sin bloquear"""
        self.wave_active = True
        self.wave_completed = False
        self.enemies_spawned = 0
        self.enemies_in_wave = ENEMIES_PER_WAVE + (self.current_wave - 1) * 3
        self.spawn_timer = 0
        self.completion_timer = 0
        
        # Dificultad progresiva
        self.spawn_delay = max(20, 60 - self.current_wave * 3)
    
    def update(self, enemies):
        """Actualiza sin bloqueos"""
        if not self.wave_active:
            # Manejar transición entre oleadas
            if self.wave_completed:
                self.completion_timer += 1
                if self.completion_timer >= 120:  # 2 segundos sin bloquear
                    self.wave_completed = False
                    self.completion_timer = 0
                    self.start_wave()
            return None
        
        # Spawn de enemigos
        if self.enemies_spawned < self.enemies_in_wave:
            self.spawn_timer += 1
            
            if self.spawn_timer >= self.spawn_delay:
                self.spawn_timer = 0
                self.enemies_spawned += 1
                
                speed_mult = 1.0 + (self.current_wave - 1) * 0.1
                return Enemy.spawn_random(speed_mult, self.current_wave)
        
        # Verificar fin de oleada
        elif len(enemies) == 0:
            self.wave_active = False
            self.wave_completed = True
            self.current_wave += 1
        
        return None
    
    def is_wave_completed(self):
        return self.wave_completed
    
    def get_completion_progress(self):
        """Retorna progreso de transición (0-1)"""
        if not self.wave_completed:
            return 0
        return min(1.0, self.completion_timer / 120)
    
    def reset(self):
        self.current_wave = 1
        self.enemies_in_wave = ENEMIES_PER_WAVE
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_completed = False
        self.completion_timer = 0