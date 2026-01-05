import pygame
import sys
import os
from settings import *
from game import Game

def main():
    # Centrar ventana y posicionarla en (0,0) para el modo sin bordes
    os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
    os.environ['SDL_VIDEO_CENTERED'] = '0' # Desactivamos centrado automático para usar 0,0
    
    pygame.init()
    
    # Detectar resolución del monitor
    monitor_info = pygame.display.Info()
    monitor_w = monitor_info.current_w
    monitor_h = monitor_info.current_h
    
    # --- SOLUCIÓN: Usar NOFRAME en lugar de FULLSCREEN exclusivo ---
    # Esto crea una "Ventana sin bordes" que no cambia la resolución de tu monitor
    screen = pygame.display.set_mode((monitor_w, monitor_h), pygame.NOFRAME)
    pygame.display.set_caption("ProyectSurvivor")
    
    # Superficie Virtual (HD 1280x720)
    virtual_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))
    
    clock = pygame.time.Clock()
    game = Game(virtual_surface)
    
    running = True
    fullscreen = True
    needs_rescale = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    needs_rescale = True
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        # Al volver a fullscreen, usamos NOFRAME de nuevo
                        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
                        screen = pygame.display.set_mode((monitor_w, monitor_h), pygame.NOFRAME)
                    else:
                        # Modo ventana normal
                        os.environ['SDL_VIDEO_CENTERED'] = '1' # Centrar ventana normal
                        screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
                    needs_rescale = True

            game.handle_events(event)

        game.update()
        game.render() 
        
        # --- LÓGICA DE ESCALADO ---
        if needs_rescale:
            current_w, current_h = screen.get_size()
            
            scale_w = current_w / BASE_WIDTH
            scale_h = current_h / BASE_HEIGHT
            scale = min(scale_w, scale_h)
            
            new_w = int(BASE_WIDTH * scale)
            new_h = int(BASE_HEIGHT * scale)
            
            x_offset = (current_w - new_w) // 2
            y_offset = (current_h - new_h) // 2
            
            game.set_render_params(scale, x_offset, y_offset)
            needs_rescale = False
        
        screen.fill(BLACK) 
        scaled_surface = pygame.transform.scale(virtual_surface, (int(BASE_WIDTH * game.render_scale), int(BASE_HEIGHT * game.render_scale)))
        screen.blit(scaled_surface, (game.render_offset_x, game.render_offset_y))
        
        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()