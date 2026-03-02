"""
ChunkManager — Sistema de chunks para sangre/decales del mundo.

¿Por qué existe esto?
  Antes: una sola Surface SRCALPHA del tamaño de la ventana que se
  desplazaba cada frame al mover la cámara → memoria fija, scroll costoso.

  Ahora: el mundo se divide en cuadrados de CHUNK_SIZE × CHUNK_SIZE px
  (coordenadas de mundo). Cada chunk tiene su propia Surface SRCALPHA
  donde se hornean las partículas de sangre estáticas.

  Ventajas:
  · Solo existen chunks que el jugador ha visitado → sin RAM desperdiciada.
  · Solo se renderizan los 4-9 chunks visibles → pocos blits por frame.
  · Al alejarse, los chunks lejanos se eliminan → GC automático de RAM.
  · Sin scroll de superficie: la cámara transforma las coordenadas normalmente.

Integración:
  · LevelManager instancia ChunkManager en initialize().
  · ParticlePool.update_and_bake() recibe chunk_manager en lugar de blood_surface.
  · LevelManager.render_world() llama a chunk_manager.render(screen, camera).
  · LevelManager.update() llama a chunk_manager.update_active_chunks(camera)
    cada CHUNK_UPDATE_INTERVAL frames.
"""

import pygame
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

# Configuración
CHUNK_SIZE          = 1000   # px de mundo por lado del chunk
ACTIVE_MARGIN       = 1      # chunks extra de margen visible (cada dirección)
EVICT_MARGIN        = 2      # chunks de margen antes de liberar del todo
CHUNK_UPDATE_INTERVAL = 20   # frames entre actualizaciones de chunks activos


class Chunk:
    """Un cuadrado de CHUNK_SIZE×CHUNK_SIZE del mundo con su capa de sangre."""
    __slots__ = ('cx', 'cy', 'world_x', 'world_y', 'size',
                 'surface', 'dirty', '_scaled', '_cached_zoom')

    def __init__(self, cx: int, cy: int, size: int):
        self.cx      = cx
        self.cy      = cy
        self.size    = size
        self.world_x = cx * size   # esquina superior-izquierda en coords de mundo
        self.world_y = cy * size
        # Surface SRCALPHA vacía — se rellena on-demand con sangre horneada
        self.surface = pygame.Surface((size, size), pygame.SRCALPHA)
        self.dirty   = False       # True → hay que reescalar antes de renderizar
        self._scaled      : pygame.Surface | None = None
        self._cached_zoom : float = 0.0


