import pygame, random
from settings import WINDOW_WIDTH, WINDOW_HEIGHT, WORLD_WIDTH, WORLD_HEIGHT

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.offset_x = 0
        self.offset_y = 0
        self.lerp_speed = 0.08
        self.true_scroll_x = 0
        self.true_scroll_y = 0
        self.culling_margin = 100 
        self.viewport_rect = pygame.Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
        self.shake_intensity = 0
        self.shake_decay = 0.9

    def add_shake(self, amount):
        self.shake_intensity = min(self.shake_intensity + amount, 20)
    
    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)
    
    def apply_coords(self, x, y):
        return (x + self.offset_x, y + self.offset_y)
        
    def is_on_screen(self, rect):
        """
        Determina si un rectángulo (en coordenadas de mundo) 
        debe renderizarse, aplicando un margen de seguridad.
        """
        screen_rect = self.apply_rect(rect)
        display_area = self.viewport_rect.inflate(self.culling_margin, self.culling_margin)
        
        return screen_rect.colliderect(display_area)

    def update(self, target, mouse_pos=None):
        target_x = -target.rect.centerx + int(WINDOW_WIDTH / 2)
        target_y = -target.rect.centery + int(WINDOW_HEIGHT / 2)
        
        if mouse_pos:
            mx = mouse_pos[0] - WINDOW_WIDTH / 2
            my = mouse_pos[1] - WINDOW_HEIGHT / 2
            target_x -= mx * 0.4 
            target_y -= my * 0.4

        self.true_scroll_x += (target_x - self.true_scroll_x) * self.lerp_speed
        self.true_scroll_y += (target_y - self.true_scroll_y) * self.lerp_speed
        
        shake_x = 0
        shake_y = 0
        if self.shake_intensity > 0.1:
            shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
            shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
            self.shake_intensity *= self.shake_decay

        x = int(self.true_scroll_x)
        y = int(self.true_scroll_y)

        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))
        
        x += int(shake_x)
        y += int(shake_y)
        
        self.camera = pygame.Rect(x, y, self.width, self.height)
        self.offset_x = x
        self.offset_y = y