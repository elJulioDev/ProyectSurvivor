"""
Escena de Mejoras — con clock propio para limitarse a 60fps.
"""
import pygame
import random
import math
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, UPGRADES

RARITY_COLORS = {
    'common':    (160, 165, 175),
    'uncommon':  (80,  200,  80),
    'rare':      (60,  130, 255),
    'epic':      (190,  60, 255),
    'legendary': (255, 180,   0),
}
RARITY_BG = {
    'common':    (18,  19,  22),
    'uncommon':  (13,  26,  13),
    'rare':      (10,  14,  32),
    'epic':      (22,   8,  32),
    'legendary': (30,  20,   4),
}
RARITY_LABEL = {
    'common':    'COMUN',
    'uncommon':  'POCO COMUN',
    'rare':      'RARO',
    'epic':      'EPICO',
    'legendary': 'LEGENDARIO',
}
RARITY_WEIGHTS = {
    'common':    50,
    'uncommon':  28,
    'rare':      14,
    'epic':       5,
    'legendary':  3,
}

CATEGORY_LABEL = {
    'movement': 'MOVIMIENTO',
    'survival': 'SUPERVIVENCIA',
    'weapons':  'ARMAS',
    'xp':       'XP / GEMAS',
}
CATEGORY_COLOR = {
    'movement': (0,   210, 255),
    'survival': (255,  80,  80),
    'weapons':  (255, 200,  50),
    'xp':       (150,  80, 255),
}
CATEGORY_SHAPE = {
    'movement': 'arrow',
    'survival': 'cross',
    'weapons':  'diamond',
    'xp':       'gem',
}

CARD_W = 275
CARD_H = 340
CARD_GAP = 32
CARDS_Y = 185
TOTAL_CARDS_W = CARD_W * 3 + CARD_GAP * 2
CARDS_START_X = (WINDOW_WIDTH - TOTAL_CARDS_W) // 2


