"""
Clase principal del juego refactorizada para usar escenas
"""

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.running = True
        self.current_scene = None
        
        # Iniciar con el menú
        from scenes.menu import MenuScene
        self.current_scene = MenuScene(self)
        self.current_scene.on_enter()
    
    def handle_events(self, event):
        """Delega el manejo de eventos a la escena actual"""
        if self.current_scene:
            self.current_scene.handle_events(event)
    
    def update(self):
        """Actualiza la escena actual y maneja transiciones"""
        if self.current_scene:
            self.current_scene.update()
            
            # Verificar si hay que cambiar de escena
            if self.current_scene.next_scene:
                self.current_scene.on_exit()
                self.current_scene = self.current_scene.next_scene
                self.current_scene.on_enter()
    
    def render(self):
        """Renderiza la escena actual"""
        if self.current_scene:
            self.current_scene.render()