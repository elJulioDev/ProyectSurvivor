import pygame
from scenes.menu import MenuScene

class Game:
    def __init__(self, surface):
        self.screen = surface
        self.running = True
        
        self.render_scale = 1.0
        self.render_offset_x = 0
        self.render_offset_y = 0
        
        self.current_scene = MenuScene(self)
    
    def handle_events(self, event):
        self.current_scene.handle_events(event)
    
    def update(self):
        self.current_scene.update()
        
        # --- CORRECCIÓN CLAVE ---
        if self.current_scene.next_scene:
            self.current_scene = self.current_scene.next_scene
            # IMPORTANTE: Inicializar la nueva escena (crear jugador, enemigos, etc.)
            self.current_scene.on_enter()
    
    def render(self):
        self.current_scene.render()
        
    def set_render_params(self, scale, offset_x, offset_y):
        self.render_scale = scale
        self.render_offset_x = offset_x
        self.render_offset_y = offset_y
        
    def get_mouse_pos(self):
        real_x, real_y = pygame.mouse.get_pos()
        virtual_x = real_x - self.render_offset_x
        virtual_y = real_y - self.render_offset_y
        
        if self.render_scale > 0:
            virtual_x /= self.render_scale
            virtual_y /= self.render_scale
        
        return virtual_x, virtual_y