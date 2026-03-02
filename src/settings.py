"""
Configuraciones globales del juego.

CAMBIO DE RENDIMIENTO:
  WORLD_WIDTH / WORLD_HEIGHT reducidos de 12000×9000 a 6000×4500.

  ¿Por qué?
  · Los enemigos siempre spawnean en un radio de 650-1100 px alrededor
    del jugador → el jugador nunca necesita recorrer el mundo completo.
  · La SpatialGrid mejora: de ~10 800 celdas a ~2 700 celdas (×4 más rápida).
  · El cálculo de teleport de enemigos (TELEPORT_DISTANCE) sigue funcionando.
  · Con ChunkManager, la capa de sangre ya no depende del tamaño del mundo.
"""

# CONFIGURACIÓN DE PANTALLA
BASE_WIDTH = 1280
BASE_HEIGHT = 720
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720

# Mundo: reducido de 12000×9000 a 6000×4500
# (los enemigos spawnean circulares alrededor del jugador, así que
#  el tamaño del mundo solo afecta a los bordes y a la SpatialGrid)
WORLD_WIDTH  = 6000   # era: 2400 * 5 = 12 000
WORLD_HEIGHT = 4500   # era: 1800 * 5 =  9 000

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
CROSSHAIR_SIZE = 6
CROSSHAIR_GAP = 4
CROSSHAIR_THICKNESS = 2
CROSSHAIR_DOT_SIZE = 2

MOBILE_CAMERA_ZOOM = 1.6

# SISTEMA DE MEJORAS — Categorías, Rarezas y Stats expandidos
# type:        'stat' | 'weapon' | 'xp' | 'unlock' | 'unlock_weapon'
# rarity:      'common' | 'uncommon' | 'rare' | 'epic' | 'legendary'
# category:    'movement' | 'survival' | 'weapons' | 'xp'
# stackable:   Si puede elegirse más de una vez
# max_stacks:  Límite de veces que puede acumularse (None = sin límite)
# requires:    Condición para que aparezca:
#                'dash_unlocked'   → player.dash_unlocked == True
#                'aura_unlocked'   → player.aura_damage > 0
#                'ninja_dash_ready'→ dash desbloqueado + dash_cooldown al máximo (3 stacks)

