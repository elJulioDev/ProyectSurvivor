"""
Escena de Gameplay — Pausa rediseñada con botones táctiles.
La lógica del juego vive en LevelManager.
GameplayScene maneja UI, input y transiciones.
"""
import pygame
import sys
import math
import random
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, BLACK, WHITE
from managers.level_manager import LevelManager
from ui.hud import HUD
from ui.mobile_controls import MobileControls

# ── Paleta coherente con el resto de menús ────────────────────────────────────
_C_BG      = (6,   7,  10)
_C_PANEL   = (12,  14,  22)
_C_BORDER  = (40,  44,  62)
_C_BORDER_LIT = (70, 75, 110)
_C_RED     = (210,  30,  30)
_C_RED_DIM = (100,  12,  12)
_C_CYAN    = (0,  200, 215)
_C_CYAN_DIM= (0,   80, 95)
_C_WHITE   = (230, 232, 238)
_C_GRAY    = (90,  92, 105)


def _sa(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


class _PauseButton:
    """Botón grande táctil para el menú de pausa."""

    H = 62
    R = 10  # border radius

    def __init__(self, cx, y, width, label, accent=_C_RED, font_size=34):
        self.rect   = pygame.Rect(0, 0, width, self.H)
        self.rect.centerx = cx
        self.rect.y = y
        self.label  = label
        self.accent = accent
        self.font   = pygame.font.Font(None, font_size)
        self.hover  = False
        self._sc    = 1.0
        self._gl    = 0.0

    def update(self, mouse_pos, dt=1.0):
        self.hover = self.rect.inflate(16, 16).collidepoint(mouse_pos)
        t_sc = 1.015 if self.hover else 1.0
        t_gl = 1.0   if self.hover else 0.0
        spd  = 0.14 * dt
        self._sc += (t_sc - self._sc) * spd * 3
        self._gl += (t_gl - self._gl) * spd * 2

    def hit(self, vpos):
        return self.rect.inflate(16, 16).collidepoint(vpos)

    def draw(self, screen):
        w  = int(self.rect.width  * self._sc)
        h  = int(self.rect.height * self._sc)
        x  = self.rect.centerx - w // 2
        y  = self.rect.centery - h // 2

        # Sombra
        sh = _sa(w + 16, h + 16)
        pygame.draw.rect(sh, (0, 0, 0, 80),
                         (0, 0, w + 16, h + 16), border_radius=self.R + 4)
        screen.blit(sh, (x - 4, y + 6))

        # Glow
        if self._gl > 0.05:
            gs = _sa(w + 40, h + 40)
            pygame.draw.rect(gs, (*self.accent, int(self._gl * 50)),
                             (0, 0, w + 40, h + 40), border_radius=self.R + 8)
            screen.blit(gs, (x - 20, y - 20))

        # Fondo
        bg = _sa(w, h)
        bc = (
            min(255, _C_PANEL[0] + int(self._gl * 14)),
            min(255, _C_PANEL[1] + int(self._gl * 14)),
            min(255, _C_PANEL[2] + int(self._gl * 24)),
        )
        pygame.draw.rect(bg, (*bc, 220), (0, 0, w, h), border_radius=self.R)
        screen.blit(bg, (x, y))

        # Marca lateral
        mk = _sa(5, h - 16)
        pygame.draw.rect(mk, (*self.accent, 240), (0, 0, 5, h - 16), border_radius=3)
        screen.blit(mk, (x + 6, y + 8))

        # Borde
        bd = _sa(w, h)
        bd_c = self.accent if self.hover else _C_BORDER_LIT
        pygame.draw.rect(bd, (*bd_c, 220 if self.hover else 140),
                         (0, 0, w, h), 2, border_radius=self.R)
        screen.blit(bd, (x, y))

        # Texto
        tc   = _C_WHITE if self.hover else (175, 178, 192)
        shd  = self.font.render(self.label, True, (0, 0, 0))
        surf = self.font.render(self.label, True, tc)
        tx = x + w // 2 - surf.get_width() // 2
        ty = y + h // 2 - surf.get_height() // 2
        screen.blit(shd,  (tx + 2, ty + 2))
        screen.blit(surf, (tx, ty))


class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.level      = LevelManager()
        self.hud        = HUD(self.screen)
        self.clock      = pygame.time.Clock()
        self.dt         = 1.0
        self.target_fps = 60
        self.paused     = False

        # Fuentes de pausa
        self.f_pause_title = pygame.font.Font(None, 82)
        self.f_pause_sub   = pygame.font.Font(None, 28)

        # Botones de pausa (rediseñados, grandes y táctiles)
        cx = WINDOW_WIDTH  // 2
        self.btn_continue = _PauseButton(cx, WINDOW_HEIGHT // 2 + 20,  300,
                                          "  CONTINUAR",
                                          accent=_C_CYAN,  font_size=36)
        self.btn_menu     = _PauseButton(cx, WINDOW_HEIGHT // 2 + 100, 300,
                                          "  MENÚ PRINCIPAL",
                                          accent=(70, 75, 110), font_size=30)
        self.btn_exit     = _PauseButton(cx, WINDOW_HEIGHT // 2 + 178, 300,
                                          "  SALIR DEL JUEGO",
                                          accent=_C_RED_DIM if True else _C_RED,
                                          font_size=28)

        # Para el fondo de pausa animado
        self._pause_timer   = 0.0
        self._pause_overlay = self._build_pause_overlay()

        self.show_debug      = False
        self.crosshair_scale = 1.0
        self.last_pulse_time = 0

        # Controles móviles
        self.mobile = MobileControls(WINDOW_WIDTH, WINDOW_HEIGHT)

    def _build_pause_overlay(self):
        """Construye la superficie de fondo del menú de pausa."""
        s = _sa(WINDOW_WIDTH, WINDOW_HEIGHT)
        # Cuadrícula sutil
        gs = 60
        for x in range(0, WINDOW_WIDTH, gs):
            pygame.draw.line(s, (255, 255, 255, 6), (x, 0), (x, WINDOW_HEIGHT))
        for y in range(0, WINDOW_HEIGHT, gs):
            pygame.draw.line(s, (255, 255, 255, 6), (0, y), (WINDOW_WIDTH, y))
        return s

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def on_enter(self):
        pygame.mouse.set_visible(False)
        self.level.initialize()
        self.paused          = False
        self.show_debug      = False
        self.crosshair_scale = 1.0
        self._pause_timer    = 0.0

    def on_exit(self):
        if self.level:
            self.level.cleanup()
        pygame.mouse.set_visible(True)

    # ── Eventos ───────────────────────────────────────────────────────────────

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            self.mobile.enabled = not self.mobile.enabled
            estado = "ACTIVADO" if self.mobile.enabled else "desactivado"
            print(f"[DEBUG] Modo móvil: {estado}")
            pygame.mouse.set_visible(not self.mobile.enabled)
            return

        vpos = self._vpos_from_event(event)

        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_menu.update(mouse_pos)
            self.btn_exit.update(mouse_pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_continue.hit(vpos):
                    self.paused = False
                    pygame.mouse.set_visible(self.mobile.enabled)
                    return
                if self.btn_menu.hit(vpos):
                    pygame.mouse.set_visible(True)
                    from scenes.menu import MenuScene
                    self.next_scene = MenuScene(self.game)
                    return
                if self.btn_exit.hit(vpos):
                    pygame.quit()
                    sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                    self.paused = False
                    pygame.mouse.set_visible(self.mobile.enabled)
            return

        # Tap en slot de arma (móvil)
        if self.mobile.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            slot_idx = self.mobile.check_weapon_slot_tap(vpos[0], vpos[1],
                                                          self.level.player)
            if slot_idx >= 0 and self.level.player:
                self.level.player.current_weapon_index = slot_idx
                return

        consumed = self.mobile.handle_event(event, vpos, self.level.player)
        if consumed:
            if self.mobile.pause_request:
                self.paused = True
                pygame.mouse.set_visible(True)
                self.mobile.pause_request = False
            return

        if self.level.player and not self.paused:
            self.level.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.mouse.set_visible(True)
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            elif event.key == pygame.K_RETURN:
                self.paused = not self.paused
                pygame.mouse.set_visible(self.paused)
            elif event.key == pygame.K_x:
                self.show_debug = not self.show_debug

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self):
        raw_dt  = self.clock.tick(self.target_fps) / (1000.0 / self.target_fps)
        self.dt = min(raw_dt, 3.0)

        if self.paused:
            self._pause_timer += self.dt
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos, self.dt)
            self.btn_menu.update(mouse_pos, self.dt)
            self.btn_exit.update(mouse_pos, self.dt)
            return

        if self.level.player and self.level.player.pending_level_ups > 0:
            self.level.player.pending_level_ups -= 1
            from scenes.upgrade import UpgradeScene
            pygame.mouse.set_visible(True)
            self.game.current_scene = UpgradeScene(self.game, self)
            return

        if self.level.game_over:
            pygame.mouse.set_visible(True)
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(
                self.game,
                self.level.score,
                self.level.spawn_manager.get_time_string()
            )
            return

        keys          = pygame.key.get_pressed()
        mouse_pos     = self.game.get_mouse_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        self.mobile.update(self.level.player)

        if self.mobile.enabled and self.mobile.dash_request:
            if self.level.player:
                mdx, mdy = self.mobile.movement
                self.level.player._execute_dash_with_vector(mdx, mdy)
            self.mobile.dash_request = False

        self.level.update(self.dt, keys, mouse_pos, mouse_pressed,
                          mobile=self.mobile)

        self.mobile.clear_requests()
        self._update_crosshair(mouse_pressed)

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self):
        self.screen.fill(BLACK)
        self.level.render_world(self.screen)

        if self.hud and self.level.player:
            time_str = self.level.spawn_manager.get_time_string()
            self.hud.render(
                self.level.player,
                time_str,
                self.level.score,
                len(self.level.enemies),
                self.dt
            )

        self.mobile.render(self.screen, self.level.player)

        if not self.paused and not self.mobile.enabled:
            self._render_crosshair()

        if self.paused:
            self._render_pause_menu()

        if self.show_debug:
            self._render_debug_info()

    # ── Pause menu ────────────────────────────────────────────────────────────

    def _render_pause_menu(self):
        # ── Overlay oscuro ─────────────────────────────────────────────────
        ov = _sa(WINDOW_WIDTH, WINDOW_HEIGHT)
        ov.fill((0, 0, 8, 195))
        self.screen.blit(ov, (0, 0))

        # Cuadrícula sutil
        self.screen.blit(self._pause_overlay, (0, 0))

        cx = WINDOW_WIDTH  // 2
        cy = WINDOW_HEIGHT // 2

        # ── Panel central ──────────────────────────────────────────────────
        pw, ph = 360, 340
        px = cx - pw // 2
        py = cy - ph // 2 + 10

        # Sombra del panel
        sh = _sa(pw + 24, ph + 24)
        pygame.draw.rect(sh, (0, 0, 0, 110),
                         (0, 0, pw + 24, ph + 24), border_radius=14)
        self.screen.blit(sh, (px - 8, py + 12))

        # Fondo del panel
        bg = _sa(pw, ph)
        pygame.draw.rect(bg, (*_C_PANEL, 235), (0, 0, pw, ph), border_radius=12)
        self.screen.blit(bg, (px, py))

        # Borde
        bd = _sa(pw, ph)
        pygame.draw.rect(bd, (*_C_BORDER_LIT, 180),
                         (0, 0, pw, ph), 1, border_radius=12)
        self.screen.blit(bd, (px, py))

        # Acento superior (franja de color cian)
        pygame.draw.line(self.screen, _C_CYAN,
                         (px + 12, py + 1), (px + pw - 12, py + 1), 2)

        # ── Título ─────────────────────────────────────────────────────────
        beat   = abs(math.sin(self._pause_timer * 0.04))
        c_beat = (
            int(_C_CYAN[0] * 0.7 + beat * _C_CYAN[0] * 0.3),
            int(_C_CYAN[1] * 0.7 + beat * _C_CYAN[1] * 0.3),
            int(_C_CYAN[2] * 0.7 + beat * _C_CYAN[2] * 0.3),
        )

        sh_t = self.f_pause_title.render("PAUSA", True, (0, 0, 0))
        ti_t = self.f_pause_title.render("PAUSA", True, c_beat)
        tx   = cx - ti_t.get_width() // 2
        ty   = py + 22
        self.screen.blit(sh_t, (tx + 3, ty + 3))
        self.screen.blit(ti_t, (tx, ty))

        # Separador
        pygame.draw.line(self.screen, _C_BORDER,
                         (px + 20, py + 100), (px + pw - 20, py + 100), 1)

        # ── Botones ────────────────────────────────────────────────────────
        self.btn_continue.draw(self.screen)
        self.btn_menu.draw(self.screen)
        self.btn_exit.draw(self.screen)

        # ── Hint teclado ───────────────────────────────────────────────────
        hint = self.f_pause_sub.render("ESC / ENTER  para continuar", True,
                                        (40, 42, 58))
        self.screen.blit(hint,
                         (cx - hint.get_width() // 2,
                          py + ph + 14))

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _vpos_from_event(self, event) -> tuple:
        if hasattr(event, 'pos'):
            rx, ry = event.pos
            scale  = max(0.001, self.game.render_scale)
            return ((rx - self.game.render_offset_x) / scale,
                    (ry - self.game.render_offset_y) / scale)
        return self.game.get_mouse_pos()

    def _update_crosshair(self, mouse_pressed):
        if not self.level.player:
            return
        player_shot_time = self.level.player.last_shot_time
        if player_shot_time != self.last_pulse_time:
            current_weapon  = self.level.player.weapons[
                self.level.player.current_weapon_index]
            pulse_intensity = 0.3 + (current_weapon.shake_amount * 0.15)
            self.crosshair_scale += pulse_intensity
            self.last_pulse_time  = player_shot_time
        if self.crosshair_scale > 4.0:
            self.crosshair_scale = 4.0
        self.crosshair_scale += (1.0 - self.crosshair_scale) * 0.08 * self.dt

    def _render_crosshair(self):
        mx, my = self.game.get_mouse_pos()
        from settings import (CROSSHAIR_COLOR, CROSSHAIR_SIZE,
                              CROSSHAIR_GAP, CROSSHAIR_THICKNESS, CROSSHAIR_DOT_SIZE)
        cur_gap  = CROSSHAIR_GAP  * self.crosshair_scale
        cur_size = CROSSHAIR_SIZE * self.crosshair_scale
        dot_rect = pygame.Rect(0, 0, CROSSHAIR_DOT_SIZE, CROSSHAIR_DOT_SIZE)
        dot_rect.center = (mx, my)
        pygame.draw.rect(self.screen, CROSSHAIR_COLOR, dot_rect)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my - cur_gap - cur_size),
                         (mx, my - cur_gap), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my + cur_gap),
                         (mx, my + cur_gap + cur_size), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx - cur_gap - cur_size, my),
                         (mx - cur_gap, my), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx + cur_gap, my),
                         (mx + cur_gap + cur_size, my), CROSSHAIR_THICKNESS)

    def _render_debug_info(self):
        font  = pygame.font.Font(None, 24)
        fps   = self.clock.get_fps()
        dt_ms = self.dt * (1000.0 / self.target_fps)
        d     = self.level.get_debug_info()
        mobile_str = "ACTIVADO  [F5 desactiva]" if self.mobile.enabled \
                     else "desactivado  [F5 activa]"
        debug_texts = [
            f"FPS: {fps:.1f} | DeltaTime: {dt_ms:.1f}ms",
            f"Enemigos vivos: {d['enemies_total']} (Visibles: {d['enemies_rendered']})  |  Dead pool: {d['dead_pool_size']}",
            f"Proyectiles: {d['projectiles']}  |  Enemigo: {d['enemy_projectiles']}",
            f"Partículas: {d['particles_active']} (Visibles: {d['particles_rendered']}) / {d['particles_capacity']}",
            f"Gemas XP: {d['gems_count']}",
            f"Móvil: {mobile_str}",
            f"Pausa: {'SÍ' if self.paused else 'NO'}   |   X: Toggle Debug",
        ]
        y = 110
        for text in debug_texts:
            shadow = font.render(text, True, (0, 0, 0))
            self.screen.blit(shadow, (11, y + 1))
            surf = font.render(text, True, (0, 255, 0))
            self.screen.blit(surf,   (10, y))
            y += 25