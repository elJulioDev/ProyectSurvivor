"""
Camera con soporte de zoom y delta-time CORRECTO.

Correcciones vs versión anterior:
  - update() acepta `dt` (float, default 1.0) — antes ignoraba el FPS real.
  - Lerp frame-rate independent:  lerp_dt = 1 - (1 - lerp_speed)^dt
      · A dt=1.0 (60fps):  lerp_dt = 0.08        (igual que antes)
      · A dt=0.5 (120fps): lerp_dt ≈ 0.041       (la mitad por frame, pero
        se aplica el doble de veces → mismo seguimiento real por segundo)
      · A dt=2.0 (30fps):  lerp_dt ≈ 0.1536      (más grande, pero la mitad
        de frames → mismo resultado)
  - Shake decay frame-rate independent:  intensity *= decay^dt
      · Antes a 120fps el temblor desaparecía en la mitad del tiempo real.
"""
import pygame, random
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

_CW = WINDOW_WIDTH
_CH = WINDOW_HEIGHT

class Camera:
    def __init__(self, width: int, height: int, zoom: float = 1.0):
        self.width  = width
        self.height = height
        self.zoom   = zoom

        # Posición del mundo en el centro de la pantalla (lerpeada)
        self.center_x: float = float(width  // 2)
        self.center_y: float = float(height // 2)

        self.lerp_speed      = 0.08
        self.culling_margin  = 120
        self.shake_intensity = 0.0
        self.shake_decay     = 0.88
        self._shake_x        = 0.0
        self._shake_y        = 0.0

        # Offsets legados — se recalculan cada frame
        self.offset_x = 0
        self.offset_y = 0
        self.camera   = pygame.Rect(0, 0, width, height)

        # Culling bounds en espacio de pantalla
        self._cx_min = 0
        self._cx_max = _CW
        self._cy_min = 0
        self._cy_max = _CH

        self._update_offsets()
        self._update_culling_bounds()

    def snap_to(self, target) -> None:
        self.center_x = float(target.rect.centerx)
        self.center_y = float(target.rect.centery)
        self._shake_x = 0.0
        self._shake_y = 0.0
        self._clamp_center()
        self._update_offsets()
        self._update_culling_bounds()

    def add_shake(self, amount: float) -> None:
        self.shake_intensity = min(self.shake_intensity + amount, 20.0)

    def is_on_screen(self, rect) -> bool:
        z  = self.zoom
        sx = (rect.x - self.center_x) * z + _CW * 0.5 + self._shake_x
        sy = (rect.y - self.center_y) * z + _CH * 0.5 + self._shake_y
        sw = rect.width  * z
        sh = rect.height * z
        m  = self.culling_margin
        return (sx < _CW + m and sx + sw > -m and
                sy < _CH + m and sy + sh > -m)

    def is_point_on_screen(self, x: float, y: float) -> bool:
        z  = self.zoom
        sx = (x - self.center_x) * z + _CW * 0.5 + self._shake_x
        sy = (y - self.center_y) * z + _CH * 0.5 + self._shake_y
        m  = self.culling_margin
        return (-m < sx < _CW + m and -m < sy < _CH + m)

    def apply_coords(self, x, y):
        z = self.zoom
        sx = (x - self.center_x) * z + _CW * 0.5 + self._shake_x
        sy = (y - self.center_y) * z + _CH * 0.5 + self._shake_y
        return (sx, sy)

    def apply(self, entity):
        return entity.rect.move(self.offset_x, self.offset_y)

    def apply_rect(self, rect):
        return rect.move(self.offset_x, self.offset_y)

    def update(self, target, mouse_pos=None, dt: float = 1.0) -> None:
        tx = float(target.rect.centerx)
        ty = float(target.rect.centery)

        # Paralaje del ratón dividido por zoom para no exagerar en mobile
        if mouse_pos:
            z  = max(self.zoom, 0.01)
            mx = (mouse_pos[0] - _CW * 0.5) / z
            my = (mouse_pos[1] - _CH * 0.5) / z
            tx += mx * 0.4
            ty += my * 0.4

        # ── Lerp frame-rate independent ─────────────────────────────────
        # Fórmula: lerp_dt = 1 - (1 - lerp_speed)^dt
        #   · Garantiza que la cámara recorra la misma fracción de la
        #     distancia al target POR SEGUNDO de tiempo real, sin importar FPS.
        #   · A 60fps (dt=1.0):  lerp_dt = 0.08  (sin cambio)
        #   · A 120fps (dt=0.5): lerp_dt ≈ 0.041 (la mitad por frame,
        #     el doble de frames → igual por segundo real)
        lerp_dt = 1.0 - (1.0 - self.lerp_speed) ** dt
        self.center_x += (tx - self.center_x) * lerp_dt
        self.center_y += (ty - self.center_y) * lerp_dt
        self._clamp_center()

        # ── Shake frame-rate independent ─────────────────────────────────
        # decay^dt garantiza el mismo tiempo de extinción a cualquier FPS.
        #   · Antes: a 120fps el temblor desaparecía en la mitad del tiempo real.
        self._shake_x = self._shake_y = 0.0
        if self.shake_intensity > 0.1:
            self._shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self._shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay ** dt
            if self.shake_intensity < 0.1:
                self.shake_intensity = 0.0

        self._update_offsets()
        self._update_culling_bounds()

    def _clamp_center(self) -> None:
        """Con zoom z, la región visible del mundo mide CW/(2z) a cada lado."""
        z      = self.zoom
        half_w = _CW * 0.5 / z
        half_h = _CH * 0.5 / z
        self.center_x = max(half_w, min(self.width  - half_w, self.center_x))
        self.center_y = max(half_h, min(self.height - half_h, self.center_y))

    def _update_offsets(self) -> None:
        self.offset_x = int(-self.center_x * self.zoom + _CW * 0.5 + self._shake_x)
        self.offset_y = int(-self.center_y * self.zoom + _CH * 0.5 + self._shake_y)
        self.camera   = pygame.Rect(
            self.offset_x, self.offset_y,
            int(self.width  * self.zoom),
            int(self.height * self.zoom),
        )

    def _update_culling_bounds(self) -> None:
        m = self.culling_margin
        self._cx_min = -m
        self._cx_max = _CW + m
        self._cy_min = -m
        self._cy_max = _CH + m