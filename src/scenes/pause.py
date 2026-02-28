"""
Escena de Pausa — escena independiente (como UpgradeScene).
Renderiza el gameplay congelado de fondo y superpone el panel de pausa.
"""
import pygame
import math
import sys
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

_C_BG         = (6,   7,  10)
_C_PANEL      = (12,  14,  22)
_C_BORDER     = (40,  44,  62)
_C_BORDER_LIT = (70,  75, 110)
_C_RED        = (210,  30,  30)
_C_RED_DIM    = (100,  12,  12)
_C_CYAN       = (0,  200, 215)
_C_WHITE      = (230, 232, 238)
_C_GRAY       = (90,  92, 105)


def _sa(w: int, h: int) -> pygame.Surface:
    return pygame.Surface((w, h), pygame.SRCALPHA)

_PANEL_W = 360
_PANEL_H = 390
_PANEL_X = WINDOW_WIDTH  // 2 - _PANEL_W // 2   # 460
_PANEL_Y = WINDOW_HEIGHT // 2 - _PANEL_H // 2   # 165

# Botones: ancho, posición X centrada, separación
_BTN_W   = 300
_BTN_H   = 62
_BTN_GAP = 14
_BTN_CX  = WINDOW_WIDTH // 2

# Primer botón arranca justo bajo el título + separador
_BTN_Y0  = _PANEL_Y + 118          # 283
_BTN_Y1  = _BTN_Y0 + _BTN_H + _BTN_GAP   # 359
_BTN_Y2  = _BTN_Y1 + _BTN_H + _BTN_GAP   # 435


class _PauseButton:
    """Botón táctil para el menú de pausa."""

    RADIUS = 10

    def __init__(self, cx: int, y: int, width: int, label: str,
                 accent=_C_RED, font_size: int = 34) -> None:
        self.rect = pygame.Rect(0, 0, width, _BTN_H)
        self.rect.centerx = cx
        self.rect.y = y
        self.label  = label
        self.accent = accent
        self.font   = pygame.font.Font(None, font_size)
        self.hover  = False
        self._sc    = 1.0
        self._gl    = 0.0

    def update(self, mouse_pos: tuple, dt: float = 1.0) -> None:
        self.hover = self.rect.inflate(16, 16).collidepoint(mouse_pos)
        t_sc = 1.015 if self.hover else 1.0
        t_gl = 1.0   if self.hover else 0.0
        spd  = 0.14 * dt
        self._sc += (t_sc - self._sc) * spd * 3
        self._gl += (t_gl - self._gl) * spd * 2

    def hit(self, vpos: tuple) -> bool:
        return self.rect.inflate(16, 16).collidepoint(vpos)

    def draw(self, screen: pygame.Surface) -> None:
        w = int(self.rect.width  * self._sc)
        h = int(self.rect.height * self._sc)
        x = self.rect.centerx - w // 2
        y = self.rect.centery - h // 2

        # Sombra
        sh = _sa(w + 16, h + 16)
        pygame.draw.rect(sh, (0, 0, 0, 80),
                         (0, 0, w + 16, h + 16), border_radius=self.RADIUS + 4)
        screen.blit(sh, (x - 4, y + 6))

        # Glow
        if self._gl > 0.05:
            gs = _sa(w + 40, h + 40)
            pygame.draw.rect(gs, (*self.accent, int(self._gl * 50)),
                             (0, 0, w + 40, h + 40), border_radius=self.RADIUS + 8)
            screen.blit(gs, (x - 20, y - 20))

        # Fondo
        bg = _sa(w, h)
        bc = (
            min(255, _C_PANEL[0] + int(self._gl * 14)),
            min(255, _C_PANEL[1] + int(self._gl * 14)),
            min(255, _C_PANEL[2] + int(self._gl * 24)),
        )
        pygame.draw.rect(bg, (*bc, 220), (0, 0, w, h), border_radius=self.RADIUS)
        screen.blit(bg, (x, y))

        # Marca lateral de color
        mk = _sa(5, h - 16)
        pygame.draw.rect(mk, (*self.accent, 240), (0, 0, 5, h - 16), border_radius=3)
        screen.blit(mk, (x + 6, y + 8))

        # Borde
        bd = _sa(w, h)
        bd_c   = self.accent if self.hover else _C_BORDER_LIT
        bd_a   = 220 if self.hover else 140
        pygame.draw.rect(bd, (*bd_c, bd_a), (0, 0, w, h), 2, border_radius=self.RADIUS)
        screen.blit(bd, (x, y))

        # Texto
        tc   = _C_WHITE if self.hover else (175, 178, 192)
        shd  = self.font.render(self.label, True, (0, 0, 0))
        surf = self.font.render(self.label, True, tc)
        tx = x + w // 2 - surf.get_width() // 2
        ty = y + h // 2 - surf.get_height() // 2
        screen.blit(shd,  (tx + 2, ty + 2))
        screen.blit(surf, (tx, ty))


