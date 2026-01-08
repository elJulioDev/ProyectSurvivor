"""
Configuraciones globales del juego
"""

# CONFIGURACIÓN DE PANTALLA
# Resolución INTERNA (Diseño del juego)
# Usaremos 1280x720 (HD) como base. Esto hará que los sprites se vean más grandes.
BASE_WIDTH = 1280
BASE_HEIGHT = 720

# Resolución INICIAL de la ventana (Lo que ve el usuario al abrir)
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Configuración del Mundo
WORLD_WIDTH = 2400
WORLD_HEIGHT = 1800

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

CROSSHAIR_COLOR = (255, 255, 255)
CROSSHAIR_SIZE = 6       # Largo de las líneas
CROSSHAIR_GAP = 4        # Espacio entre el punto central y las líneas
CROSSHAIR_THICKNESS = 2  # Grosor de las líneas
CROSSHAIR_DOT_SIZE = 2   # Tamaño del punto central (2x2 px se ve mejor que 1x1)