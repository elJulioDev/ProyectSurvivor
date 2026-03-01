"""
Camera optimizada — sin asignación de Rect por is_on_screen().
is_on_screen() pasa de crear un Rect nuevo por enemigo a solo aritmética entera.
Con 800 enemigos esto elimina ~800 allocations/frame.
"""
import pygame, random
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

# Pre-computados para evitar lookups en el hot-path
_CW = WINDOW_WIDTH
_CH = WINDOW_HEIGHT

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width  = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0
        self.lerp_speed = 0.08
        self.true_scroll_x = 0.0
        self.true_scroll_y = 0.0
        self.culling_margin = 120
        self.shake_intensity = 0.0
        self.shake_decay     = 0.88

        # Pre-computados que se actualizan en update() para el hot-path
        self._cx_min = 0   # offset_x - culling_margin
        self._cx_max = 0   # offset_x + WINDOW_WIDTH  + culling_margin
        self._cy_min = 0
        self._cy_max = 0

    def snap_to(self, target):
        x = -target.rect.centerx + _CW // 2
        y = -target.rect.centery + _CH // 2
        x = min(0, max(-(self.width  - _CW), x))
        y = min(0, max(-(self.height - _CH), y))
        self.true_scroll_x = float(x)
        self.true_scroll_y = float(y)
        self.offset_x = x
        self.offset_y = y
        self.camera = pygame.Rect(x, y, self.width, self.height)
        self._update_culling_bounds()

    def is_on_screen(self, rect) -> bool:
        sx = rect.x + self.offset_x
        sy = rect.y + self.offset_y
        return (sx < self._cx_max and sx + rect.width  > self._cx_min and
                sy < self._cy_max and sy + rect.height > self._cy_min)

    # Versión con coordenadas explícitas (para proyectiles puntuales)
    def is_point_on_screen(self, x: float, y: float) -> bool:
        sx = x + self.offset_x
        sy = y + self.offset_y
        return (self._cx_min < sx < self._cx_max and
                self._cy_min < sy < self._cy_max)

    def apply_coords(self, x, y):
        return (x + self.offset_x, y + self.offset_y)

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def add_shake(self, amount: float):
        self.shake_intensity = min(self.shake_intensity + amount, 20.0)

    def update(self, target, mouse_pos=None):
        tx = -target.rect.centerx + _CW // 2
        ty = -target.rect.centery + _CH // 2

        if mouse_pos:
            mx = mouse_pos[0] - _CW * 0.5
            my = mouse_pos[1] - _CH * 0.5
            tx -= mx * 0.4
            ty -= my * 0.4

        ls = self.lerp_speed
        self.true_scroll_x += (tx - self.true_scroll_x) * ls
        self.true_scroll_y += (ty - self.true_scroll_y) * ls

        sx = sy = 0.0
        if self.shake_intensity > 0.1:
            sx = random.uniform(-self.shake_intensity, self.shake_intensity)
            sy = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay

        x = int(self.true_scroll_x + sx)
        y = int(self.true_scroll_y + sy)

        x = min(0, max(-(self.width  - _CW), x))
        y = min(0, max(-(self.height - _CH), y))

        self.offset_x = x
        self.offset_y = y
        self.camera = pygame.Rect(x, y, self.width, self.height)
        self._update_culling_bounds()

    def _update_culling_bounds(self):
        m = self.culling_margin
        self._cx_min = -m
        self._cx_max = _CW + m
        self._cy_min = -m
        self._cy_max = _CH + m