import pygame
from settings import WHITE, BLACK, GRAY

class Button:
    def __init__(self, x, y, width, height, text, font, 
                 text_color=WHITE, 
                 button_color=(40, 40, 50), 
                 hover_color=(70, 70, 90), 
                 border_color=(200, 200, 200)):
        
        # x, y definen el centro del botón
        self.rect = pygame.Rect(0, 0, width, height)
        self.rect.center = (x, y)
        
        self.text = text
        self.font = font
        self.text_color = text_color
        self.button_color = button_color
        self.hover_color = hover_color
        self.border_color = border_color
        self.is_hovered = False

    def update(self, mouse_pos):
        """Actualiza el estado de hover basado en la posición del mouse (virtual)"""
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, screen):
        """Renderiza el botón en la pantalla"""
        color = self.hover_color if self.is_hovered else self.button_color
        
        # Sombra (offset)
        shadow_rect = self.rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pygame.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=12)
        
        # Fondo
        pygame.draw.rect(screen, color, self.rect, border_radius=12)
        
        # Borde
        pygame.draw.rect(screen, self.border_color, self.rect, 2, border_radius=12)
        
        # Texto
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, event):
        """Detecta si se hizo clic en el botón"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered:
                return True
        return False