"""
GameplayScene optimizado:
- TARGET_FPS configurable: 60 / 120 / 240 / 0 (sin límite).
- dt siempre normalizado a unidades de 60fps (1.0 = 1 frame a 60fps).
- LevelManager.set_target_fps() llamado al iniciar para escalar intervalos.
- F6: ciclo entre 60 / 120 / 240 / 0fps en tiempo real.
- F7: [DEBUG] aplica TODAS las mejoras al jugador + nivel 999.
- Cruce de delta-time máximo reducido a 2.5 para evitar micro-freezes.

PARCHE 2: MOBILE_CAMERA_ZOOM aplicado en on_enter() cuando se detecta móvil.
"""
import pygame
import math
from scenes.scene   import Scene
from settings       import WINDOW_WIDTH, WINDOW_HEIGHT, BLACK, WHITE, UPGRADES
from managers.level_manager  import LevelManager
from ui.hud          import HUD
from ui.mobile_controls import MobileControls

# FPS objetivo por defecto — cambiar aquí o con F6 en juego
DEFAULT_TARGET_FPS = 60

def _detect_mobile() -> bool:
    try:
        from utils.platform_detect import is_mobile
        return is_mobile()
    except ImportError:
        import sys, os
        if sys.platform == 'android':
            return True
        try:
            import android
            return True
        except ImportError:
            pass
        return False


