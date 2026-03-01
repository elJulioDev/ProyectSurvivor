import pygame, sys, os
from settings import *
from game import Game


def main():
    from utils.platform_detect import is_android
    running_on_android = is_android()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.mixer.set_num_channels(32)

    # Configuración de ventana
    if running_on_android:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        fullscreen = True
        pygame.mouse.set_visible(False)
    else:
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        os.environ['SDL_VIDEO_CENTERED'] = '0'

        monitor_info = pygame.display.Info()
        monitor_w = monitor_info.current_w
        monitor_h = monitor_info.current_h
        screen = pygame.display.set_mode((monitor_w, monitor_h), pygame.NOFRAME)
        fullscreen = True

    pygame.display.set_caption(TITLE)

    virtual_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))

    # El clock principal NO limita FPS — cada escena gestiona su propio tick.
    # GameplayScene usa clock.tick(target_fps) para 60/120/240/ilimitado.
    # MenuScene y otras usan clock.tick(60) en su update().
    clock = pygame.time.Clock()
    game = Game(virtual_surface)

    running = True
    needs_rescale = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                if not fullscreen:
                    screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE
                    )
                    needs_rescale = True

            elif event.type == pygame.KEYDOWN:
                if not running_on_android and event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
                        monitor_info = pygame.display.Info()
                        screen = pygame.display.set_mode(
                            (monitor_info.current_w, monitor_info.current_h),
                            pygame.NOFRAME
                        )
                    else:
                        os.environ['SDL_VIDEO_CENTERED'] = '1'
                        screen = pygame.display.set_mode(
                            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
                        )
                    needs_rescale = True

            game.handle_events(event)

        # Cada escena controla su propio FPS vía clock.tick() en su update().
        game.update()
        game.render()

        if needs_rescale:
            current_w, current_h = screen.get_size()

            scale_w = current_w / BASE_WIDTH
            scale_h = current_h / BASE_HEIGHT

            # max() → siempre llena toda la pantalla (puede recortar
            # ligeramente en relaciones de aspecto distintas a 16:9).
            # min() → letterbox/pillarbox con barras negras (no se recorta nada).
            # Usamos max() en todos los casos para eliminar bordes negros.
            scale = max(scale_w, scale_h)

            new_w = int(BASE_WIDTH  * scale)
            new_h = int(BASE_HEIGHT * scale)

            x_offset = (current_w - new_w) // 2
            y_offset = (current_h - new_h) // 2

            game.set_render_params(scale, x_offset, y_offset)
            needs_rescale = False

        screen.fill(BLACK)
        scaled_surface = pygame.transform.scale(
            virtual_surface,
            (int(BASE_WIDTH * game.render_scale),
             int(BASE_HEIGHT * game.render_scale))
        )
        screen.blit(scaled_surface, (game.render_offset_x, game.render_offset_y))

        pygame.display.flip()
        # SIN clock.tick() aquí — el FPS lo controla cada escena individualmente.

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()