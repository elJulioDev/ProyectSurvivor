"""
Configuraciones globales del juego — v3

CAMBIOS DE BALANCE:
  Supervivencia:
    · 'health'        → max_stacks: 6 (antes ilimitado)
    · 'max_health_big'→ max_stacks: 2 (era 3), +50 HP (era +60)
    · 'regen'         → value: 0.5/s (era 0.8), max_stacks: 5
    · 'armor'         → max_stacks: 4 (era 5)
    · 'lifesteal'     → value: 0.20 (era 0.25), max_stacks: 3 (era 4)
    · 'iframes'       → value: 1.4 (era 1.6), max_stacks: 2 (era 3)
    · 'emergency_regen'→ value: 3.0 HP/s (era 5.0)

NUEVAS MEJORAS:
  Orbes Orbitales (requieren 'unlock_orbital'):
    · 'orbital_add_orb'   → +1 orbe (máx stack 3, total 4 orbes)
    · 'orbital_speed'     → +40% velocidad de rotación
    · 'orbital_range'     → +25px radio orbital
    · 'orbital_damage'    → +50% daño de los orbes

  Aura Repulsora (requiere 'aura_knockback_unlocked'):
    · 'aura_pulse_rapido' → -1s al intervalo de pulso (mín 1s, máx 3 stacks)
"""

# CONFIGURACIÓN DE PANTALLA
BASE_WIDTH = 1280
BASE_HEIGHT = 720
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

WORLD_WIDTH  = 12000
WORLD_HEIGHT = 9000

FPS = 60
TITLE = "ProyectSurvivor"

# Colores (RGB)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)

# Jugador
PLAYER_SIZE = 20
PLAYER_COLOR = WHITE
PLAYER_MAX_HEALTH = 100
PLAYER_SPEED = 6
PLAYER_ACCEL = 1
PLAYER_FRICTION = 0.85

# Enemigos
ENEMY_SIZE = 25
ENEMY_SPEED = 2

# Juego
ENEMIES_PER_WAVE = 5

CROSSHAIR_COLOR = WHITE
CROSSHAIR_SIZE = 6
CROSSHAIR_GAP = 4
CROSSHAIR_THICKNESS = 2
CROSSHAIR_DOT_SIZE = 2

MOBILE_CAMERA_ZOOM = 1.2