class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.level      = LevelManager()
        self.hud        = HUD(self.screen)
        self.clock      = pygame.time.Clock()

        self.target_fps = DEFAULT_TARGET_FPS   # 0 = uncapped
        self.dt         = 1.0
        self._dt_norm   = 1000.0 / 60.0        # ms por "frame lógico" (fijo a 60)

        self.show_debug      = False
        self.crosshair_scale = 1.0
        self.last_pulse_time = 0

        self.mobile = MobileControls(WINDOW_WIDTH, WINDOW_HEIGHT)
        if _detect_mobile():
            self.mobile.enabled = True
            print("[Platform] Android detectado — controles táctiles activados.")

    def on_enter(self):
        pygame.mouse.set_visible(self.mobile.enabled)
        self.level.initialize()
        self.level.set_target_fps(self.target_fps if self.target_fps > 0 else 60)
        self.show_debug      = False
        self.crosshair_scale = 1.0

        # PARCHE 2: aplicar MOBILE_CAMERA_ZOOM cuando se ejecuta en móvil
        if self.mobile.enabled:
            from settings import MOBILE_CAMERA_ZOOM
            self.level.camera.zoom = MOBILE_CAMERA_ZOOM
        else:
            self.level.camera.zoom = 1.0

    def on_exit(self):
        if self.level:
            self.level.cleanup()
        pygame.mouse.set_visible(True)

    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F5:
            self.mobile.enabled = not self.mobile.enabled
            print(f"[DEBUG] Modo móvil: {'ON' if self.mobile.enabled else 'OFF'}")
            pygame.mouse.set_visible(self.mobile.enabled)
            # Re-aplicar zoom al cambiar modo
            if self.mobile.enabled:
                from settings import MOBILE_CAMERA_ZOOM
                self.level.camera.zoom = MOBILE_CAMERA_ZOOM
            else:
                self.level.camera.zoom = 1.0
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_F6:
            fps_cycle = [60, 120, 240, 0]
            idx = fps_cycle.index(self.target_fps) if self.target_fps in fps_cycle else 0
            self.target_fps = fps_cycle[(idx + 1) % len(fps_cycle)]
            fps_label = str(self.target_fps) if self.target_fps > 0 else "ILIMITADO"
            print(f"[DEBUG] FPS objetivo: {fps_label}")
            self.level.set_target_fps(self.target_fps if self.target_fps > 0 else 60)
            return

        # F7: aplicar todas las mejoras + nivel 999
        if event.type == pygame.KEYDOWN and event.key == pygame.K_F7:
            if self.level.player:
                self._apply_all_upgrades_debug()
            return

        vpos = self._vpos_from_event(event)

        if self.mobile.enabled and event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            slot_idx = self.mobile.check_weapon_slot_tap(vpos[0], vpos[1],
                                                          self.level.player)
            if slot_idx >= 0 and self.level.player:
                self.level.player.current_weapon_index = slot_idx
                return

        consumed = self.mobile.handle_event(event, vpos, self.level.player)
        if consumed:
            if self.mobile.pause_request:
                self._open_pause()
                self.mobile.pause_request = False
            return

        if self.level.player:
            self.level.player.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.mouse.set_visible(True)
                from scenes.menu import MenuScene
                self.next_scene = MenuScene(self.game)
            elif event.key in (pygame.K_RETURN, pygame.K_p):
                self._open_pause()
            elif event.key == pygame.K_x:
                self.show_debug = not self.show_debug

    def _apply_all_upgrades_debug(self):
        """
        [F7 DEBUG] Aplica TODAS las mejoras disponibles en UPGRADES al jugador
        y lo sube al nivel 999 sin pasar por la pantalla de selección.

        Reglas:
          · Mejoras con max_stacks → se aplican hasta el tope.
          · Mejoras sin max_stacks y stackable=False → se aplican 1 vez.
          · Desbloqueos de armas → se desbloquean si no lo están ya.
          · El jugador se pone en nivel 999 y pending_level_ups = 0.
        """
        player    = self.level.player
        proj_pool = self.level.projectile_pool

        print("\n========== [F7 DEBUG] APLICANDO TODAS LAS MEJORAS ==========")

        for key, upg in UPGRADES.items():
            utype = upg['type']

            # ── Desbloqueo de dash ────────────────────────────────────────
            if utype == 'unlock' and key == 'dash':
                if not player.dash_unlocked:
                    player.dash_unlocked = True
                    player.upgrade_counts[key] = 1
                    print(f"  ✅ {upg['name']} desbloqueado")
                continue

            # ── Desbloqueo de arma ───────────────────────────────────────
            if utype == 'unlock_weapon':
                wc = upg['weapon_class']
                if wc not in player.unlocked_weapons:
                    player.add_weapon(wc, proj_pool)
                    player.upgrade_counts[key] = 1
                    print(f"  ✅ Arma desbloqueada: {upg['name']}")
                continue

            # ── Mejoras de stat / weapon / xp ────────────────────────────
            max_stacks = upg.get('max_stacks')
            stackable  = upg.get('stackable', False)

            if max_stacks is not None:
                # Aplicar hasta el máximo de stacks
                already = player.upgrade_counts.get(key, 0)
                times   = max_stacks - already
            elif stackable:
                # Stackable sin límite explícito → aplicar 1 vez en debug
                already = player.upgrade_counts.get(key, 0)
                times   = 1 if already == 0 else 0
            else:
                # No stackable → solo 1 vez
                already = player.upgrade_counts.get(key, 0)
                times   = 1 if already == 0 else 0

            if times <= 0:
                continue

            for _ in range(times):
                self._apply_single_upgrade(player, key, upg)
            player.upgrade_counts[key] = player.upgrade_counts.get(key, 0) + times
            print(f"  ✅ [{upg.get('rarity','?').upper()}] {upg['name']}  ×{times}")

        # ── Nivel 999 sin menú de mejoras pendiente ──────────────────────
        player.level              = 999
        player.pending_level_ups  = 0
        player.experience         = 0
        player.experience_next_level = 999999   # prácticamente infinito

        print("=============================================================")
        print(f"[F7 DEBUG] ¡Listo! Jugador en nivel 999 con todas las mejoras.\n")

    def _apply_single_upgrade(self, player, key, upg):
        """Aplica UNA instancia de una mejora al jugador (lógica extraída de UpgradeScene)."""
        utype = upg['type']
        proj_pool = self.level.projectile_pool

        if utype == 'stat':
            sname = upg['stat_name']
            val   = upg['value']

            if sname == 'max_speed':
                player.max_speed *= val
                player.accel     *= val
            elif sname == 'max_health':
                player.max_health += val
                player.health = min(player.health + val, player.max_health)
            elif sname == 'health_regen':
                player.health_regen += val
            elif sname == 'damage_reduction':
                player.damage_reduction = min(0.75, player.damage_reduction + val)
            elif sname == 'lifesteal_chance':
                player.lifesteal_chance = min(1.0, player.lifesteal_chance + val)
            elif sname == 'emergency_regen':
                player.emergency_regen += val
            elif sname == 'invulnerable_mult':
                player.invulnerable_mult *= val
            elif sname == 'dash_cooldown':
                player.dash_cooldown = max(10, int(player.dash_cooldown * val))
            elif sname == 'dash_duration':
                player.dash_duration = int(player.dash_duration * val)
            elif sname == 'ninja_dash':
                player.ninja_dash = True
            elif sname == 'aura_damage':
                player.aura_damage += val
            elif sname == 'aura_radius':
                player.aura_radius += val
            elif sname == 'aura_damage_mult':
                player.aura_damage *= val
            elif sname == 'aura_knockback':
                player.aura_knockback = val

        elif utype == 'weapon':
            sname = upg['stat_name']
            val   = upg['value']
            if sname == 'global_damage_mult':      player.global_damage_mult    *= val
            elif sname == 'global_cooldown_mult':  player.global_cooldown_mult  *= val
            elif sname == 'projectile_speed_mult': player.projectile_speed_mult *= val
            elif sname == 'extra_penetration':     player.extra_penetration     += int(val)
            elif sname == 'projectile_size_mult':  player.projectile_size_mult  *= val
            elif sname == 'knockback_mult':        player.knockback_mult        *= val

        elif utype == 'xp':
            sname = upg['stat_name']
            val   = upg['value']
            if sname == 'magnet_range_mult':    player.magnet_range_mult *= val
            elif sname == 'xp_mult':            player.xp_mult           *= val
            elif sname == 'xp_on_kill_bonus':   player.xp_on_kill_bonus  += int(val)
            elif sname == 'magnet_speed_mult':  player.magnet_speed_mult *= val

    def _open_pause(self):
        from scenes.pause import PauseScene
        pygame.mouse.set_visible(True)
        self.game.current_scene = PauseScene(self.game, self)

    def update(self):
        elapsed_ms = self.clock.tick(self.target_fps)
        raw_dt     = elapsed_ms / self._dt_norm
        self.dt    = min(raw_dt, 2.5)

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

        if not self.mobile.enabled:
            self._render_crosshair()

        if self.show_debug:
            self._render_debug_info()

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
        shot_t = self.level.player.last_shot_time
        if shot_t != self.last_pulse_time:
            w = self.level.player.weapons[self.level.player.current_weapon_index]
            self.crosshair_scale += 0.3 + w.shake_amount * 0.15
            self.last_pulse_time  = shot_t
        self.crosshair_scale = min(self.crosshair_scale, 4.0)
        self.crosshair_scale += (1.0 - self.crosshair_scale) * 0.08 * self.dt

    def _render_crosshair(self):
        mx, my = self.game.get_mouse_pos()
        from settings import (CROSSHAIR_COLOR, CROSSHAIR_SIZE,
                               CROSSHAIR_GAP, CROSSHAIR_THICKNESS, CROSSHAIR_DOT_SIZE)
        g  = CROSSHAIR_GAP  * self.crosshair_scale
        sz = CROSSHAIR_SIZE * self.crosshair_scale
        dr = pygame.Rect(0, 0, CROSSHAIR_DOT_SIZE, CROSSHAIR_DOT_SIZE)
        dr.center = (mx, my)
        pygame.draw.rect(self.screen, CROSSHAIR_COLOR, dr)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR, (mx, my - g - sz), (mx, my - g),      CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR, (mx, my + g),      (mx, my + g + sz), CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR, (mx - g - sz, my), (mx - g, my),      CROSSHAIR_THICKNESS)
        pygame.draw.line(self.screen, CROSSHAIR_COLOR, (mx + g, my),      (mx + g + sz, my), CROSSHAIR_THICKNESS)

    def _render_debug_info(self):
        font  = pygame.font.Font(None, 24)
        fps   = self.clock.get_fps()
        dt_ms = self.dt * self._dt_norm
        d     = self.level.get_debug_info()
        fps_lbl = f"{self.target_fps}fps" if self.target_fps > 0 else "ILIMITADO"
        mobile_str = "ON [F5 desact.]" if self.mobile.enabled else "OFF [F5 act.]"

        q_labels = {0: "CRISIS (0)", 1: "MEDIO (1)", 2: "ALTO (2)"}
        q_str = q_labels.get(d.get('particle_quality', 2), "?")

        texts = [
            f"FPS real: {fps:.1f}  |  DeltaTime: {dt_ms:.2f}ms  |  Objetivo: {fps_lbl} [F6 ciclo]",
            f"Enemigos vivos: {d['enemies_total']} (Visibles: {d['enemies_rendered']})  |  Dead pool: {d['dead_pool_size']}",
            f"Proyectiles: {d['projectiles']}  |  Enemi: {d['enemy_projectiles']}",
            f"Partículas: {d['particles_active']} (render: {d['particles_rendered']}) / {d['particles_capacity']}  |  Calidad: {q_str}",
            f"Kills este frame: {d.get('kills_this_frame', 0)}  |  Gemas XP: {d['gems_count']}",
            f"Chunks: {d.get('chunks_active', '?')} activos / {d.get('chunks_total', '?')} en RAM  |  Zoom: {self.level.camera.zoom:.2f}",
            f"Móvil: {mobile_str}",
            f"[X] Toggle Debug  |  [F7] Todas las mejoras",
        ]
        y = 110
        for text in texts:
            sh = font.render(text, True, (0, 0, 0))
            sf = font.render(text, True, (0, 255, 0))
            self.screen.blit(sh, (11, y + 1))
            self.screen.blit(sf, (10, y))
            y += 25