"""
Escena Game Over — Rediseñada
Botones grandes táctiles, sin depender del teclado.
Estética dark-industrial coherente con el menú principal.
"""
import pygame
import math
import random
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT

# ── Paleta (coherente con menu.py) ────────────────────────────────────────────
C_BG       = (6,   7,  10)
C_RED      = (210,  30,  30)
C_RED_DARK = (100,  10,  10)
C_RED_DIM  = (130,  15,  15)
C_CYAN     = (0,  210, 220)
C_CYAN_DIM = (0,   90, 100)
C_WHITE    = (230, 232, 238)
C_GRAY     = (90,  92, 105)
C_PANEL    = (14,  16,  24)
C_BORDER   = (40,  44,  62)
C_GOLD     = (255, 200,  40)
C_GOLD_DIM = (120,  85,  10)

def _sa(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


class _DebrisShard:
    """Fragmento que cae al inicio de la animación."""
    def __init__(self):
        self.x    = random.uniform(0, WINDOW_WIDTH)
        self.y    = random.uniform(-60, -10)
        self.vx   = random.uniform(-1.2, 1.2)
        self.vy   = random.uniform(1.0, 3.5)
        self.size = random.randint(2, 7)
        self.rot  = random.uniform(0, 360)
        self.vrot = random.uniform(-3, 3)
        r = random.random()
        self.color = C_RED if r < 0.4 else ((80, 0, 0) if r < 0.7 else (40, 42, 58))
        self.alpha = 240
        self.landed = False
        self.life   = 0
        self.max_life = random.randint(280, 520)

    def update(self, dt):
        if not self.landed:
            self.x   += self.vx  * dt
            self.y   += self.vy  * dt
            self.rot += self.vrot * dt
            self.vy  *= 1.004
            if self.y > WINDOW_HEIGHT * 0.85:
                self.landed = True
        else:
            self.life += dt
            self.alpha = int(max(0, 240 * (1 - self.life / self.max_life)))


class _StatBadge:
    """Tarjeta de estadística con animación de entrada."""
    def __init__(self, cx, y, label, value, color=C_WHITE, delay=0):
        self.cx    = cx
        self.y     = y
        self.label = label
        self.value = value
        self.color = color
        self.delay = delay
        self.shown = 0.0   # 0→1 fade/slide
        self.f_l   = pygame.font.Font(None, 24)
        self.f_v   = pygame.font.Font(None, 52)

    def update(self, dt):
        if self.delay > 0:
            self.delay -= dt
            return
        self.shown = min(1.0, self.shown + 0.035 * dt)

    def draw(self, screen):
        if self.shown < 0.01:
            return
        a    = int(self.shown * 255)
        slide = int((1 - self.shown) * 22)
        y    = self.y + slide
        w, h = 230, 80
        x    = self.cx - w // 2

        # Fondo
        bg = _sa(w, h)
        pygame.draw.rect(bg, (*C_PANEL, int(a * 0.85)), (0, 0, w, h), border_radius=8)
        screen.blit(bg, (x, y))

        # Borde
        bd = _sa(w, h)
        pygame.draw.rect(bd, (*C_BORDER, a), (0, 0, w, h), 1, border_radius=8)
        screen.blit(bd, (x, y))

        # Acento izquierdo
        ac = _sa(4, h - 16)
        pygame.draw.rect(ac, (*self.color, a), (0, 0, 4, h - 16), border_radius=2)
        screen.blit(ac, (x + 5, y + 8))

        # Textos
        lsurf = self.f_l.render(self.label, True,
                                 (int(C_GRAY[0]*a/255), int(C_GRAY[1]*a/255),
                                  int(C_GRAY[2]*a/255)))
        vsurf = self.f_v.render(str(self.value), True,
                                 (int(self.color[0]*a/255),
                                  int(self.color[1]*a/255),
                                  int(self.color[2]*a/255)))
        screen.blit(lsurf, (x + 16, y + 10))
        screen.blit(vsurf, (x + 16, y + 30))


class _TapButton:
    """Botón grande y táctil."""

    H      = 62
    RADIUS = 10

    def __init__(self, cx, y, width, label,
                 accent=C_RED, font_size=34):
        self.rect   = pygame.Rect(0, 0, width, self.H)
        self.rect.centerx = cx
        self.rect.y = y
        self.label  = label
        self.accent = accent
        self.font   = pygame.font.Font(None, font_size)
        self.hover  = False
        self._sc    = 1.0
        self._gl    = 0.0
        self.visible= 0.0   # 0→1 fade

    def update(self, mouse_pos, dt, visible_prog):
        self.visible = min(1.0, visible_prog)
        self.hover   = self.rect.inflate(14, 14).collidepoint(mouse_pos)
        t_sc = 1.015 if self.hover else 1.0
        t_gl = 1.0   if self.hover else 0.0
        spd  = 0.14 * dt
        self._sc += (t_sc - self._sc) * spd * 3
        self._gl += (t_gl - self._gl) * spd * 2

    def hit(self, vpos):
        return self.rect.inflate(14, 14).collidepoint(vpos)

    def draw(self, screen):
        a = int(self.visible * 255)
        if a < 8:
            return

        w  = int(self.rect.width  * self._sc)
        h  = int(self.rect.height * self._sc)
        x  = self.rect.centerx - w // 2
        y  = self.rect.centery - h // 2

        # Sombra
        sh = _sa(w + 16, h + 16)
        pygame.draw.rect(sh, (0, 0, 0, int(a * 0.4)),
                         (0, 0, w + 16, h + 16), border_radius=self.RADIUS + 4)
        screen.blit(sh, (x - 4, y + 6))

        # Glow
        if self._gl > 0.05:
            gs = _sa(w + 40, h + 40)
            pygame.draw.rect(gs, (*self.accent, int(self._gl * 50 * a / 255)),
                             (0, 0, w + 40, h + 40), border_radius=self.RADIUS + 8)
            screen.blit(gs, (x - 20, y - 20))

        # Fondo
        bg = _sa(w, h)
        bc = (
            min(255, C_PANEL[0] + int(self._gl * 14)),
            min(255, C_PANEL[1] + int(self._gl * 14)),
            min(255, C_PANEL[2] + int(self._gl * 24)),
        )
        pygame.draw.rect(bg, (*bc, int(a * 0.88)),
                         (0, 0, w, h), border_radius=self.RADIUS)
        screen.blit(bg, (x, y))

        # Marca lateral
        mk = _sa(5, h - 16)
        pygame.draw.rect(mk, (*self.accent, a), (0, 0, 5, h - 16), border_radius=3)
        screen.blit(mk, (x + 6, y + 8))

        # Borde
        bd = _sa(w, h)
        bd_c = self.accent if self.hover else C_BORDER
        pygame.draw.rect(bd, (*bd_c, a), (0, 0, w, h), 2, border_radius=self.RADIUS)
        screen.blit(bd, (x, y))

        # Texto
        tc = C_WHITE if self.hover else (175, 178, 192)
        tx_a = int(a * (tc[0] / 255)), int(a * (tc[1] / 255)), int(a * (tc[2] / 255))
        sh2  = self.font.render(self.label, True, (0, 0, 0))
        surf = self.font.render(self.label, True, tc)
        tx = x + w // 2 - surf.get_width() // 2
        ty = y + h // 2 - surf.get_height() // 2
        screen.blit(sh2, (tx + 2, ty + 2))
        screen.blit(surf, (tx, ty))


# ─────────────────────────────────────────────────────────────────────────────

class GameOverScene(Scene):

    def __init__(self, game, final_score, final_time_str):
        super().__init__(game)
        self.final_score    = final_score
        self.final_time_str = final_time_str

        # Fuentes
        self.f_huge   = pygame.font.Font(None, 110)
        self.f_medium = pygame.font.Font(None, 42)
        self.f_small  = pygame.font.Font(None, 28)
        self.f_hint   = pygame.font.Font(None, 22)

        # Estado de animación
        self.phase          = 'enter'   # enter → show_stats → buttons
        self.phase_timer    = 0.0
        self.fade_in        = 0.0       # 0→1 overlay de entrada
        self.title_shown    = 0.0
        self.content_prog   = 0.0
        self.buttons_prog   = 0.0

        # Escombros
        self.shards = [_DebrisShard() for _ in range(18)]

        # Estadísticas (con delay escalonado)
        cx   = WINDOW_WIDTH  // 2
        self.badges = [
            _StatBadge(cx - 125, 300, "PUNTUACIÓN",
                       f"{final_score:,}".replace(',', '.'),
                       C_GOLD, delay=55),
            _StatBadge(cx + 125, 300, "TIEMPO",
                       final_time_str,
                       C_CYAN, delay=90),
        ]

        # Botones
        btn_w = 280
        gap   = 24
        b_cx  = WINDOW_WIDTH // 2
        b_y   = 440

        self.btn_retry = _TapButton(b_cx - btn_w // 2 - gap // 2, b_y,
                                    btn_w, "  REINTENTAR",
                                    accent=C_RED, font_size=34)
        self.btn_menu  = _TapButton(b_cx + btn_w // 2 + gap // 2, b_y,
                                    btn_w, "  MENÚ PRINCIPAL",
                                    accent=(70, 75, 115), font_size=30)

        # Precalcular líneas de cuadrícula
        self._grid_surf = self._build_grid()

    def _build_grid(self):
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        gs = 60
        for x in range(0, WINDOW_WIDTH, gs):
            pygame.draw.line(s, (255, 255, 255, 5), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, gs):
            pygame.draw.line(s, (255, 255, 255, 5), (0, y), (WINDOW_WIDTH, y))
        return s

    def on_enter(self):
        self.phase        = 'enter'
        self.phase_timer  = 0.0
        self.fade_in      = 0.0
        self.title_shown  = 0.0
        self.content_prog = 0.0
        self.buttons_prog = 0.0

    # ─── events ──────────────────────────────────────────────────────────────

    def handle_events(self, event):
        if self.buttons_prog < 0.3:
            return

        vpos = self._vpos(event)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_retry.hit(vpos):
                self._go_retry()
                return
            if self.btn_menu.hit(vpos):
                self._go_menu()
                return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self._go_retry()
            elif event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                self._go_menu()

    def _vpos(self, event):
        if hasattr(event, 'pos'):
            rx, ry = event.pos
            scale  = max(0.001, self.game.render_scale)
            return ((rx - self.game.render_offset_x) / scale,
                    (ry - self.game.render_offset_y) / scale)
        return self.game.get_mouse_pos()

    def _go_retry(self):
        from scenes.gameplay import GameplayScene
        self.next_scene = GameplayScene(self.game)

    def _go_menu(self):
        from scenes.menu import MenuScene
        self.next_scene = MenuScene(self.game)

    # ─── update ──────────────────────────────────────────────────────────────

    def update(self):
        dt = 1.0  # escena no tiene su propio clock; se llama ~60 fps desde main

        self.phase_timer += dt

        # Fase enter: fade negro a fondo
        if self.phase == 'enter':
            self.fade_in = min(1.0, self.phase_timer / 40)
            if self.phase_timer > 25:
                self.title_shown = min(1.0, (self.phase_timer - 25) / 30)
            if self.phase_timer >= 60:
                self.phase = 'stats'
                self.phase_timer = 0.0

        elif self.phase == 'stats':
            self.content_prog = min(1.0, self.phase_timer / 50)
            for b in self.badges:
                b.update(dt)
            if self.phase_timer >= 80:
                self.phase = 'buttons'
                self.phase_timer = 0.0

        elif self.phase == 'buttons':
            self.buttons_prog = min(1.0, self.phase_timer / 40)
            for b in self.badges:
                b.update(dt)

        for s in self.shards:
            s.update(dt)

        mouse_pos = self.game.get_mouse_pos()
        self.btn_retry.update(mouse_pos, dt, self.buttons_prog)
        self.btn_menu.update(mouse_pos,  dt, self.buttons_prog)

    # ─── render ──────────────────────────────────────────────────────────────

    def render(self):
        self.screen.fill(C_BG)
        self.screen.blit(self._grid_surf, (0, 0))

        self._draw_vignette()
        self._draw_shards()
        self._draw_overlay()
        self._draw_title()
        self._draw_divider()
        for b in self.badges:
            b.draw(self.screen)
        self._draw_buttons()
        self._draw_hints()

    def _draw_vignette(self):
        for corner_x, corner_y in [(0, 0), (WINDOW_WIDTH, 0),
                                    (0, WINDOW_HEIGHT), (WINDOW_WIDTH, WINDOW_HEIGHT)]:
            r = 360
            s = _sa(r * 2, r * 2)
            pygame.draw.circle(s, (0, 0, 0, 70), (r, r), r)
            self.screen.blit(s, (corner_x - r, corner_y - r))

    def _draw_shards(self):
        for sh in self.shards:
            if sh.alpha < 8:
                continue
            s = _sa(sh.size * 2 + 2, sh.size * 2 + 2)
            pygame.draw.rect(s, (*sh.color, sh.alpha),
                             (0, 0, sh.size * 2, sh.size * 2))
            self.screen.blit(s, (int(sh.x) - sh.size, int(sh.y) - sh.size))

    def _draw_overlay(self):
        # Faja oscura de fondo para el título
        a   = int(self.fade_in * 210)
        ov  = _sa(WINDOW_WIDTH, 180)
        ov.fill((0, 0, 0, a))
        self.screen.blit(ov, (0, 120))

    def _draw_title(self):
        if self.title_shown < 0.01:
            return

        a  = int(self.title_shown * 255)
        sl = int((1 - self.title_shown) * 20)
        cx = WINDOW_WIDTH // 2
        ty = 132 + sl

        # Chromatic shadow
        sh_r = self.f_huge.render("GAME  OVER", True, (160, 0, 0))
        sh_c = self.f_huge.render("GAME  OVER", True, (0, 100, 110))
        txt  = self.f_huge.render("GAME  OVER", True, C_WHITE)

        for surf, ox, oy in [(sh_r, 4, 4), (sh_c, -3, 2), (txt, 0, 0)]:
            surf_a = surf.copy()
            surf_a.set_alpha(a if surf is txt else int(a * 0.6))
            self.screen.blit(surf_a,
                             (cx - surf.get_width() // 2 + ox, ty + oy))

        # Línea decorativa roja bajo el título
        lw  = int(self.title_shown * 460)
        lhf = _sa(lw + 2, 3)
        pygame.draw.line(lhf, (C_RED[0], C_RED[1], C_RED[2], a),
                         (0, 1), (lw, 1), 2)
        self.screen.blit(lhf, (cx - lw // 2, ty + 98))

    def _draw_divider(self):
        if self.content_prog < 0.01:
            return
        a  = int(self.content_prog * 180)
        cx = WINDOW_WIDTH // 2
        y  = 268
        lw = int(self.content_prog * 520)
        s  = _sa(lw + 2, 1)
        pygame.draw.line(s, (C_BORDER[0], C_BORDER[1], C_BORDER[2], a),
                         (0, 0), (lw, 0), 1)
        self.screen.blit(s, (cx - lw // 2, y))

    def _draw_buttons(self):
        self.btn_retry.draw(self.screen)
        self.btn_menu.draw(self.screen)

    def _draw_hints(self):
        if self.buttons_prog < 0.6:
            return
        a = int((self.buttons_prog - 0.6) / 0.4 * 160)
        hints = [
            ("R", "Reintentar"),
            ("ESPACIO / ESC", "Menú principal"),
        ]
        cx = WINDOW_WIDTH // 2
        y  = 528
        f  = self.f_hint
        for i, (key, act) in enumerate(hints):
            ks = f.render(key, True, (80, 83, 100))
            ac = f.render(f"  {act}", True, (50, 52, 68))
            ks.set_alpha(a)
            ac.set_alpha(a)
            tw  = ks.get_width() + ac.get_width()
            gap = 40
            off = (i - 0.5) * (tw + gap)
            self.screen.blit(ks, (int(cx + off), y))
            self.screen.blit(ac, (int(cx + off + ks.get_width()), y))