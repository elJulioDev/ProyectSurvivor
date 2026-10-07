"""
ProyectSurvivor — punto de entrada.

Ejecutar desde la raíz del proyecto:
    uv run main.py
"""
import pygame, sys, os
from src.settings import *
from src.game import Game


def _desktop_size():
    """Tamaño del escritorio actual.

    get_desktop_sizes() es fiable bajo Wayland/HiDPI, donde Info().current_w/h
    puede devolver valores incorrectos (o -1) y dejar la ventana mal encajada.
    """
    try:
        sizes = pygame.display.get_desktop_sizes()
        if sizes:
            w, h = sizes[0]
            if w > 0 and h > 0:
                return (w, h)
    except Exception:
        pass
    info = pygame.display.Info()
    return (info.current_w, info.current_h)


def main():
    from src.utils.platform_detect import is_android
    running_on_android = is_android()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    pygame.mixer.set_num_channels(32)

    # Configuración de ventana
    fullscreen = True
    if running_on_android:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
    else:
        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
        os.environ['SDL_VIDEO_CENTERED'] = '0'
        screen = pygame.display.set_mode(_desktop_size(), pygame.NOFRAME)

    pygame.display.set_caption(TITLE)

    virtual_surface = pygame.Surface((BASE_WIDTH, BASE_HEIGHT))

    clock = pygame.time.Clock()
    game = Game(virtual_surface)

    # Superficie reutilizada para el escalado (si no, se allocaba una de
    # 1920×1080 en cada frame). None = blit directo 1:1.
    scaled_surface = None

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
                    scaled_surface = None
                    needs_rescale = True

            elif event.type == pygame.KEYDOWN:
                if not running_on_android and event.key == pygame.K_F11:
                    fullscreen = not fullscreen
                    if fullscreen:
                        os.environ['SDL_VIDEO_WINDOW_POS'] = "0,0"
                        screen = pygame.display.set_mode(
                            _desktop_size(), pygame.NOFRAME
                        )
                    else:
                        os.environ['SDL_VIDEO_CENTERED'] = '1'
                        screen = pygame.display.set_mode(
                            (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE
                        )
                    scaled_surface = None
                    needs_rescale = True

            game.handle_events(event)

        game.update()
        game.render()

        if needs_rescale:
            current_w, current_h = screen.get_size()

            # Escala "contain": el 16:9 completo cabe dentro del monitor.
            # Con max() la imagen se recortaba en pantallas que no son 16:9
            # (16:10, 21:9, móviles 20:9...) y se perdía parte del escenario.
            scale = min(current_w / BASE_WIDTH, current_h / BASE_HEIGHT)

            new_w = int(BASE_WIDTH  * scale)
            new_h = int(BASE_HEIGHT * scale)

            x_offset = (current_w - new_w) // 2
            y_offset = (current_h - new_h) // 2

            game.set_render_params(scale, x_offset, y_offset)

            if (new_w, new_h) == (BASE_WIDTH, BASE_HEIGHT):
                scaled_surface = None          # 1:1 — se blitea directo
            else:
                scaled_surface = pygame.Surface((new_w, new_h))

            needs_rescale = False

        if scaled_surface is None:
            screen.blit(virtual_surface,
                        (game.render_offset_x, game.render_offset_y))
        else:
            # Limpia solo el área de las barras negras del letterbox.
            screen.fill(BLACK)
            pygame.transform.scale(virtual_surface,
                                   scaled_surface.get_size(), scaled_surface)
            screen.blit(scaled_surface,
                        (game.render_offset_x, game.render_offset_y))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