UPGRADES = {

    # MOVIMIENTO
    'dash': {
        'name': 'Dash Tactico',
        'desc': 'Desbloquea el Dash (Ctrl). Atraviesa la horda y esquiva en el ultimo segundo.',
        'type': 'unlock',
        'rarity': 'rare',
        'category': 'movement',
    },
    'speed': {
        'name': 'Adrenalina',
        'desc': '+12% velocidad de movimiento (velocidad real y aceleracion). Apilable.',
        'type': 'stat',
        'stat_name': 'max_speed',
        'value': 1.12,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'common',
        'category': 'movement',
    },
    'dash_cooldown': {
        'name': 'Carga Rapida',
        'desc': '-25% tiempo de recarga del Dash. Mas escapadas, menos mordidas.',
        'type': 'stat',
        'stat_name': 'dash_cooldown',
        'value': 0.75,
        'stackable': True,
        'max_stacks': 3,
        'requires': 'dash_unlocked',
        'rarity': 'uncommon',
        'category': 'movement',
    },
    'dash_duration': {
        'name': 'Dash Prolongado',
        'desc': 'El Dash recorre un 40% mas de distancia. Cruza grupos enteros de zombies.',
        'type': 'stat',
        'stat_name': 'dash_duration',
        'value': 1.4,
        'stackable': False,
        'requires': 'dash_unlocked',
        'rarity': 'rare',
        'category': 'movement',
    },

    # ARTES OSCURAS — habilidad Ninja del Dash
    'ninja_dash': {
        'name': 'Artes Oscuras',
        'desc': (
            'El Dash atraviesa y MATA INSTANTANEAMENTE a los zombies en tu camino. '
            'Requiere Dash desbloqueado y Carga Rapida al maximo.'
        ),
        'type': 'stat',
        'stat_name': 'ninja_dash',
        'value': True,
        'stackable': False,
        'requires': 'ninja_dash_ready',
        'rarity': 'legendary',
        'category': 'movement',
    },

    # SUPERVIVENCIA
    'health': {
        'name': 'Vitalidad',
        'desc': '+25 HP maximo. Mas margen para errores contra la horda.',
        'type': 'stat',
        'stat_name': 'max_health',
        'value': 25,
        'stackable': True,
        'rarity': 'common',
        'category': 'survival',
    },
    'regen': {
        'name': 'Regeneracion',
        'desc': '+0.8 HP por segundo. Recuperate pasivamente entre enfrentamientos.',
        'type': 'stat',
        'stat_name': 'health_regen',
        'value': 0.8,
        'stackable': True,
        'rarity': 'uncommon',
        'category': 'survival',
    },
    'armor': {
        'name': 'Armadura',
        'desc': '-10% al daño recibido. Cada punto de vida importa cuando hay cientos de zombies.',
        'type': 'stat',
        'stat_name': 'damage_reduction',
        'value': 0.10,
        'stackable': True,
        'max_stacks': 5,
        'rarity': 'uncommon',
        'category': 'survival',
    },
    'lifesteal': {
        'name': 'Vampirismo',
        'desc': '25% de probabilidad de recuperar 5 HP al matar un zombie. Apilable hasta 100%.',
        'type': 'stat',
        'stat_name': 'lifesteal_chance',
        'value': 0.25,
        'stackable': True,
        'max_stacks': 4,
        'rarity': 'rare',
        'category': 'survival',
    },
    'emergency_regen': {
        'name': 'Segundo Aliento',
        'desc': '+5 HP/s adicional cuando tu vida baja del 25%. Un seguro de vida.',
        'type': 'stat',
        'stat_name': 'emergency_regen',
        'value': 5.0,
        'stackable': False,
        'rarity': 'epic',
        'category': 'survival',
    },
    'iframes': {
        'name': 'Esquiva Fantasma',
        'desc': '+60% duracion de invulnerabilidad tras recibir daño. Mas tiempo para reaccionar.',
        'type': 'stat',
        'stat_name': 'invulnerable_mult',
        'value': 1.6,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'uncommon',
        'category': 'survival',
    },
    'max_health_big': {
        'name': 'Musculatura de Acero',
        'desc': '+60 HP maximo de golpe. Para quien prefiere absorber impactos.',
        'type': 'stat',
        'stat_name': 'max_health',
        'value': 60,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'rare',
        'category': 'survival',
    },

    # AURA DE ESPINAS
    'aura_espinas': {
        'name': 'Aura de Espinas',
        'desc': (
            'Genera un campo de energia violeta que inflige 12 DPS a todos los '
            'zombies cercanos. Radio base: 80px. Apilable para mas daño.'
        ),
        'type': 'stat',
        'stat_name': 'aura_damage',
        'value': 12.0,
        'stackable': True,
        'max_stacks': 5,
        'rarity': 'uncommon',
        'category': 'survival',
    },
    'aura_radio': {
        'name': 'Campo Expandido',
        'desc': (
            '+40px al radio del Aura de Espinas. Cubre mas terreno '
            'y elimina grupos densos mas facilmente.'
        ),
        'type': 'stat',
        'stat_name': 'aura_radius',
        'value': 40.0,
        'stackable': True,
        'max_stacks': 4,
        'requires': 'aura_unlocked',
        'rarity': 'uncommon',
        'category': 'survival',
    },
    'aura_sobrecarga': {
        'name': 'Sobrecarga del Aura',
        'desc': (
            'DUPLICA el daño del Aura de Espinas. Para builds que confian '
            'en el daño en area mas que en las armas.'
        ),
        'type': 'stat',
        'stat_name': 'aura_damage_mult',
        'value': 2.0,
        'stackable': False,
        'requires': 'aura_unlocked',
        'rarity': 'epic',
        'category': 'survival',
    },

    # ARMAS — GLOBALES
    'weapon_damage': {
        'name': 'Potencia de Fuego',
        'desc': '+15% daño de TODAS las armas. Afecta pistola, escopeta, rifle y laser.',
        'type': 'weapon',
        'stat_name': 'global_damage_mult',
        'value': 1.15,
        'stackable': True,
        'rarity': 'common',
        'category': 'weapons',
    },
    'weapon_damage_big': {
        'name': 'Calibre Mayor',
        'desc': '+30% daño de todas las armas. Una mejora masiva para todo tu arsenal.',
        'type': 'weapon',
        'stat_name': 'global_damage_mult',
        'value': 1.30,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'rare',
        'category': 'weapons',
    },
    'fire_rate': {
        'name': 'Cadencia',
        'desc': '+12% velocidad de disparo global. Mas plomo en menos tiempo.',
        'type': 'weapon',
        'stat_name': 'global_cooldown_mult',
        'value': 0.88,
        'stackable': True,
        'rarity': 'common',
        'category': 'weapons',
    },
    'fire_rate_big': {
        'name': 'Gatillo Mecanico',
        'desc': '+25% velocidad de disparo. El estruendo no para.',
        'type': 'weapon',
        'stat_name': 'global_cooldown_mult',
        'value': 0.75,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'rare',
        'category': 'weapons',
    },
    'projectile_speed': {
        'name': 'Balas Supersonicas',
        'desc': '+20% velocidad de todos los proyectiles. Mas dificil de esquivar para los zombies.',
        'type': 'weapon',
        'stat_name': 'projectile_speed_mult',
        'value': 1.2,
        'stackable': True,
        'max_stacks': 5,
        'rarity': 'common',
        'category': 'weapons',
    },
    'penetration': {
        'name': 'Municion Perforante',
        'desc': 'Los proyectiles atraviesan +1 zombie adicional. Elimina grupos apretados.',
        'type': 'weapon',
        'stat_name': 'extra_penetration',
        'value': 1,
        'stackable': True,
        'max_stacks': 4,
        'rarity': 'uncommon',
        'category': 'weapons',
    },
    'projectile_size': {
        'name': 'Balas Expansivas',
        'desc': '+5% tamaño visual de balas. Impacto mas visible sin alterar la precision.',
        'type': 'weapon',
        'stat_name': 'projectile_size_mult',
        'value': 1.05,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'uncommon',
        'category': 'weapons',
    },
    'knockback': {
        'name': 'Impacto Brutal',
        'desc': '+50% fuerza de retroceso al impactar zombies. Crea espacio cuando mas lo necesitas.',
        'type': 'weapon',
        'stat_name': 'knockback_mult',
        'value': 1.5,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'uncommon',
        'category': 'weapons',
    },

    # ARMAS — DESBLOQUEOS
    'unlock_shotgun': {
        'name': 'Escopeta',
        'desc': 'Desbloquea la escopeta (Tecla 2). 8 perdigones, devastadora a corto rango.',
        'type': 'unlock_weapon',
        'weapon_class': 'ShotgunWeapon',
        'rarity': 'rare',
        'category': 'weapons',
    },
    'unlock_rifle': {
        'name': 'Rifle de Asalto',
        'desc': 'Desbloquea el rifle (Tecla 3). Alta cadencia y buen daño sostenido.',
        'type': 'unlock_weapon',
        'weapon_class': 'AssaultRifleWeapon',
        'rarity': 'rare',
        'category': 'weapons',
    },
    'unlock_laser': {
        'name': 'Laser de Plasma',
        'desc': 'Desbloquea el laser (Tecla 4). Daño continuo masivo en linea recta.',
        'type': 'unlock_weapon',
        'weapon_class': 'LaserWeapon',
        'rarity': 'legendary',
        'category': 'weapons',
    },
    'unlock_sniper': {
        'name': 'Rifle de Caza',
        'desc': (
            'Desbloquea el Francotirador (Tecla 5). '
            'Maxima penetracion (8 zombies), 110 de daño por disparo, '
            'proyectil ultrarapido y preciso. Recarga lenta.'
        ),
        'type': 'unlock_weapon',
        'weapon_class': 'SniperWeapon',
        'rarity': 'epic',
        'category': 'weapons',
    },

    # XP Y GEMAS
    'xp_magnet': {
        'name': 'Iman de XP',
        'desc': '+40% radio de atraccion de gemas. Recoge experiencia desde mas lejos.',
        'type': 'xp',
        'stat_name': 'magnet_range_mult',
        'value': 1.4,
        'stackable': True,
        'max_stacks': 5,
        'rarity': 'common',
        'category': 'xp',
    },
    'xp_boost': {
        'name': 'Estudioso',
        'desc': '+25% experiencia obtenida de todas las fuentes. Sube de nivel mas rapido.',
        'type': 'xp',
        'stat_name': 'xp_mult',
        'value': 1.25,
        'stackable': True,
        'rarity': 'uncommon',
        'category': 'xp',
    },
    'xp_on_kill': {
        'name': 'Coleccionista',
        'desc': '+8 XP bonus directo por cada zombie eliminado. No necesitas recoger gema.',
        'type': 'xp',
        'stat_name': 'xp_on_kill_bonus',
        'value': 8,
        'stackable': True,
        'rarity': 'uncommon',
        'category': 'xp',
    },
    'magnet_speed': {
        'name': 'Tractor de Gemas',
        'desc': 'Las gemas vuelan un 60% mas rapido hacia ti. Recoleccion casi instantanea.',
        'type': 'xp',
        'stat_name': 'magnet_speed_mult',
        'value': 1.6,
        'stackable': True,
        'max_stacks': 3,
        'rarity': 'uncommon',
        'category': 'xp',
    },
    'xp_magnet_huge': {
        'name': 'Campo Magnetico',
        'desc': 'DUPLICA el radio de atraccion de gemas. Practicamente una aspiradora de XP.',
        'type': 'xp',
        'stat_name': 'magnet_range_mult',
        'value': 2.0,
        'stackable': False,
        'rarity': 'epic',
        'category': 'xp',
    },
    'xp_boost_big': {
        'name': 'Genio Tactico',
        'desc': '+50% experiencia obtenida. El camino rapido a las mejoras mas poderosas.',
        'type': 'xp',
        'stat_name': 'xp_mult',
        'value': 1.5,
        'stackable': True,
        'max_stacks': 2,
        'rarity': 'rare',
        'category': 'xp',
    },
}