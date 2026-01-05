"""
Gestor de oleadas de enemigos
"""
import pygame
from entities.enemy import Enemy
from settings import ENEMIES_PER_WAVE

class WaveManager:
    def __init__(self):
        self.current_wave = 1
        self.enemies_in_wave = ENEMIES_PER_WAVE
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.spawn_delay = 60  # frames entre spawns (1 segundo)
        self.wave_active = False
        self.wave_completed = False
        
    def start_wave(self):
        """Inicia una nueva oleada"""
        self.wave_active = True
        self.wave_completed = False
        self.enemies_spawned = 0
        self.enemies_in_wave = ENEMIES_PER_WAVE + (self.current_wave - 1) * 3
        self.spawn_timer = 0
        
        # Aumentar dificultad gradualmente
        self.spawn_delay = max(20, 60 - self.current_wave * 3)
    
    def update(self, enemies):
        """Actualiza el estado de la oleada"""
        if not self.wave_active:
            return None
        
        # Spawneo de enemigos
        if self.enemies_spawned < self.enemies_in_wave:
            self.spawn_timer += 1
            
            if self.spawn_timer >= self.spawn_delay:
                self.spawn_timer = 0
                self.enemies_spawned += 1
                
                # Calcular multiplicador de velocidad basado en oleada
                speed_mult = 1.0 + (self.current_wave - 1) * 0.1
                return Enemy.spawn_random(speed_mult)
        
        # Verificar si la oleada terminó
        elif len(enemies) == 0:
            self.wave_active = False
            self.wave_completed = True
            self.current_wave += 1
        
        return None
    
    def is_wave_completed(self):
        """Retorna si la oleada actual terminó"""
        return self.wave_completed
    
    def reset_wave_completion(self):
        """Resetea el estado de oleada completada"""
        self.wave_completed = False
    
    def reset(self):
        """Reinicia el gestor de oleadas"""
        self.current_wave = 1
        self.enemies_in_wave = ENEMIES_PER_WAVE
        self.enemies_spawned = 0
        self.spawn_timer = 0
        self.wave_active = False
        self.wave_completed = False