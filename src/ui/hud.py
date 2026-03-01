"""
HUD - Rediseñado: jerarquía clara, sin solapamientos, estética pulida
Layout:
  - Barra XP + Nivel: franja superior completa
  - Temporizador: top center, bien separado del nivel
  - Panel salud + dash: top left
  - Panel score + enemigos: top right
  - Arma activa: bottom center
"""

import pygame, math

class Palette:
    BG          = (10, 10, 14)
    BG_PANEL    = (18, 18, 26)
    BORDER      = (45, 45, 65)
    BORDER_LIT  = (80, 80, 110)

    WHITE       = (235, 235, 245)
    GRAY        = (110, 110, 130)
    DIM         = (55, 55, 70)

    HP_HIGH     = (46, 204, 113)
    HP_MID      = (241, 196, 15)
    HP_LOW      = (231, 76, 60)
    HP_SHADOW   = (100, 20, 10)

    DASH_READY  = (0, 210, 255)
    DASH_EMPTY  = (30, 40, 55)

    XP_FILL     = (80, 140, 255)
    XP_BG       = (15, 20, 40)
    XP_GLOW     = (50, 90, 200)

    SCORE       = (255, 220, 60)
    TIME        = (200, 210, 230)

    ENEMIES     = (220, 80, 60)


