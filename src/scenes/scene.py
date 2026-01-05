"""
Clase base para las escenas del juego
"""

class Scene:
    """Clase base abstracta para todas las escenas"""
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.next_scene = None
    
    def handle_events(self, event):
        """Maneja eventos de pygame"""
        pass
    
    def update(self):
        """Actualiza la lógica de la escena"""
        pass
    
    def render(self):
        """Renderiza la escena"""
        pass
    
    def on_enter(self):
        """Se llama cuando se entra a la escena"""
        pass
    
    def on_exit(self):
        """Se llama cuando se sale de la escena"""
        pass