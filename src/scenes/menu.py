"""
Menú Principal — Rediseñado
Estética dark-industrial / zombie survivor.
Botones grandes y táctiles, animaciones atmosféricas.

FIXES:
- BigButton.update(): clampa _glow en [0,1] y _scale en [0.95, 1.1]
  para evitar valores negativos/NaN cuando dt es alto (fps bajo).
- MenuScene.handle_events(): ya NO actualiza botones (evita doble-tick).
- MenuScene usa clock.tick(60) para limitarse a 60fps reales.
"""
import pygame
import math
import random
import sys
from scenes.scene import Scene
from settings import BLACK, WHITE, WINDOW_WIDTH, WINDOW_HEIGHT

C_BG         = (6,  7,  10)
C_BG2        = (10, 12, 18)
C_RED        = (210,  30,  30)
C_RED_DIM    = (130,  15,  15)
C_CYAN       = (0,  210, 220)
C_CYAN_DIM   = (0,   90, 100)
C_WHITE      = (230, 232, 238)
C_GRAY       = (90,  92, 105)
C_PANEL      = (14,  16,  24)
C_BORDER     = (40,  44,  62)
C_BORDER_LIT = (70,  75, 110)
C_ACCENT     = (200,  20,  20)

def _surf_alpha(w, h):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    return s


class _Particle:
    """Partícula de ambiente (ascendente, tenue)."""
    __slots__ = ('x', 'y', 'speed', 'size', 'color', 'life', 'max_life')

    def __init__(self):
        self.reset()

    def reset(self):
        self.x        = random.uniform(0, WINDOW_WIDTH)
        self.y        = random.uniform(0, WINDOW_HEIGHT)
        self.speed    = random.uniform(0.15, 0.55)
        self.size     = random.randint(1, 3)
        self.max_life = random.randint(180, 420)
        self.life     = random.randint(0, self.max_life)
        r = random.random()
        if r < 0.45:
            self.color = C_RED
        elif r < 0.65:
            self.color = C_CYAN
        else:
            self.color = (80, 85, 110)

    def update(self, dt):
        self.y    -= self.speed * dt
        self.life += dt
        if self.y < -10 or self.life > self.max_life:
            self.reset()
            self.y = WINDOW_HEIGHT + 5

    @property
    def alpha(self):
        t = self.life / self.max_life
        if t < 0.2: return int(t / 0.2 * 160)
        if t > 0.8: return int((1 - t) / 0.2 * 160)
        return 160

class _ScanLine:
    """Línea de escaneo horizontal decorativa."""
    def __init__(self):
        self.y    = random.uniform(0, WINDOW_HEIGHT)
        self.alpha = random.randint(8, 22)
        self.speed = random.uniform(0.2, 0.8)

    def update(self, dt):
        self.y += self.speed * dt
        if self.y > WINDOW_HEIGHT:
            self.y = -2
            self.alpha = random.randint(8, 22)
            self.speed = random.uniform(0.2, 0.8)

