"""
HUD - Heads Up Display Minimalista y Profesional (Versión Flat)
"""

import pygame
import math

class HUD:
    def __init__(self, screen):
        self.screen = screen
        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()
        
        # Fuentes limpias
        self.font_wave = pygame.font.Font(None, 64)
        self.font_score = pygame.font.Font(None, 48)
        self.font_stats = pygame.font.Font(None, 32)
        self.font_health = pygame.font.Font(None, 24)
        
        # Variables de animación
        self.damage_bar_health = 0
        self.health_icon_pulse = 0.0
        self.health_icon_base_size = 12  # Más pequeña
        
        # Colores Planos (Sin degradados ni brillos)
        self.COLOR_BLACK = (15, 15, 15)      # Fondo oscuro casi negro
        self.COLOR_WHITE = (255, 255, 255)
        self.COLOR_RED = (235, 60, 60)       # Rojo vibrante flat
        self.COLOR_DARK_RED = (140, 30, 30)  # Rojo oscuro flat
        self.COLOR_GREEN = (46, 204, 113)    # Verde Emerald flat
        self.COLOR_YELLOW = (241, 196, 15)   # Amarillo Sunflower flat
        self.COLOR_CYAN = (0, 255, 255)      # Cyan flat
        self.COLOR_GRAY_DARK = (40, 40, 40)  # Gris para fondos inactivos
        
    def render(self, player, wave=1, score=0, enemies_alive=0, dt=1.0):
        if not player: return
        self._update_animations(player, dt)
        self._render_status_bars(player, dt)
        self._render_wave_info(wave)
        self._render_stats(score, enemies_alive)
    
    def _update_animations(self, player, dt):
        # Inicialización
        if self.damage_bar_health == 0: 
            self.damage_bar_health = player.health

        # Animación Smooth de barra de daño
        if self.damage_bar_health > player.health:
            diff = self.damage_bar_health - player.health
            # Velocidad de caída
            self.damage_bar_health -= diff * 0.1 * dt
            # Snap al final si está muy cerca
            if abs(self.damage_bar_health - player.health) < 0.5:
                self.damage_bar_health = player.health
        else:
            self.damage_bar_health = player.health

    def _get_health_color(self, pct):
        if pct > 0.5: return self.COLOR_GREEN
        elif pct > 0.25: return self.COLOR_YELLOW
        return self.COLOR_RED

    def _render_status_bars(self, player, dt):
        start_x = 30
        start_y = 30
        
        # --- 1. CRUZ (Izquierda) ---
        hp_pct = max(0, player.health / player.max_health)
        color = self._get_health_color(hp_pct)
        
        # Pulsación Aggressive: Muy rápida si la vida es baja
        # Base: 2.0 | Max (low hp): 10.0
        pulse_speed = 2.0 + (1.0 - hp_pct) * 8.0 
        self.health_icon_pulse += pulse_speed * (dt * 0.016)
        
        # Cálculo de escala "snappy" (golpe rápido)
        pulse = (math.sin(self.health_icon_pulse) + 1) * 0.5
        scale_intensity = 0.2 + (1.0 - hp_pct) * 0.5 # Más intenso si hay poca vida
        scale = 1.0 + (pulse * scale_intensity)
        
        current_size = int(self.health_icon_base_size * scale)
        icon_cx = start_x + 10
        icon_cy = start_y + 12 # Centrado con barra de 24px
        
        # Cruz gruesa y pequeña
        thickness = max(4, int(5 * scale)) # Espesor constante grueso
        
        # Dibujar cruz
        pygame.draw.line(self.screen, color, (icon_cx, icon_cy - current_size), (icon_cx, icon_cy + current_size), thickness)
        pygame.draw.line(self.screen, color, (icon_cx - current_size, icon_cy), (icon_cx + current_size, icon_cy), thickness)

        # --- 2. BARRA DE SALUD (Plana) ---
        bar_x = start_x + 40
        bar_w = 280
        bar_h = 24
        
        # Fondo contenedor (Gris oscuro plano)
        pygame.draw.rect(self.screen, self.COLOR_BLACK, (bar_x, start_y, bar_w, bar_h))
        
        # Barra Daño (Roja oscura flat)
        dmg_w = int(bar_w * (self.damage_bar_health / player.max_health))
        if dmg_w > 0:
            pygame.draw.rect(self.screen, self.COLOR_DARK_RED, (bar_x, start_y, dmg_w, bar_h))
            
        # Barra Vida (Color flat)
        hp_w = int(bar_w * hp_pct)
        if hp_w > 0:
            pygame.draw.rect(self.screen, color, (bar_x, start_y, hp_w, bar_h))
            
        # Borde simple (Opcional, para definición)
        pygame.draw.rect(self.screen, self.COLOR_GRAY_DARK, (bar_x, start_y, bar_w, bar_h), 1)

        # Número de vida
        txt = self.font_health.render(str(int(player.health)), True, self.COLOR_WHITE)
        self.screen.blit(txt, (bar_x + bar_w + 10, start_y + 4))

        # --- 3. BARRA DE DASH (Plana) ---
        dash_y = start_y + bar_h + 8
        dash_h = 8 # Ligeramente más gruesa para que se vea bien en flat
        
        dash_pct = 1.0
        if player.dash_cooldown > 0:
            dash_pct = 1.0 - (player.dash_cooldown_timer / player.dash_cooldown)
            
        # Fondo Dash
        pygame.draw.rect(self.screen, self.COLOR_BLACK, (bar_x, dash_y, bar_w, dash_h))
        
        # Relleno Dash (Cyan flat)
        dash_fill_w = int(bar_w * dash_pct)
        dash_c = self.COLOR_CYAN if dash_pct >= 0.99 else self.COLOR_GRAY_DARK
        
        if dash_fill_w > 0:
            pygame.draw.rect(self.screen, dash_c, (bar_x, dash_y, dash_fill_w, dash_h))

    def _render_wave_info(self, wave):
        txt = f"WAVE {wave}"
        # Sombra sólida sin difuminado
        shadow = self.font_wave.render(txt, True, self.COLOR_BLACK)
        surf = self.font_wave.render(txt, True, self.COLOR_WHITE)
        
        cx = self.screen_width // 2 - surf.get_width() // 2
        self.screen.blit(shadow, (cx + 3, 23))
        self.screen.blit(surf, (cx, 20))

    def _render_stats(self, score, enemies):
        margin = 30
        
        # Score
        s_txt = f"{int(score):06d}"
        s_surf = self.font_score.render(s_txt, True, self.COLOR_WHITE)
        s_shadow = self.font_score.render(s_txt, True, self.COLOR_BLACK)
        
        sx = self.screen_width - margin - s_surf.get_width()
        self.screen.blit(s_shadow, (sx + 2, 27))
        self.screen.blit(s_surf, (sx, 25))
        
        # Enemies
        e_txt = f"{enemies} ENEMIGOS"
        e_surf = self.font_stats.render(e_txt, True, self.COLOR_RED)
        e_shadow = self.font_stats.render(e_txt, True, self.COLOR_BLACK)
        
        ex = self.screen_width - margin - e_surf.get_width()
        ey = 25 + 40
        self.screen.blit(e_shadow, (ex + 1, ey + 1))
        self.screen.blit(e_surf, (ex, ey))