class UpgradeScene(Scene):
    def __init__(self, game, gameplay_scene):
        super().__init__(game)
        self.gameplay_scene = gameplay_scene

        # Clock propio — limita a 60fps
        self._clock = pygame.time.Clock()

        self.font_title  = pygame.font.Font(None, 58)
        self.font_sub    = pygame.font.Font(None, 30)
        self.font_name   = pygame.font.Font(None, 34)
        self.font_desc   = pygame.font.Font(None, 22)
        self.font_cat    = pygame.font.Font(None, 21)
        self.font_rarity = pygame.font.Font(None, 19)
        self.font_pick   = pygame.font.Font(None, 26)

        self.options = self._select_upgrades()
        self.hovered_idx = -1
        self.anim_timer = 0.0
        self.hover_scales = [1.0, 1.0, 1.0]

        self.fade_alpha = 255
        self.fade_speed = 18
        self.input_cooldown = 45

    def _select_upgrades(self):
        player = self.gameplay_scene.level.player
        available_keys = []
        available_weights = []

        for key, upg in UPGRADES.items():
            req = upg.get('requires')
            if req == 'dash_unlocked' and not player.dash_unlocked:
                continue
            if upg['type'] == 'unlock' and key == 'dash':
                if player.dash_unlocked:
                    continue
            elif upg['type'] == 'unlock_weapon':
                if upg['weapon_class'] in player.unlocked_weapons:
                    continue
            max_stacks = upg.get('max_stacks')
            if max_stacks is not None:
                current = player.upgrade_counts.get(key, 0)
                if current >= max_stacks:
                    continue
            if not upg.get('stackable', False):
                if player.upgrade_counts.get(key, 0) >= 1:
                    continue
            available_keys.append(key)
            rarity = upg.get('rarity', 'common')
            available_weights.append(RARITY_WEIGHTS.get(rarity, 20))

        chosen = []
        used_categories = set()
        keys_copy = list(available_keys)
        weights_copy = list(available_weights)

        attempts = 0
        while len(chosen) < 3 and keys_copy and attempts < 60:
            attempts += 1
            idx = random.choices(range(len(keys_copy)), weights=weights_copy, k=1)[0]
            key = keys_copy[idx]
            cat = UPGRADES[key].get('category', '')
            if cat not in used_categories or attempts > 30:
                chosen.append(key)
                used_categories.add(cat)
            keys_copy.pop(idx)
            weights_copy.pop(idx)

        while len(chosen) < 3:
            valid_stackables = []
            for k, v in UPGRADES.items():
                if v.get('stackable', False) and k not in chosen:
                    max_stacks = v.get('max_stacks')
                    current_stacks = player.upgrade_counts.get(k, 0)
                    if max_stacks is None or current_stacks < max_stacks:
                        valid_stackables.append(k)
            if valid_stackables:
                chosen.append(random.choice(valid_stackables))
            else:
                break

        return chosen[:3]

    def handle_events(self, event):
        mouse_pos = self.game.get_mouse_pos()

        self.hovered_idx = -1
        for i in range(len(self.options)):
            card_rect = self._get_card_rect(i)
            if card_rect.collidepoint(mouse_pos):
                self.hovered_idx = i

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.hovered_idx >= 0 and self.input_cooldown <= 0:
                self._apply_upgrade(self.options[self.hovered_idx])
                pygame.mouse.set_visible(self.gameplay_scene.mobile.enabled)
                self.game.current_scene = self.gameplay_scene

        if event.type == pygame.KEYDOWN and self.input_cooldown <= 0:
            if event.key == pygame.K_1 and len(self.options) >= 1:
                self._apply_upgrade(self.options[0])
                pygame.mouse.set_visible(self.gameplay_scene.mobile.enabled)
                self.game.current_scene = self.gameplay_scene
            elif event.key == pygame.K_2 and len(self.options) >= 2:
                self._apply_upgrade(self.options[1])
                pygame.mouse.set_visible(self.gameplay_scene.mobile.enabled)
                self.game.current_scene = self.gameplay_scene
            elif event.key == pygame.K_3 and len(self.options) >= 3:
                self._apply_upgrade(self.options[2])
                pygame.mouse.set_visible(self.gameplay_scene.mobile.enabled)
                self.game.current_scene = self.gameplay_scene

    def _apply_upgrade(self, key):
        player    = self.gameplay_scene.level.player
        upg       = UPGRADES[key]
        proj_pool = self.gameplay_scene.level.projectile_pool

        player.upgrade_counts[key] = player.upgrade_counts.get(key, 0) + 1
        utype = upg['type']

        if utype == 'unlock' and key == 'dash':
            player.dash_unlocked = True
        elif utype == 'unlock_weapon':
            player.add_weapon(upg['weapon_class'], proj_pool)
        elif utype == 'stat':
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

        print(f"✅ Mejora aplicada: [{upg['rarity'].upper()}] {upg['name']}")

    def update(self):
        # Limitar a 60fps — necesario porque main.py ya no llama clock.tick()
        dt_ms = self._clock.tick(60)
        dt = dt_ms / 16.667

        self.anim_timer += 0.04 * dt

        if self.fade_alpha > 0:
            self.fade_alpha = max(0, self.fade_alpha - self.fade_speed * dt)

        if self.input_cooldown > 0:
            self.input_cooldown -= dt

        mouse_pos = self.game.get_mouse_pos()
        self.hovered_idx = -1
        for i in range(len(self.options)):
            if self._get_card_rect(i).collidepoint(mouse_pos):
                self.hovered_idx = i

        for i in range(len(self.options)):
            target = 1.04 if i == self.hovered_idx else 1.0
            self.hover_scales[i] += (target - self.hover_scales[i]) * 0.15 * dt
            self.hover_scales[i] = max(0.98, min(1.06, self.hover_scales[i]))

    def render(self):
        self.gameplay_scene.render()

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))

        player_level = self.gameplay_scene.level.player.level
        self._draw_title(player_level)

        sub_surf = self.font_sub.render(
            "Elige una mejora   |   Teclas 1  2  3",
            True, (100, 105, 120)
        )
        self.screen.blit(sub_surf, (WINDOW_WIDTH // 2 - sub_surf.get_width() // 2, 140))

        for i, key in enumerate(self.options):
            self._draw_card(i, key)

        if self.fade_alpha > 0:
            fade_surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            fade_surf.fill((0, 0, 0, int(self.fade_alpha)))
            self.screen.blit(fade_surf, (0, 0))

    def _draw_title(self, level):
        glow_val = int(abs(math.sin(self.anim_timer)) * 40 + 180)
        title_color = (255, glow_val, 40)
        title_str = f"NIVEL {level} ALCANZADO"
        shadow = self.font_title.render(title_str, True, (80, 40, 0))
        title  = self.font_title.render(title_str, True, title_color)
        cx = WINDOW_WIDTH // 2
        self.screen.blit(shadow, (cx - shadow.get_width() // 2 + 3, 73))
        self.screen.blit(title,  (cx - title.get_width()  // 2,     70))

    def _get_card_rect(self, index):
        x = CARDS_START_X + index * (CARD_W + CARD_GAP)
        return pygame.Rect(x, CARDS_Y, CARD_W, CARD_H)

    def _draw_card(self, index, key):
        upg    = UPGRADES[key]
        rarity = upg.get('rarity', 'common')
        cat    = upg.get('category', 'weapons')

        rc        = RARITY_COLORS.get(rarity,  (150, 150, 150))
        rbg       = RARITY_BG.get(rarity,      (18,  18,  22))
        cat_color = CATEGORY_COLOR.get(cat, (150, 150, 150))

        is_hovered = (index == self.hovered_idx)
        scale      = self.hover_scales[index]

        base_x = CARDS_START_X + index * (CARD_W + CARD_GAP)
        base_y = CARDS_Y

        cw = int(CARD_W * scale)
        ch = int(CARD_H * scale)
        cx = base_x + CARD_W // 2
        cy = base_y + CARD_H // 2
        x  = cx - cw // 2
        y  = cy - ch // 2

        card_rect = pygame.Rect(x, y, cw, ch)

        shadow_surf = pygame.Surface((cw + 20, ch + 20), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 120), (0, 0, cw + 20, ch + 20))
        self.screen.blit(shadow_surf, (x - 10 + 8, y - 10 + 8))

        glow_alpha = 80 if is_hovered else 30
        if is_hovered:
            pulse = abs(math.sin(self.anim_timer * 3))
            glow_alpha = int(60 + pulse * 50)
        glow_surf = pygame.Surface((cw + 30, ch + 30), pygame.SRCALPHA)
        pygame.draw.rect(glow_surf, (*rc, glow_alpha), (0, 0, cw + 30, ch + 30))
        self.screen.blit(glow_surf, (x - 15, y - 15))

        pygame.draw.rect(self.screen, rbg, card_rect)
        pygame.draw.rect(self.screen, cat_color, (x, y, cw, 5))

        border_w = 2 if not is_hovered else 3
        pygame.draw.rect(self.screen, rc, card_rect, border_w)

        inner = card_rect.inflate(-6, -6)
        pygame.draw.rect(self.screen, (*rc, 30), inner, 1)

        num_surf = self.font_pick.render(str(index + 1), True, (60, 65, 75))
        self.screen.blit(num_surf, (x + 10, y + 10))

        rlabel = RARITY_LABEL.get(rarity, rarity.upper())
        rl_surf = self.font_rarity.render(rlabel, True, rc)
        self.screen.blit(rl_surf, (x + cw - rl_surf.get_width() - 10, y + 12))

        icon_cx = x + cw // 2
        icon_cy = y + 65
        self._draw_category_icon(icon_cx, icon_cy, cat, cat_color, scale * 22)

        cat_label = CATEGORY_LABEL.get(cat, cat.upper())
        cl_surf = self.font_cat.render(cat_label, True, cat_color)
        self.screen.blit(cl_surf,
                         (x + cw // 2 - cl_surf.get_width() // 2, y + 95))

        sep_y = y + 115
        sep_surf = pygame.Surface((cw - 32, 1), pygame.SRCALPHA)
        sep_surf.fill((*rc, 60))
        self.screen.blit(sep_surf, (x + 16, sep_y))

        name_surf = self.font_name.render(upg['name'], True, (235, 235, 245))
        name_x = x + cw // 2 - name_surf.get_width() // 2
        self.screen.blit(name_surf, (name_x, sep_y + 10))

        self._draw_wrapped_text(
            upg['desc'],
            self.font_desc,
            (160, 165, 175),
            x + 14, sep_y + 42,
            cw - 28,
            line_height=20
        )

        if is_hovered:
            pulse = abs(math.sin(self.anim_timer * 4))
            pick_color = (min(255, rc[0]), min(255, rc[1]), min(255, rc[2]))
            pick_surf = self.font_pick.render("ELEGIR", True, pick_color)
            px_ = x + cw // 2 - pick_surf.get_width() // 2
            py_ = y + ch - 32
            btn_bg = pygame.Surface((pick_surf.get_width() + 20, 26), pygame.SRCALPHA)
            btn_bg.fill((*rc, 30))
            self.screen.blit(btn_bg, (px_ - 10, py_ - 3))
            self.screen.blit(pick_surf, (px_, py_))
            pygame.draw.line(self.screen, rc, (x, y + ch - 1), (x + cw, y + ch - 1), 2)
        else:
            idle_surf = self.font_rarity.render(f"Tecla  {index + 1}", True, (50, 55, 65))
            self.screen.blit(idle_surf,
                             (x + cw // 2 - idle_surf.get_width() // 2,
                              y + ch - 22))

    def _draw_category_icon(self, cx, cy, category, color, size):
        s = int(size)
        shape = CATEGORY_SHAPE.get(category, 'diamond')

        if shape == 'arrow':
            pts = [
                (cx - s, cy - s * 0.7),
                (cx - s, cy + s * 0.7),
                (cx + s, cy),
            ]
            pygame.draw.polygon(self.screen, color, pts)
            pygame.draw.polygon(self.screen, (255, 255, 255), pts, 2)

        elif shape == 'cross':
            w = max(3, s // 3)
            pygame.draw.rect(self.screen, color, (cx - w, cy - s, w * 2, s * 2))
            pygame.draw.rect(self.screen, color, (cx - s, cy - w, s * 2, w * 2))

        elif shape == 'diamond':
            pts = [
                (cx,     cy - s),
                (cx + s, cy),
                (cx,     cy + s),
                (cx - s, cy),
            ]
            pygame.draw.polygon(self.screen, color, pts)
            pygame.draw.polygon(self.screen, (255, 255, 255), pts, 2)

        elif shape == 'gem':
            pts = []
            for i in range(6):
                a = math.radians(i * 60 - 30)
                r = s if i % 2 == 0 else s * 0.7
                pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
            pygame.draw.polygon(self.screen, color, pts)
            pygame.draw.polygon(self.screen, (255, 255, 255), pts, 2)

    def _draw_wrapped_text(self, text, font, color, x, y, max_width, line_height=22):
        words = text.split()
        lines = []
        current = []
        for word in words:
            test = ' '.join(current + [word])
            if font.size(test)[0] <= max_width:
                current.append(word)
            else:
                if current:
                    lines.append(' '.join(current))
                current = [word]
        if current:
            lines.append(' '.join(current))
        for i, line in enumerate(lines):
            surf = font.render(line, True, color)
            self.screen.blit(surf, (x, y + i * line_height))