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

# ===== SISTEMA DE MEJORAS =====
UPGRADES = {
    # STATS DEL JUGADOR
    'dash': {
        'name': 'Dash Tactical',
        'desc': 'Desbloquea el dash (Ctrl)',
        'type': 'unlock',
        'rarity': 'rare'
    },
    'speed': {
        'name': 'Velocidad',
        'desc': '+10% velocidad de movimiento',
        'type': 'stat',
        'stat_name': 'max_speed',
        'value': 1.1,
        'stackable': True
    },
    'health': {
        'name': 'Vitalidad',
        'desc': '+20 HP máximo',
        'type': 'stat',
        'stat_name': 'max_health',
        'value': 20,
        'stackable': True
    },
    'regen': {
        'name': 'Regeneración',
        'desc': '+0.5 HP/segundo',
        'type': 'stat',
        'stat_name': 'health_regen',
        'value': 0.5,
        'stackable': True
    },
    
    # ARMAS
    'weapon_damage': {
        'name': 'Fuerza',
        'desc': '+15% daño de armas',
        'type': 'weapon',
        'stat_name': 'global_damage_mult',
        'value': 1.15,
        'stackable': True
    },
    'fire_rate': {
        'name': 'Cadencia',
        'desc': '+10% velocidad de disparo',
        'type': 'weapon',
        'stat_name': 'global_cooldown_mult',
        'value': 0.9,
        'stackable': True
    },
    'unlock_shotgun': {
        'name': 'Escopeta',
        'desc': 'Desbloquea la escopeta (Tecla 2)',
        'type': 'unlock_weapon',
        'weapon_class': 'ShotgunWeapon',
        'rarity': 'rare'
    },
    'unlock_rifle': {
        'name': 'Rifle de Asalto',
        'desc': 'Desbloquea el rifle (Tecla 3)',
        'type': 'unlock_weapon',
        'weapon_class': 'AssaultRifleWeapon',
        'rarity': 'rare'
    },
    'unlock_laser': {
        'name': 'Láser',
        'desc': 'Desbloquea el láser (Tecla 4)',
        'type': 'unlock_weapon',
        'weapon_class': 'LaserWeapon',
        'rarity': 'legendary'
    }
}
