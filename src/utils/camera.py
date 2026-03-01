"""
Camera con soporte de zoom.
  zoom > 1.0  →  vista más cercana (modo mobile: MOBILE_CAMERA_ZOOM)
  zoom = 1.0  →  comportamiento original (desktop)

Cambios respecto a la versión anterior:
  - Nuevo atributo: self.zoom   (float, default 1.0)
  - center_x / center_y  rastrean la posición mundo del centro de cámara
  - apply_coords()        tiene en cuenta el zoom
  - is_on_screen()        tiene en cuenta el zoom
  - is_point_on_screen()  ídem
  - _clamp_center()       limita al borde del mundo con zoom correcto
  - offset_x / offset_y   se mantienen actualizados para código legacy
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
        # Con zoom=1: offset_x = -center_x + _CW/2  (idéntico al original)
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

    def update(self, target, mouse_pos=None) -> None:
        tx = float(target.rect.centerx)
        ty = float(target.rect.centery)

        # Paralaje del ratón dividido por zoom para no exagerar en mobile
        if mouse_pos:
            z  = max(self.zoom, 0.01)
            mx = (mouse_pos[0] - _CW * 0.5) / z
            my = (mouse_pos[1] - _CH * 0.5) / z
            tx += mx * 0.4
            ty += my * 0.4

        ls = self.lerp_speed
        self.center_x += (tx - self.center_x) * ls
        self.center_y += (ty - self.center_y) * ls
        self._clamp_center()

        self._shake_x = self._shake_y = 0.0
        if self.shake_intensity > 0.1:
            self._shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            self._shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay

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
        """
        Mantiene offset_x/y legados que usan spawn_manager, _render_grid, etc.
        Derivación: apply_coords(0,0) = (-center_x*z + CW/2 + shake, ...)
        """
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