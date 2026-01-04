"""
Punto de entrada principal del juego
"""
import pygame
from game import Game
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, FPS, TITLE

def main():
    # Inicializar pygame
    pygame.init()
    
    # Crear ventana
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(TITLE)
    
    # Reloj para controlar FPS
    clock = pygame.time.Clock()
    
    # Crear instancia del juego
    game = Game(screen)
    
    # Loop principal
    running = True
    while running:
        # Manejar eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            game.handle_events(event)
        
        # Actualizar
        game.update()
        
        # Renderizar
        game.render()
        
        # Actualizar pantalla
        pygame.display.flip()
        clock.tick(FPS)
    
    pygame.quit()

if __name__ == "__main__":
    main()