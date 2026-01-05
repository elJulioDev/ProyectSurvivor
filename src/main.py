"""
Punto de entrada principal del juego OPTIMIZADO
"""
import pygame
from game import Game
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, TITLE

def main():
    pygame.init()
    
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption(TITLE)
    
    # El clock ahora se maneja dentro de GameplayScene para DeltaTime correcto
    game = Game(screen)
    
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            game.handle_events(event)
        
        game.update()
        game.render()
        
        pygame.display.flip()
        # Ya no llamamos clock.tick() aquí, GameplayScene lo maneja internamente
    
    pygame.quit()

if __name__ == "__main__":
    main()