class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.W = screen.get_width()
        self.H = screen.get_height()
        self.f_huge   = pygame.font.Font(None, 72)   # timer
        self.f_large  = pygame.font.Font(None, 48)   # score
        self.f_medium = pygame.font.Font(None, 34)   # labels
        self.f_small  = pygame.font.Font(None, 26)   # detalles
        self.f_tiny   = pygame.font.Font(None, 22)   # sub-labels
        self._damage_health  = 0.0    # barra de daño suavizada
        self._hp_pulse       = 0.0
        self._score_display  = 0.0    # contador animado
        self._score_target   = 0.0
        self._xp_anim        = 0.0    # glow de barra XP al subir nivel
        self._level_prev     = 1
        self._time_pulse     = 0.0
        self._weapon_flash   = 0.0
        self._panel_cache = {}

    def render(self, player, wave_time_str, score=0, enemies_alive=0, dt=1.0):
        if not player:
            return

        self._update_state(player, score, dt)

        self._render_xp_strip(player)          # franja superior
        self._render_timer(wave_time_str)       # centro top (bajo la franja)
        self._render_health_panel(player, dt)   # panel izquierdo
        self._render_score_panel(enemies_alive) # panel derecho
        self._render_weapon_indicator(player)   # bottom center

    def _update_state(self, player, score, dt):
        # Inicialización
        if self._damage_health == 0.0:
            self._damage_health = player.health

        # Barra de daño suavizada
        if self._damage_health > player.health:
            diff = self._damage_health - player.health
            self._damage_health -= max(diff * 0.08 * dt, 0.3)
            if self._damage_health < player.health:
                self._damage_health = player.health
        else:
            self._damage_health = player.health

        # Contador de score animado (sube suavemente)
        self._score_target = float(score)
        gap = self._score_target - self._score_display
        if abs(gap) > 0.5:
            self._score_display += gap * 0.12 * dt
        else:
            self._score_display = self._score_target

        # Pulso de salud (más rápido con poca vida)
        hp_pct = player.health / player.max_health
        pulse_speed = 1.5 + (1.0 - hp_pct) * 6.0
        self._hp_pulse += pulse_speed * dt * 0.016

        # Glow al subir de nivel
        if player.level != self._level_prev:
            self._xp_anim = 1.0
            self._level_prev = player.level
        if self._xp_anim > 0:
            self._xp_anim -= 0.02 * dt
            if self._xp_anim < 0:
                self._xp_anim = 0.0

        self._time_pulse += 0.04 * dt

    def _render_xp_strip(self, player):
        STRIP_H = 20
        pct = player.experience / max(1, player.experience_next_level)
        fill_w = int(self.W * pct)

        # Fondo
        pygame.draw.rect(self.screen, Palette.XP_BG, (0, 0, self.W, STRIP_H))

        # Relleno XP
        if fill_w > 2:
            pygame.draw.rect(self.screen, Palette.XP_FILL, (0, 0, fill_w, STRIP_H))

        # Glow al subir nivel
        if self._xp_anim > 0:
            glow_alpha = int(self._xp_anim * 200)
            glow_surf = pygame.Surface((self.W, STRIP_H), pygame.SRCALPHA)
            glow_surf.fill((*Palette.XP_GLOW, glow_alpha))
            self.screen.blit(glow_surf, (0, 0))

        # Borde inferior sutil
        pygame.draw.line(self.screen, Palette.BORDER_LIT,
                         (0, STRIP_H - 1), (self.W, STRIP_H - 1), 1)

        # Pastilla de NIVEL centrada sobre la barra
        lv_text = f"LVL {player.level}"
        lv_surf = self.f_small.render(lv_text, True, Palette.WHITE)
        lw, lh = lv_surf.get_size()

        pad_x, pad_y = 14, 3
        pill_w = lw + pad_x * 2
        pill_h = lh + pad_y * 2
        pill_x = self.W // 2 - pill_w // 2
        pill_y = STRIP_H + 4

        # Fondo pastilla
        self._draw_panel(pill_x, pill_y, pill_w, pill_h, radius=8,
                         bg=Palette.BG_PANEL, border=Palette.BORDER_LIT)

        # Texto nivel
        self.screen.blit(lv_surf, (pill_x + pad_x, pill_y + pad_y))

    def _render_timer(self, time_str):
        # Posición: centrado horizontalmente, debajo de la pastilla de nivel
        TIME_Y = 60

        # Leve pulso de opacidad
        alpha_mod = int(220 + math.sin(self._time_pulse) * 30)
        color = (
            min(255, int(Palette.TIME[0] * alpha_mod / 255)),
            min(255, int(Palette.TIME[1] * alpha_mod / 255)),
            min(255, int(Palette.TIME[2] * alpha_mod / 255)),
        )

        # Sombra
        shadow = self.f_huge.render(time_str, True, (0, 0, 0))
        surf   = self.f_huge.render(time_str, True, color)

        cx = self.W // 2 - surf.get_width() // 2
        self.screen.blit(shadow, (cx + 2, TIME_Y + 2))
        self.screen.blit(surf,   (cx, TIME_Y))

    def _render_health_panel(self, player, dt):
        PANEL_X = 16
        PANEL_Y = 28
        PANEL_W = 310
        PANEL_H = 68

        self._draw_panel(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, radius=10,
                         bg=Palette.BG_PANEL, border=Palette.BORDER)

        hp_pct = max(0.0, player.health / player.max_health)
        dmg_pct = max(0.0, self._damage_health / player.max_health)
        hp_color = self._get_hp_color(hp_pct)

        # Icono cruz animada
        icon_cx = PANEL_X + 22
        icon_cy = PANEL_Y + 22

        scale_intensity = 0.15 + (1.0 - hp_pct) * 0.45
        pulse = (math.sin(self._hp_pulse) + 1) * 0.5
        scale = 1.0 + pulse * scale_intensity
        arm = int(9 * scale)
        thick = max(3, int(5 * scale))

        pygame.draw.line(self.screen, hp_color,
                         (icon_cx, icon_cy - arm),
                         (icon_cx, icon_cy + arm), thick)
        pygame.draw.line(self.screen, hp_color,
                         (icon_cx - arm, icon_cy),
                         (icon_cx + arm, icon_cy), thick)

        # Barra de salud
        BAR_X = PANEL_X + 42
        BAR_Y = PANEL_Y + 12
        BAR_W = PANEL_W - 55
        BAR_H = 20

        # Fondo
        pygame.draw.rect(self.screen, Palette.BG,
                         (BAR_X, BAR_Y, BAR_W, BAR_H), border_radius=4)

        # Barra daño (rojo fantasma)
        dmg_w = int(BAR_W * dmg_pct)
        if dmg_w > 0:
            pygame.draw.rect(self.screen, Palette.HP_SHADOW,
                             (BAR_X, BAR_Y, dmg_w, BAR_H), border_radius=4)

        # Barra vida
        hp_w = int(BAR_W * hp_pct)
        if hp_w > 0:
            pygame.draw.rect(self.screen, hp_color,
                             (BAR_X, BAR_Y, hp_w, BAR_H), border_radius=4)

        # Número de HP
        hp_str = f"{int(player.health)} / {int(player.max_health)}"
        hp_surf = self.f_tiny.render(hp_str, True, Palette.GRAY)
        self.screen.blit(hp_surf,
                         (BAR_X + BAR_W // 2 - hp_surf.get_width() // 2,
                          BAR_Y + 3))

        # Label
        label = self.f_tiny.render("SALUD", True, Palette.DIM)
        self.screen.blit(label, (BAR_X, BAR_Y - 14))

        # Barra dash
        DASH_Y = BAR_Y + BAR_H + 8

        dash_pct = 1.0
        if player.dash_unlocked and player.dash_cooldown > 0:
            dash_pct = 1.0 - (player.dash_cooldown_timer / player.dash_cooldown)

        DASH_H = 8
        pygame.draw.rect(self.screen, Palette.BG,
                         (BAR_X, DASH_Y, BAR_W, DASH_H), border_radius=3)

        dash_fill = int(BAR_W * dash_pct)
        if dash_fill > 0:
            if not player.dash_unlocked:
                dash_color = Palette.DIM
            elif dash_pct >= 0.99:
                dash_color = Palette.DASH_READY
            else:
                dash_color = (30, 90, 130)
            pygame.draw.rect(self.screen, dash_color,
                             (BAR_X, DASH_Y, dash_fill, DASH_H), border_radius=3)

        dash_lbl = "DASH — BLOQUEADO" if not player.dash_unlocked else \
                   ("DASH — LISTO" if dash_pct >= 0.99 else "DASH  recargando…")
        dash_color_lbl = Palette.DASH_READY if (player.dash_unlocked and dash_pct >= 0.99) \
                         else Palette.DIM
        dl = self.f_tiny.render(dash_lbl, True, dash_color_lbl)
        self.screen.blit(dl, (BAR_X, DASH_Y + DASH_H + 3))

    def _render_score_panel(self, enemies_alive):
        PANEL_W = 220
        PANEL_H = 68
        PANEL_X = self.W - PANEL_W - 16
        PANEL_Y = 28

        self._draw_panel(PANEL_X, PANEL_Y, PANEL_W, PANEL_H, radius=10,
                         bg=Palette.BG_PANEL, border=Palette.BORDER)

        # Score animado
        score_int = int(self._score_display)
        score_str = f"{score_int:,}".replace(",", ".")
        sc_surf = self.f_large.render(score_str, True, Palette.SCORE)
        sc_x = PANEL_X + PANEL_W - sc_surf.get_width() - 12
        self.screen.blit(sc_surf, (sc_x, PANEL_Y + 8))

        # Separador
        sep_y = PANEL_Y + PANEL_H // 2 + 4
        pygame.draw.line(self.screen, Palette.BORDER,
                         (PANEL_X + 10, sep_y), (PANEL_X + PANEL_W - 10, sep_y), 1)

        # Enemigos
        en_color = Palette.ENEMIES if enemies_alive > 0 else Palette.GRAY
        en_str = f"{enemies_alive} ENEMIGOS"
        en_surf = self.f_small.render(en_str, True, en_color)
        en_x = PANEL_X + PANEL_W - en_surf.get_width() - 12
        self.screen.blit(en_surf, (en_x, sep_y + 6))

    def _render_weapon_indicator(self, player):
        if not player.weapons:
            return

        SLOT_W = 54
        SLOT_H = 54
        GAP    = 8
        n      = len(player.weapons)
        total_w = n * SLOT_W + (n - 1) * GAP
        start_x = self.W // 2 - total_w // 2
        base_y  = self.H - SLOT_H - 20

        WEAPON_NAMES = {
            'PistolWeapon':       'PISTOLA',
            'ShotgunWeapon':      'ESCOPETA',
            'AssaultRifleWeapon': 'RIFLE',
            'LaserWeapon':        'LÁSER',
        }
        WEAPON_COLORS = {
            'PistolWeapon':       (0, 210, 210),
            'ShotgunWeapon':      (255, 140, 40),
            'AssaultRifleWeapon': (255, 220, 70),
            'LaserWeapon':        (100, 180, 255),
        }

        for i, weapon in enumerate(player.weapons):
            wtype = type(weapon).__name__
            is_active = (i == player.current_weapon_index)
            sx = start_x + i * (SLOT_W + GAP)

            # Fondo slot
            bg = Palette.BG_PANEL if not is_active else (25, 28, 45)
            border = WEAPON_COLORS.get(wtype, Palette.BORDER) if is_active \
                     else Palette.BORDER
            self._draw_panel(sx, base_y, SLOT_W, SLOT_H, radius=8,
                             bg=bg, border=border, border_w=2 if is_active else 1)

            # Número de tecla
            key_surf = self.f_small.render(str(i + 1), True,
                                           Palette.WHITE if is_active else Palette.DIM)
            self.screen.blit(key_surf, (sx + 6, base_y + 5))

            # Nombre del arma
            wname = WEAPON_NAMES.get(wtype, wtype[:4])
            wn_surf = self.f_tiny.render(wname, True,
                                         WEAPON_COLORS.get(wtype, Palette.GRAY)
                                         if is_active else Palette.DIM)
            wx = sx + SLOT_W // 2 - wn_surf.get_width() // 2
            self.screen.blit(wn_surf, (wx, base_y + SLOT_H - 18))

            # Barra de cooldown en el slot activo
            if is_active:
                cd_pct = 1.0
                if weapon.cooldown > 0:
                    cd_pct = 1.0 - (weapon.current_cooldown / weapon.cooldown)
                bar_w = int((SLOT_W - 10) * cd_pct)
                bar_y = base_y + SLOT_H - 6
                pygame.draw.rect(self.screen, Palette.BG,
                                 (sx + 5, bar_y, SLOT_W - 10, 4), border_radius=2)
                if bar_w > 0:
                    wc = WEAPON_COLORS.get(wtype, Palette.WHITE)
                    pygame.draw.rect(self.screen, wc,
                                     (sx + 5, bar_y, bar_w, 4), border_radius=2)

    # Utilidades
    def _get_hp_color(self, pct):
        if pct > 0.5:  return Palette.HP_HIGH
        if pct > 0.25: return Palette.HP_MID
        return Palette.HP_LOW

    def _draw_panel(self, x, y, w, h, radius=8, bg=None, border=None, border_w=1):
        """Dibuja un panel con fondo y borde redondeado"""
        rect = pygame.Rect(x, y, w, h)
        if bg:
            pygame.draw.rect(self.screen, bg, rect, border_radius=radius)
        if border:
            pygame.draw.rect(self.screen, border, rect,
                             border_w, border_radius=radius)