"""
Escena de Mejoras (Level Up)
"""
import pygame
import random
from scenes.scene import Scene
from ui.button import Button
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, UPGRADES, WHITE, BLACK

class UpgradeScene(Scene):
    def __init__(self, game, gameplay_scene):
        super().__init__(game)
        self.gameplay_scene = gameplay_scene
        self.font_title = pygame.font.Font(None, 64)
        self.font_text = pygame.font.Font(None, 28)
        self.font_desc = pygame.font.Font(None, 22)
        
        # Seleccionar 3 mejoras aleatorias disponibles
        self.options = self._select_upgrades()
        self.buttons = []
        
        # Crear botones para las opciones
        for i, opt in enumerate(self.options):
            upgrade = UPGRADES[opt]
            x = WINDOW_WIDTH // 2
            y = 220 + i * 120
            btn = Button(x, y, 500, 80, upgrade['name'], self.font_text)
            btn.action_value = opt
            btn.desc = upgrade['desc']
            self.buttons.append(btn)
    
    def _select_upgrades(self):
        """Selecciona 3 mejoras válidas al azar"""
        player = self.gameplay_scene.level.player
        available = []
        
        for key, upg in UPGRADES.items():
            # Filtrar mejoras de dash si ya se tiene
            if upg['type'] == 'unlock' and key == 'dash':
                if not player.dash_unlocked:
                    available.append(key)
            # Filtrar armas ya desbloqueadas
            elif upg['type'] == 'unlock_weapon':
                if upg['weapon_class'] not in player.unlocked_weapons:
                    available.append(key)
            # Mejoras stackeables (siempre disponibles)
            elif upg.get('stackable', False):
                available.append(key)
        
        # Si hay menos de 3 opciones, rellenar con duplicados (o manejar error)
        if len(available) < 3:
            stackables = [k for k, v in UPGRADES.items() if v.get('stackable', False)]
            if stackables:
                while len(available) < 3:
                    available.append(random.choice(stackables))
        
        return random.sample(available, min(3, len(available)))
    
    def handle_events(self, event):
        mouse_pos = self.game.get_mouse_pos()
        
        for btn in self.buttons:
            btn.update(mouse_pos)
            
            if btn.is_clicked(event):
                self._apply_upgrade(btn.action_value)
                
                # Volver al juego inmediatamente
                pygame.mouse.set_visible(False)
                self.game.current_scene = self.gameplay_scene
                # NOTA: Ya no llamamos a start_wave() porque el spawn es continuo
    
    def _apply_upgrade(self, key):
        """Aplica la mejora seleccionada al jugador"""
        player = self.gameplay_scene.level.player
        upg = UPGRADES[key]
        projectile_pool = self.gameplay_scene.level.projectile_pool
        
        if upg['type'] == 'unlock' and key == 'dash':
            player.dash_unlocked = True
        
        elif upg['type'] == 'stat':
            stat_name = upg['stat_name']
            value = upg['value']
            
            if stat_name == 'max_speed':
                player.max_speed *= value
            elif stat_name == 'max_health':
                player.max_health += value
                player.health += value
            elif stat_name == 'health_regen':
                player.health_regen += value
        
        elif upg['type'] == 'weapon':
            stat_name = upg['stat_name']
            value = upg['value']
            
            if stat_name == 'global_damage_mult':
                player.global_damage_mult *= value
            elif stat_name == 'global_cooldown_mult':
                player.global_cooldown_mult *= value
        
        elif upg['type'] == 'unlock_weapon':
            player.add_weapon(upg['weapon_class'], projectile_pool)
    
    def update(self):
        mouse_pos = self.game.get_mouse_pos()
        for btn in self.buttons:
            btn.update(mouse_pos)
    
    def render(self):
        # 1. Renderizar el juego de fondo (congelado)
        self.gameplay_scene.render()
        
        # 2. Overlay oscuro
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        
        # 3. Título (CORREGIDO: Usamos Nivel en vez de Oleada)
        player_level = self.gameplay_scene.level.player.level
        title = self.font_title.render(
            f"¡NIVEL {player_level} ALCANZADO!", True, (255, 215, 0)
        )
        title_rect = title.get_rect(center=(WINDOW_WIDTH//2, 120))
        self.screen.blit(title, title_rect)
        
        # 4. Botones
        for btn in self.buttons:
            btn.draw(self.screen)
            
            # Descripción centrada bajo el botón
            desc_surf = self.font_desc.render(btn.desc, True, (200, 200, 200))
            desc_rect = desc_surf.get_rect(center=(btn.rect.centerx, btn.rect.centery + 50))
            self.screen.blit(desc_surf, desc_rect)