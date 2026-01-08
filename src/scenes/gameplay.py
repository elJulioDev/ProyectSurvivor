"""
Escena de Gameplay REFACTORIZADA
La lógica del juego ahora vive en LevelManager
GameplayScene solo maneja UI, input y transiciones
"""
import pygame
import sys
from scenes.scene import Scene
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, BLACK, WHITE
from managers.level_manager import LevelManager
from ui.hud import HUD
from ui.button import Button

class GameplayScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.level = LevelManager()
        self.hud = HUD(self.screen)
        self.clock = pygame.time.Clock()
        self.dt = 1.0
        self.target_fps = 60
        self.paused = False
        self.font_pause = pygame.font.Font(None, 80)
        self.font_btn = pygame.font.Font(None, 36)
        cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
        self.btn_continue = Button(cx, cy + 20, 200, 50, "Continuar", self.font_btn)
        self.btn_exit = Button(cx, cy + 90, 200, 50, "Salir del Juego", self.font_btn)
        self.show_debug = False
        self.crosshair_scale = 1.0
        self.last_pulse_time = 0
    
    def on_enter(self):
        """Inicializa el nivel al entrar a la escena"""
        pygame.mouse.set_visible(False)
        self.level.initialize()
        self.paused = False
        self.show_debug = False
        self.crosshair_scale = 1.0
    
    def on_exit(self):
        """Se llama cuando salimos de la escena (al Menú o Game Over)"""
        if self.level:
            self.level.cleanup()
        pygame.mouse.set_visible(True)
    
    def handle_events(self, event):
        """Maneja eventos de input"""
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            
            if self.btn_continue.is_clicked(event):
                self.paused = False
                pygame.mouse.set_visible(False)
            if self.btn_exit.is_clicked(event):
                pygame.mouse.set_visible(True)
                pygame.quit()
                sys.exit()
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
            
            elif event.key == pygame.K_F3:
                self.show_debug = not self.show_debug
    
    def update(self):
        """Actualiza la escena"""
        raw_dt = self.clock.tick(self.target_fps) / (1000.0 / self.target_fps)
        self.dt = min(raw_dt, 3.0)
        
        if self.paused:
            mouse_pos = self.game.get_mouse_pos()
            self.btn_continue.update(mouse_pos)
            self.btn_exit.update(mouse_pos)
            return
        
        if self.level.game_over:
            pygame.mouse.set_visible(True)
            from scenes.game_over import GameOverScene
            self.next_scene = GameOverScene(
                self.game,
                self.level.score,
                self.level.wave_manager.current_wave
            )
            return
        
        keys = pygame.key.get_pressed()
        mouse_pos = self.game.get_mouse_pos()
        mouse_pressed = pygame.mouse.get_pressed()
        
        self.level.update(self.dt, keys, mouse_pos, mouse_pressed)
        self._update_crosshair(mouse_pressed)
    
    def _update_crosshair(self, mouse_pressed):
        """Actualiza la animación del crosshair"""
        if not self.level.player:
            return

        player_shot_time = self.level.player.last_shot_time
        
        if player_shot_time != self.last_pulse_time:
            current_weapon = self.level.player.weapons[self.level.player.current_weapon_index]
            pulse_intensity = 0.3 + (current_weapon.shake_amount * 0.15)
            self.crosshair_scale += pulse_intensity
            self.last_pulse_time = player_shot_time
        
        if self.crosshair_scale > 4.0:
            self.crosshair_scale = 4.0
        
        self.crosshair_scale += (1.0 - self.crosshair_scale) * 0.08 * self.dt
    
    def render(self):
        """Renderiza la escena completa"""
        self.screen.fill(BLACK)
        
        self.level.render_world(self.screen)
        
        if self.hud and self.level.player:
            self.hud.render(
                self.level.player,
                self.level.wave_manager.current_wave,
                self.level.score,
                len(self.level.enemies)
            )
        
        if self.level.wave_manager.is_wave_completed():
            self._render_wave_transition()
        
        if not self.paused:
            self._render_crosshair()
        
        if self.paused:
            self._render_pause_menu()
        
        if self.show_debug:
            self._render_debug_info()
    
    def _render_crosshair(self):
        """Renderiza el crosshair dinámico"""
        mx, my = self.game.get_mouse_pos()
        
        from settings import (CROSSHAIR_COLOR, CROSSHAIR_SIZE,
                              CROSSHAIR_GAP, CROSSHAIR_THICKNESS, CROSSHAIR_DOT_SIZE)
        
        current_gap = CROSSHAIR_GAP * self.crosshair_scale
        current_size = CROSSHAIR_SIZE * self.crosshair_scale
        
        dot_rect = pygame.Rect(0, 0, CROSSHAIR_DOT_SIZE, CROSSHAIR_DOT_SIZE)
        dot_rect.center = (mx, my)
        pygame.draw.rect(self.screen, CROSSHAIR_COLOR, dot_rect)
        
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my - current_gap - current_size),
                         (mx, my - current_gap),
                         CROSSHAIR_THICKNESS)
        
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx, my + current_gap),
                         (mx, my + current_gap + current_size),
                         CROSSHAIR_THICKNESS)
        
        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx - current_gap - current_size, my),
                         (mx - current_gap, my),
                         CROSSHAIR_THICKNESS)

        pygame.draw.line(self.screen, CROSSHAIR_COLOR,
                         (mx + current_gap, my),
                         (mx + current_gap + current_size, my),
                         CROSSHAIR_THICKNESS)
    
    def _render_wave_transition(self):
        """Renderiza la transición entre oleadas"""
        progress = self.level.wave_manager.get_completion_progress()
        alpha = int(255 * (1 - abs(progress - 0.5) * 2))
        
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        font = pygame.font.Font(None, 64)
        
        text = font.render(
            f"Oleada {self.level.wave_manager.current_wave - 1} Completada!",
            True,
            (0, 255, 0, alpha)
        )
        text_rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2))
        surf.blit(text, text_rect)
        self.screen.blit(surf, (0, 0))
    
    def _render_pause_menu(self):
        """Renderiza el menú de pausa"""
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        text = self.font_pause.render("PAUSA", True, WHITE)
        rect = text.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 - 80))
        self.screen.blit(text, rect)
        
        self.btn_continue.draw(self.screen)
        self.btn_exit.draw(self.screen)
    
    def _render_debug_info(self):
        """Renderiza información de debug"""
        font = pygame.font.Font(None, 24)
        fps = self.clock.get_fps()
        dt_ms = self.dt * (1000.0 / self.target_fps)
        debug_info = self.level.get_debug_info()
        
        debug_texts = [
            f"FPS: {fps:.1f} | DeltaTime: {dt_ms:.1f}ms",
            f"Enemigos: {debug_info['enemies_total']} (Visibles: {debug_info['enemies_rendered']})",
            f"Proyectiles: {debug_info['projectiles']}",
            f"Partículas: {debug_info['particles_active']} (Visibles: {debug_info['particles_rendered']}) / {debug_info['particles_capacity']}",
            f"Pausa: {'SÍ' if self.paused else 'NO'}",
            "F3: Toggle Debug"
        ]
        y = 110
        for text in debug_texts:
            shadow = font.render(text, True, (0, 0, 0))
            self.screen.blit(shadow, (11, y + 1))
            surf = font.render(text, True, (0, 255, 0))
            self.screen.blit(surf, (10, y))
            y += 25