class BigButton:
    """Botón grande táctil con animaciones propias."""

    H      = 64
    RADIUS = 10

    def __init__(self, cx, y, width, text,
                 accent=C_RED, font_size=34):
        self.rect    = pygame.Rect(0, 0, width, self.H)
        self.rect.centerx = cx
        self.rect.y  = y
        self.text    = text
        self.accent  = accent
        self.font    = pygame.font.Font(None, font_size)
        self.hovered = False
        self._scale  = 1.0
        self._glow   = 0.0

    def update(self, mouse_pos, dt=1.0):
        self.hovered = self.rect.inflate(16, 16).collidepoint(mouse_pos)
        target_scale = 1.015 if self.hovered else 1.0
        target_glow  = 1.0   if self.hovered else 0.0

        # Clampear dt para evitar overshoots en fps muy bajos
        safe_dt = min(dt, 3.0)
        spd = 0.14 * safe_dt

        self._scale += (target_scale - self._scale) * spd * 3
        self._glow  += (target_glow  - self._glow)  * spd * 2

        # Clamp estricto — evita valores negativos/fuera de rango
        # que causarían colores inválidos en draw()
        self._scale = max(0.98, min(1.05, self._scale))
        self._glow  = max(0.0,  min(1.0,  self._glow))

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.inflate(16, 16).collidepoint(event.pos[0], event.pos[1])
        return False

    def is_clicked_vpos(self, event, vpos):
        """Usa coordenadas virtuales para soporte táctil escalado."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.inflate(16, 16).collidepoint(vpos)
        return False

    def draw(self, screen):
        w = int(self.rect.width  * self._scale)
        h = int(self.rect.height * self._scale)
        # Seguridad: evitar superficies con dimensiones inválidas
        w = max(4, w)
        h = max(4, h)
        x = self.rect.centerx - w // 2
        y = self.rect.centery - h // 2
        r = pygame.Rect(x, y, w, h)

        # Sombra
        sh = _surf_alpha(w + 20, h + 20)
        pygame.draw.rect(sh, (0, 0, 0, 90),
                         (0, 0, w + 20, h + 20), border_radius=self.RADIUS + 4)
        screen.blit(sh, (x - 6, y + 8))

        # Glow de acento
        if self._glow > 0.05:
            ga = int(self._glow * 55)
            gs = _surf_alpha(w + 40, h + 40)
            pygame.draw.rect(gs, (*self.accent, ga),
                             (0, 0, w + 40, h + 40), border_radius=self.RADIUS + 8)
            screen.blit(gs, (x - 20, y - 20))

        # Fondo — componentes de color siempre clampeados a [0, 255]
        bg_alpha = 200 if self.hovered else 170
        bg_surf  = _surf_alpha(w, h)
        bg_color = (
            max(0, min(255, C_PANEL[0] + int(self._glow * 14))),
            max(0, min(255, C_PANEL[1] + int(self._glow * 14))),
            max(0, min(255, C_PANEL[2] + int(self._glow * 22))),
        )
        pygame.draw.rect(bg_surf, (*bg_color, bg_alpha),
                         (0, 0, w, h), border_radius=self.RADIUS)
        screen.blit(bg_surf, (x, y))

        # Borde izquierdo de acento (marca de color)
        mark_surf = _surf_alpha(5, h - 16)
        pygame.draw.rect(mark_surf, (*self.accent, 240),
                         (0, 0, 5, h - 16), border_radius=3)
        screen.blit(mark_surf, (x + 6, y + 8))

        # Borde principal
        bd_alpha = 220 if self.hovered else 130
        bd_color = self.accent if self.hovered else C_BORDER_LIT
        bd_surf  = _surf_alpha(w, h)
        pygame.draw.rect(bd_surf, (*bd_color, bd_alpha),
                         (0, 0, w, h), 2, border_radius=self.RADIUS)
        screen.blit(bd_surf, (x, y))

        # Texto
        txt_color = C_WHITE if self.hovered else (180, 183, 195)
        shadow = self.font.render(self.text, True, (0, 0, 0))
        surf   = self.font.render(self.text, True, txt_color)
        tx = r.centerx - surf.get_width() // 2
        ty = r.centery - surf.get_height() // 2
        screen.blit(shadow, (tx + 2, ty + 2))
        screen.blit(surf,   (tx, ty))

class MenuScene(Scene):

    def __init__(self, game):
        super().__init__(game)

        self.clock = pygame.time.Clock()
        self.timer = 0.0

        # Fuentes
        self.f_title    = pygame.font.Font(None, 112)
        self.f_subtitle = pygame.font.Font(None, 32)
        self.f_label    = pygame.font.Font(None, 24)
        self.f_version  = pygame.font.Font(None, 20)

        # Botones centrados
        cx     = WINDOW_WIDTH  // 2
        btn_w  = 320
        btn_y0 = 340

        self.btn_play    = BigButton(cx, btn_y0,       btn_w, "  INICIAR JUEGO",
                                     accent=C_RED,  font_size=36)
        self.btn_exit    = BigButton(cx, btn_y0 + 82,  btn_w, "  SALIR",
                                     accent=(80, 80, 110), font_size=34)

        # Ambiente
        self.particles  = [_Particle() for _ in range(55)]
        self.scanlines  = [_ScanLine() for _ in range(6)]

        # Precalcular líneas de cuadrícula de fondo
        self._grid_surf = self._build_grid()

        # Letras del título flotantes (para el efecto glitch sutil)
        self._glitch_timer = 0.0
        self._glitch_active = False

    def on_enter(self):
        pygame.mouse.set_visible(True)

    def _build_grid(self):
        """Crea una superficie de cuadrícula reutilizable."""
        s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        gs = 60
        for x in range(0, WINDOW_WIDTH, gs):
            pygame.draw.line(s, (255, 255, 255, 7), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, gs):
            pygame.draw.line(s, (255, 255, 255, 7), (0, y), (WINDOW_WIDTH, y))
        # Acento diagonal
        pygame.draw.line(s, (200, 20, 20, 18),
                         (0, WINDOW_HEIGHT), (WINDOW_WIDTH * 0.6, 0), 1)
        pygame.draw.line(s, (200, 20, 20, 12),
                         (0, WINDOW_HEIGHT * 0.8), (WINDOW_WIDTH * 0.8, 0), 1)
        return s

    def handle_events(self, event):
        vpos = self._vpos(event)

        # Clicks — NO actualizamos botones aquí (se hace en update())
        if self.btn_play.is_clicked_vpos(event, vpos):
            from scenes.gameplay import GameplayScene
            self.next_scene = GameplayScene(self.game)

        if self.btn_exit.is_clicked_vpos(event, vpos):
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN):
                from scenes.gameplay import GameplayScene
                self.next_scene = GameplayScene(self.game)
            elif event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()

    def _vpos(self, event):
        if hasattr(event, 'pos'):
            rx, ry = event.pos
            scale  = max(0.001, self.game.render_scale)
            return ((rx - self.game.render_offset_x) / scale,
                    (ry - self.game.render_offset_y) / scale)
        return self.game.get_mouse_pos()

    def update(self):
        # Limitar menú a 60 fps reales
        dt_ms = self.clock.tick(60)
        dt    = dt_ms / 16.667

        self.timer += 0.018 * dt

        for p in self.particles:
            p.update(dt)
        for sl in self.scanlines:
            sl.update(dt)

        mouse_pos = self.game.get_mouse_pos()
        self.btn_play.update(mouse_pos, dt)
        self.btn_exit.update(mouse_pos, dt)

        # Glitch sutil del título
        self._glitch_timer += dt
        if self._glitch_timer > 180 and not self._glitch_active:
            if random.random() < 0.012:
                self._glitch_active = True
                self._glitch_timer  = 0
        if self._glitch_active and self._glitch_timer > 6:
            self._glitch_active = False
            self._glitch_timer  = 0

    def render(self):
        self.screen.fill(C_BG)

        self._draw_bg()
        self._draw_particles()
        self._draw_scanlines()
        self._draw_title()
        self._draw_tagline()
        self._draw_buttons()
        self._draw_controls_panel()
        self._draw_version()

    def _draw_bg(self):
        # Cuadrícula base
        self.screen.blit(self._grid_surf, (0, 0))

        # Viñeta radial (oscurece bordes)
        vw, vh = WINDOW_WIDTH, WINDOW_HEIGHT

        # Simplificado: solo blobs oscuros en esquinas
        for corner_x, corner_y in [(0, 0), (vw, 0), (0, vh), (vw, vh)]:
            r = 350
            s2 = _surf_alpha(r * 2, r * 2)
            pygame.draw.circle(s2, (0, 0, 0, 80), (r, r), r)
            self.screen.blit(s2, (corner_x - r, corner_y - r))

        # Faja oscura central (añade profundidad)
        center_strip = _surf_alpha(vw, 320)
        center_strip.fill((0, 0, 0, 30))
        self.screen.blit(center_strip, (0, WINDOW_HEIGHT // 2 - 160))

        # Barra roja horizontal decorativa (arriba)
        pygame.draw.line(self.screen, C_RED_DIM, (0, 2), (WINDOW_WIDTH, 2), 2)
        # Barra cian (abajo)
        pygame.draw.line(self.screen, C_CYAN_DIM, (0, WINDOW_HEIGHT - 3),
                         (WINDOW_WIDTH, WINDOW_HEIGHT - 3), 2)

    def _draw_particles(self):
        for p in self.particles:
            a = p.alpha
            if a < 8:
                continue
            s = _surf_alpha(p.size * 2 + 2, p.size * 2 + 2)
            pygame.draw.circle(s, (*p.color, a),
                               (p.size + 1, p.size + 1), p.size)
            self.screen.blit(s, (int(p.x) - p.size, int(p.y) - p.size))

    def _draw_scanlines(self):
        for sl in self.scanlines:
            s = _surf_alpha(WINDOW_WIDTH, 2)
            s.fill((255, 255, 255, int(sl.alpha)))
            self.screen.blit(s, (0, int(sl.y)))

    def _draw_title(self):
        title = "PROYECT"
        sub   = "SURVIVOR"
        cx    = WINDOW_WIDTH // 2

        # Glitch offset
        gx = random.randint(-4, 4) if self._glitch_active else 0

        # Sombra roja desplazada (efecto chromatic)
        sh_r = self.f_title.render(title, True, (180, 0, 0))
        self.screen.blit(sh_r, (cx - sh_r.get_width() // 2 + gx + 3, 105 + 3))
        sh_c = self.f_title.render(title, True, (0, 120, 130))
        self.screen.blit(sh_c, (cx - sh_c.get_width() // 2 + gx - 3, 105 + 1))

        # Texto principal
        t_surf = self.f_title.render(title, True, C_WHITE)
        self.screen.blit(t_surf, (cx - t_surf.get_width() // 2 + gx, 105))

        # Subtítulo en rojo
        beat = abs(math.sin(self.timer * 0.9))
        sub_r = int(200 + beat * 55)
        sub_color = (sub_r, int(beat * 20), int(beat * 20))
        sub_surf = self.f_subtitle.render(sub, True, sub_color)
        # Líneas flanqueando el subtítulo
        sw = sub_surf.get_width()
        sy = 208
        line_y = sy + sub_surf.get_height() // 2
        pygame.draw.line(self.screen, C_RED_DIM,
                         (cx - sw // 2 - 60, line_y),
                         (cx - sw // 2 - 8,  line_y), 2)
        pygame.draw.line(self.screen, C_RED_DIM,
                         (cx + sw // 2 + 8,  line_y),
                         (cx + sw // 2 + 60, line_y), 2)
        # Sombra subtítulo
        sh2 = self.f_subtitle.render(sub, True, (60, 0, 0))
        self.screen.blit(sh2, (cx - sw // 2 + 2, sy + 2))
        self.screen.blit(sub_surf, (cx - sw // 2, sy))

    def _draw_tagline(self):
        t = "Sobrevive. Evoluciona. Muere de pie."
        cy = int(250 + math.sin(self.timer * 0.7) * 2)
        surf = self.f_label.render(t, True, C_GRAY)
        self.screen.blit(surf, (WINDOW_WIDTH // 2 - surf.get_width() // 2, cy))

    def _draw_buttons(self):
        self.btn_play.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # Hint de teclado
        hint = self.f_label.render("ESPACIO  /  ENTER  para iniciar", True,
                                    (55, 58, 75))
        self.screen.blit(hint,
                         (WINDOW_WIDTH // 2 - hint.get_width() // 2, 490))

    def _draw_controls_panel(self):
        px   = WINDOW_WIDTH // 2 - 220
        py   = 520
        pw   = 440
        ph   = 148

        # Panel
        bg = _surf_alpha(pw, ph)
        pygame.draw.rect(bg, (*C_PANEL, 175), (0, 0, pw, ph), border_radius=8)
        self.screen.blit(bg, (px, py))
        bd = _surf_alpha(pw, ph)
        pygame.draw.rect(bd, (*C_BORDER, 200), (0, 0, pw, ph), 1, border_radius=8)
        self.screen.blit(bd, (px, py))

        # Título del panel
        f_head = pygame.font.Font(None, 20)
        head = f_head.render("CONTROLES", True, C_CYAN_DIM)
        self.screen.blit(head,
                         (px + pw // 2 - head.get_width() // 2, py + 10))
        pygame.draw.line(self.screen, C_BORDER,
                         (px + 12, py + 28), (px + pw - 12, py + 28), 1)

        controls = [
            ("WASD",           "Mover"),
            ("Mouse",          "Apuntar"),
            ("Click Izq",      "Disparar"),
            ("1 – 4",          "Cambiar arma"),
            ("Ctrl",           "Dash"),
            ("ESC / Enter",    "Pausa"),
        ]
        f_ctrl = pygame.font.Font(None, 22)
        row_h  = 18
        for i, (key, action) in enumerate(controls):
            ky = py + 36 + i * row_h
            ks = f_ctrl.render(key, True, (190, 192, 205))
            ac = f_ctrl.render(action, True, (90, 93, 115))
            self.screen.blit(ks, (px + 18, ky))
            self.screen.blit(ac, (px + 165, ky))

    def _draw_version(self):
        v = self.f_version.render("v0.1-alpha  -  ProyectSurvivor", True, (35, 37, 52))
        self.screen.blit(v, (WINDOW_WIDTH - v.get_width() - 12,
                              WINDOW_HEIGHT - v.get_height() - 8))