class ChunkManager:
    """
    Gestiona la colección de chunks de decales del mundo.

    Uso básico:
        cm = ChunkManager(WORLD_WIDTH, WORLD_HEIGHT)

        # En update (cada N frames):
        cm.update_active_chunks(camera)

        # Cuando una partícula muere y se hornea:
        cm.bake_particle(world_x, world_y, surf)

        # En render:
        cm.render(screen, camera)
    """

    def __init__(self, world_width: int, world_height: int,
                 chunk_size: int = CHUNK_SIZE):
        self.chunk_size   = chunk_size
        self.world_width  = world_width
        self.world_height = world_height
        # Número máximo de índices de chunk en cada eje
        self.max_cx = world_width  // chunk_size + 1
        self.max_cy = world_height // chunk_size + 1

        self.chunks      : dict[tuple[int, int], Chunk] = {}
        self.active_keys : set[tuple[int, int]]         = set()

        # Contador interno para limitar la frecuencia de update_active_chunks
        self._frame_counter = 0

    def get_chunk_at(self, world_x: float, world_y: float) -> 'Chunk | None':
        """
        Retorna el chunk que contiene (world_x, world_y).
        Lo crea si es la primera vez que se accede a esa zona.
        Retorna None si las coordenadas están fuera del mundo.
        """
        cx = int(world_x // self.chunk_size)
        cy = int(world_y // self.chunk_size)
        if cx < 0 or cy < 0 or cx > self.max_cx or cy > self.max_cy:
            return None
        key = (cx, cy)
        if key not in self.chunks:
            self.chunks[key] = Chunk(cx, cy, self.chunk_size)
        return self.chunks[key]

    def bake_particle(self, world_x: float, world_y: float,
                      surf: pygame.Surface) -> None:
        """
        Hornea una partícula de sangre estática en la surface del chunk.
        Llamado por ParticlePool.update_and_bake() cuando la partícula se detiene.

        La posición dentro de la surface del chunk se calcula como:
            local_x = world_x - chunk.world_x
        """
        chunk = self.get_chunk_at(world_x, world_y)
        if chunk is None:
            return
        lx = int(world_x - chunk.world_x) - surf.get_width()  // 2
        ly = int(world_y - chunk.world_y) - surf.get_height() // 2
        chunk.surface.blit(surf, (lx, ly))
        chunk.dirty = True   # invalida el caché escalado

    def tick(self, camera) -> None:
        """
        Llamar UNA VEZ por frame en LevelManager.update().
        Actualiza los chunks activos cada CHUNK_UPDATE_INTERVAL frames.
        """
        self._frame_counter += 1
        if self._frame_counter >= CHUNK_UPDATE_INTERVAL:
            self._frame_counter = 0
            self.update_active_chunks(camera)

    def update_active_chunks(self, camera) -> None:
        """
        Recalcula el conjunto de chunks visibles y elimina los muy lejanos.
        Puede llamarse directamente si se desea forzar la actualización.
        """
        z      = max(camera.zoom, 0.01)
        half_w = WINDOW_WIDTH  / (2.0 * z)
        half_h = WINDOW_HEIGHT / (2.0 * z)
        cs     = self.chunk_size
        m      = ACTIVE_MARGIN

        # Rango de índices de chunk visibles (+margen)
        min_cx = max(0, int((camera.center_x - half_w) // cs) - m)
        max_cx = min(self.max_cx, int((camera.center_x + half_w) // cs) + m)
        min_cy = max(0, int((camera.center_y - half_h) // cs) - m)
        max_cy = min(self.max_cy, int((camera.center_y + half_h) // cs) + m)

        # Construir nuevo set activo, creando chunks si hacen falta
        new_active: set[tuple[int, int]] = set()
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                key = (cx, cy)
                new_active.add(key)
                if key not in self.chunks:
                    self.chunks[key] = Chunk(cx, cy, cs)

        # Eliminar chunks fuera del rango extendido (EVICT_MARGIN)
        evict_min_cx = min_cx - EVICT_MARGIN
        evict_max_cx = max_cx + EVICT_MARGIN
        evict_min_cy = min_cy - EVICT_MARGIN
        evict_max_cy = max_cy + EVICT_MARGIN

        to_remove = [
            key for key in list(self.chunks.keys())
            if key not in new_active and (
                key[0] < evict_min_cx or key[0] > evict_max_cx or
                key[1] < evict_min_cy or key[1] > evict_max_cy
            )
        ]
        for key in to_remove:
            del self.chunks[key]

        self.active_keys = new_active

    def render(self, screen: pygame.Surface, camera) -> None:
        """
        Renderiza todos los chunks activos sobre la pantalla.

        Si zoom == 1.0: blit directo (más rápido).
        Si zoom != 1.0: escala cada chunk; usa caché para no escalar cada frame
                        a menos que el chunk haya sido modificado (dirty).
        """
        z          = camera.zoom
        cs         = self.chunk_size
        use_zoom   = abs(z - 1.0) > 0.005
        scaled_dim = int(cs * z)

        for key in self.active_keys:
            chunk = self.chunks.get(key)
            if chunk is None:
                continue

            sx, sy = camera.apply_coords(chunk.world_x, chunk.world_y)
            ix, iy = int(sx), int(sy)

            # Culling rápido: descartar chunks totalmente fuera de pantalla
            draw_w = scaled_dim if use_zoom else cs
            draw_h = draw_w
            if ix > WINDOW_WIDTH  or iy > WINDOW_HEIGHT:
                continue
            if ix + draw_w < 0 or iy + draw_h < 0:
                continue

            if not use_zoom:
                screen.blit(chunk.surface, (ix, iy))
            else:
                # Reescalar solo si el contenido cambió o el zoom cambió
                if chunk.dirty or chunk._cached_zoom != z or chunk._scaled is None:
                    chunk._scaled      = pygame.transform.scale(
                        chunk.surface, (scaled_dim, scaled_dim)
                    )
                    chunk._cached_zoom = z
                    chunk.dirty        = False
                screen.blit(chunk._scaled, (ix, iy))

    def clear(self) -> None:
        """Borra todos los chunks — llamar en LevelManager.initialize()."""
        self.chunks.clear()
        self.active_keys.clear()
        self._frame_counter = 0

    def get_debug_info(self) -> dict:
        return {
            'chunks_total':  len(self.chunks),
            'chunks_active': len(self.active_keys),
            'chunk_size':    self.chunk_size,
        }