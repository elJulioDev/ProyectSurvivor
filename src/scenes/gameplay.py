"""
Escena de Gameplay REFACTORIZADA
La lógica del juego vive en LevelManager.
GameplayScene maneja UI, input y transiciones.

Controles móviles:
  · F5              → activa/desactiva modo móvil (debug)
  · Joystick izq.   → mover personaje
  · Joystick der.   → apuntar + disparo automático
  · Botón DASH      → ejecutar dash (si desbloqueado)
  · Botón II        → pausar
  · Tap en slot arma → cambiar arma activa
"""
import pygame
import sys
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, BLACK, WHITE
from managers.level_manager import LevelManager
from ui.hud import HUD
from ui.button import Button
from ui.mobile_controls import MobileControls


class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.level = LevelManager()
        self.hud   = HUD(self.screen)
        self.clock = pygame.time.Clock()
        self.dt    = 1.0
        self.target_fps = 60
        self.paused     = False

        self.font_pause = pygame.font.Font(None, 80)
        self.font_btn   = pygame.font.Font(None, 36)

        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.btn_continue = Button(cx, cy + 20,  200, 50, "Continuar",     self.font_btn)
        self.btn_exit     = Button(cx, cy + 90,  200, 50, "Salir del Juego", self.font_btn)

        self.show_debug      = False
        self.crosshair_scale = 1.0
        self.last_pulse_time = 0

        # ── Controles móviles ─────────────────────────────────────────────────
        self.mobile = MobileControls(WINDOW_WIDTH, WINDOW_HEIGHT)

    # ── Ciclo de vida ─────────────────────────────────────────────────────────

    def on_enter(self):
        pygame.mouse.set_visible(False)
        self.level.initialize()
        self.paused          = False
        self.show_debug      = False
        self.crosshair_scale = 1.0

    def on_exit(self):
        if self.level:
            self.level.cleanup()
        pygame.mouse.set_visible(True)

    # ── Eventos ───────────────────────────────────────────────────────────────

    def handle_events(self, event):
        # F5 siempre disponible (toggle modo móvil)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            self.mobile.enabled = not self.mobile.enabled
            estado = "ACTIVADO ✔" if self.mobile.enabled else "desactivado"
            print(f"[DEBUG] Modo móvil: {estado}")
            pygame.mouse.set_visible(not self.mobile.enabled)
            return

        # ── Menú de pausa ─────────────────────────────────────────────────────
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)

            if self.btn_continue.is_clicked(event):
                self.paused = False
                pygame.mouse.set_visible(self.mobile.enabled)
            if self.btn_exit.is_clicked(event):
                pygame.mouse.set_visible(True)
                pygame.quit()
                sys.exit()
            return

        # ── Tap en slot de arma (móvil) ───────────────────────────────────────
        if self.mobile.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            vx, vy = self._vpos_from_event(event)
            slot_idx = self.mobile.check_weapon_slot_tap(vx, vy, self.level.player)
            if slot_idx >= 0 and self.level.player:
                self.level.player.current_weapon_index = slot_idx
                return   # evento consumido

        # ── Controles móviles (joysticks, dash, pausa) ────────────────────────
        vpos     = self._vpos_from_event(event)
        consumed = self.mobile.handle_event(event, vpos, self.level.player)
        if consumed:
            # Pausa desde botón móvil
            if self.mobile.pause_request:
                self.paused = True
                pygame.mouse.set_visible(True)
                self.mobile.pause_request = False
            return

        # ── Input del jugador (teclado) ────────────────────────────────────────
        if self.level.player and not self.paused:
            self.level.player.handle_event(event)

        # ── Teclas de escena ──────────────────────────────────────────────────
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
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            return

        # Subida de nivel
        if self.level.player and self.level.player.pending_level_ups > 0:
            self.level.player.pending_level_ups -= 1
            from scenes.upgrade import UpgradeScene
            pygame.mouse.set_visible(True)
            self.game.current_scene = UpgradeScene(self.game, self)
            return

        # Game over
        if self.level.game_over:
            pygame.mouse.set_visible(True)
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(
                self.game,
                self.level.score,
                self.level.spawn_manager.get_time_string()
            )
            return

        keys         = pygame.key.get_pressed()
        mouse_pos    = self.game.get_mouse_pos()
        mouse_pressed = pygame.mouse.get_pressed()

        # Actualizar estado de controles móviles ANTES de level.update
        self.mobile.update(self.level.player)

        # Dash desde botón móvil
        if self.mobile.enabled and self.mobile.dash_request:
            if self.level.player:
                mdx, mdy = self.mobile.movement
                self.level.player._execute_dash_with_vector(mdx, mdy)
            self.mobile.dash_request = False

        # Actualizar lógica del juego (pasa mobile para que controle input)
        self.level.update(self.dt, keys, mouse_pos, mouse_pressed,
                          mobile=self.mobile)

        # Limpiar flags de botones al final del frame
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

        # Controles táctiles (solo si están activados)
        self.mobile.render(self.screen, self.level.player)

        # Mira (ocultarla en modo móvil)
        if not self.paused and not self.mobile.enabled:
            self._render_crosshair()

        if self.paused:
            self._render_pause_menu()

        if self.show_debug:
            self._render_debug_info()

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _vpos_from_event(self, event) -> tuple:
        """
        Transforma event.pos a coordenadas virtuales del juego (1280×720).
        Para eventos FINGER, ya se convierten en mobile_controls.handle_event.
        """
        if hasattr(event, 'pos'):
            rx, ry = event.pos
            scale  = max(0.001, self.game.render_scale)
            vx     = (rx - self.game.render_offset_x) / scale
            vy     = (ry - self.game.render_offset_y) / scale
            return (vx, vy)
        # Fallback: posición actual del mouse virtual
        return self.game.get_mouse_pos()

    def _update_crosshair(self, mouse_pressed):
        if not self.level.player:
            return

        player_shot_time = self.level.player.last_shot_time

        if player_shot_time != self.last_pulse_time:
            current_weapon   = self.level.player.weapons[self.level.player.current_weapon_index]
            pulse_intensity  = 0.3 + (current_weapon.shake_amount * 0.15)
            self.crosshair_scale += pulse_intensity
            self.last_pulse_time  = player_shot_time

        if self.crosshair_scale > 4.0:
            self.crosshair_scale = 4.0

        self.crosshair_scale += (1.0 - self.crosshair_scale) * 0.08 * self.dt

    def _render_crosshair(self):
        mx, my = self.game.get_mouse_pos()

        from settings import (CROSSHAIR_COLOR, CROSSHAIR_SIZE,
                              CROSSHAIR_GAP, CROSSHAIR_THICKNESS, CROSSHAIR_DOT_SIZE)

        current_gap  = CROSSHAIR_GAP  * self.crosshair_scale
        current_size = CROSSHAIR_SIZE * self.crosshair_scale

        dot_rect = pygame.Rect(0, 0, CROSSHAIR_DOT_SIZE, CROSSHAIR_DOT_SIZE)
        dot_rect.center = (mx, my)
        pygame.draw.rect(self.screen, CROSSHAIR_COLOR, dot_rect)

        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my - current_gap - current_size),
                         (mx, my - current_gap), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my + current_gap),
                         (mx, my + current_gap + current_size), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx - current_gap - current_size, my),
                         (mx - current_gap, my), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx + current_gap, my),
                         (mx + current_gap + current_size, my), CROSSHAIR_THICKNESS)

    def _render_pause_menu(self):
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        text = self.font_pause.render("PAUSA", True, WHITE)
        rect = text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 80))
        self.screen.blit(text, rect)

        self.btn_continue.draw(self.screen)
        self.btn_exit.draw(self.screen)

    def _render_debug_info(self):
        font   = pygame.font.Font(None, 24)
        fps    = self.clock.get_fps()
        dt_ms  = self.dt * (1000.0 / self.target_fps)
        d      = self.level.get_debug_info()

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
            self.screen.blit(surf, (10, y))
            y += 25