class PauseScene(Scene):
    """
    Escena de pausa independiente.
    Toma el gameplay_scene como referencia para:
      · Renderizar el juego congelado en el fondo.
      · Volver a él al continuar.
    """

    def __init__(self, game, gameplay_scene) -> None:
        super().__init__(game)
        self.gameplay_scene = gameplay_scene

        # Fuentes
        self.f_title = pygame.font.Font(None, 82)
        self.f_hint  = pygame.font.Font(None, 26)

        # Botones
        self.btn_continue = _PauseButton(
            _BTN_CX, _BTN_Y0, _BTN_W,
            "  CONTINUAR",
            accent=_C_CYAN, font_size=36
        )
        self.btn_menu = _PauseButton(
            _BTN_CX, _BTN_Y1, _BTN_W,
            "  MENÚ PRINCIPAL",
            accent=(70, 75, 110), font_size=30
        )
        self.btn_exit = _PauseButton(
            _BTN_CX, _BTN_Y2, _BTN_W,
            "  SALIR DEL JUEGO",
            accent=_C_RED_DIM, font_size=28
        )

        # Animación del título
        self._timer  = 0.0

        # Superficie de cuadrícula reutilizable
        self._grid   = self._build_grid()

    @staticmethod
    def _build_grid() -> pygame.Surface:
        s = _sa(WINDOW_WIDTH, WINDOW_HEIGHT)
        gs = 60
        for x in range(0, WINDOW_WIDTH, gs):
            pygame.draw.line(s, (255, 255, 255, 6), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, gs):
            pygame.draw.line(s, (255, 255, 255, 6), (0, y), (WINDOW_WIDTH, y))
        return s

    def on_enter(self) -> None:
        pygame.mouse.set_visible(True)

    def _vpos(self, event) -> tuple:
        if hasattr(event, 'pos'):
            rx, ry = event.pos
            scale  = max(0.001, self.game.render_scale)
            return (
                (rx - self.game.render_offset_x) / scale,
                (ry - self.game.render_offset_y) / scale,
            )
        return self.game.get_mouse_pos()

    def handle_events(self, event: pygame.event.Event) -> None:
        vpos      = self._vpos(event)
        mouse_pos = self.game.get_mouse_pos()

        self.btn_continue.update(mouse_pos)
        self.btn_menu.update(mouse_pos)
        self.btn_exit.update(mouse_pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_continue.hit(vpos):
                self._do_continue()
                return
            if self.btn_menu.hit(vpos):
                self._do_menu()
                return
            if self.btn_exit.hit(vpos):
                pygame.quit()
                sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self._do_continue()

    def _do_continue(self) -> None:
        pygame.mouse.set_visible(self.gameplay_scene.mobile.enabled)
        self.game.current_scene = self.gameplay_scene

    def _do_menu(self) -> None:
        pygame.mouse.set_visible(True)
        from scenes.menu import MenuScene
        self.next_scene = MenuScene(self.game)

    def update(self) -> None:
        self._timer += 1.0
        mouse_pos = self.game.get_mouse_pos()
        self.btn_continue.update(mouse_pos)
        self.btn_menu.update(mouse_pos)
        self.btn_exit.update(mouse_pos)

        # Si la siguiente escena fue asignada (menú), propagar
        # (el motor la leerá en game.update)

    def render(self) -> None:
        # 1. Fondo: gameplay congelado
        self.gameplay_scene.render()

        # 2. Overlay oscuro semitransparente
        ov = _sa(WINDOW_WIDTH, WINDOW_HEIGHT)
        ov.fill((0, 0, 8, 195))
        self.screen.blit(ov, (0, 0))

        # 3. Cuadrícula sutil
        self.screen.blit(self._grid, (0, 0))

        # 4. Panel central
        self._draw_panel()

        # 5. Título animado
        self._draw_title()

        # 6. Separador
        self._draw_separator()

        # 7. Botones
        self.btn_continue.draw(self.screen)
        self.btn_menu.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # 8. Hint de teclado
        self._draw_hint()

    def _draw_panel(self) -> None:
        px, py = _PANEL_X, _PANEL_Y
        pw, ph = _PANEL_W, _PANEL_H

        # Sombra del panel
        sh = _sa(pw + 24, ph + 24)
        pygame.draw.rect(sh, (0, 0, 0, 110),
                         (0, 0, pw + 24, ph + 24), border_radius=14)
        self.screen.blit(sh, (px - 8, py + 12))

        # Fondo
        bg = _sa(pw, ph)
        pygame.draw.rect(bg, (*_C_PANEL, 235), (0, 0, pw, ph), border_radius=12)
        self.screen.blit(bg, (px, py))

        # Borde
        bd = _sa(pw, ph)
        pygame.draw.rect(bd, (*_C_BORDER_LIT, 180),
                         (0, 0, pw, ph), 1, border_radius=12)
        self.screen.blit(bd, (px, py))

        # Franja cian superior
        pygame.draw.line(
            self.screen, _C_CYAN,
            (px + 12, py + 1),
            (px + pw - 12, py + 1), 2
        )

    def _draw_title(self) -> None:
        beat    = abs(math.sin(self._timer * 0.04))
        c_beat  = (
            int(_C_CYAN[0] * 0.7 + beat * _C_CYAN[0] * 0.3),
            int(_C_CYAN[1] * 0.7 + beat * _C_CYAN[1] * 0.3),
            int(_C_CYAN[2] * 0.7 + beat * _C_CYAN[2] * 0.3),
        )
        cx = WINDOW_WIDTH  // 2
        ty = _PANEL_Y + 22

        sh = self.f_title.render("PAUSA", True, (0, 0, 0))
        ti = self.f_title.render("PAUSA", True, c_beat)
        tx = cx - ti.get_width() // 2
        self.screen.blit(sh, (tx + 3, ty + 3))
        self.screen.blit(ti, (tx, ty))

    def _draw_separator(self) -> None:
        sep_y = _PANEL_Y + 108
        pygame.draw.line(
            self.screen, _C_BORDER,
            (_PANEL_X + 20, sep_y),
            (_PANEL_X + _PANEL_W - 20, sep_y), 1
        )

    def _draw_hint(self) -> None:
        hint = self.f_hint.render("ESC / ENTER  para continuar", True, (40, 42, 58))
        hx   = WINDOW_WIDTH  // 2 - hint.get_width() // 2
        hy   = _PANEL_Y + _PANEL_H + 12
        self.screen.blit(hint, (hx, hy))