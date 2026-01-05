"""
Configuraciones globales del juego
"""

# Ventana
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

# Configuración del Mundo
WORLD_WIDTH = 2400  # 3x ancho pantalla
WORLD_HEIGHT = 1800 # 3x alto pantalla

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
PLAYER_SPEED = 5
PLAYER_COLOR = GREEN
PLAYER_MAX_HEALTH = 100

# Enemigos
ENEMY_SIZE = 15
ENEMY_SPEED = 2
ENEMY_COLOR = RED
ENEMY_DAMAGE = 10
ENEMY_SPAWN_RATE = 2  # segundos

# Juego
INITIAL_WAVE = 1
ENEMIES_PER_WAVE = 5