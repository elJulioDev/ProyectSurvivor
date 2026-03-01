"""
Sistema de controles táctiles para móvil.
Activable en modo debug con F5 desde gameplay.

Layout (1280×720):
  ┌──────────────────────────────────────────────┐
  │                                   [II PAUSA] │
  │                                              │
  │                              [DASH]          │
  │  [JOY-MOV]   [slots arma HUD]   [JOY-AIM]   │
  └──────────────────────────────────────────────┘

Controles:
  · Joystick izquierdo  → mover personaje
  · Joystick derecho    → apuntar + disparo automático
  · Botón DASH          → ejecutar dash (solo si está desbloqueado)
  · Botón PAUSA         → pausar juego
  · Tap en slot arma    → cambiar arma activa

Soporte de entrada:
  · Mouse (botón izquierdo) para debug en PC
  · pygame.FINGERDOWN/UP/MOTION para Android multi-touch
"""

import pygame, math

def _circle_alpha(surface: pygame.Surface,
                  color_rgba: tuple,
                  center: tuple,
                  radius: int) -> None:
    """Dibuja un círculo con canal alpha sobre 'surface'."""
    s = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(s, color_rgba, (radius, radius), radius)
    surface.blit(s, (center[0] - radius, center[1] - radius))


def _rect_alpha(surface: pygame.Surface,
                color_rgba: tuple,
                rect: pygame.Rect,
                radius: int = 8) -> None:
    """Dibuja un rectángulo con alpha y esquinas redondeadas."""
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, color_rgba, s.get_rect(), border_radius=radius)
    surface.blit(s, rect.topleft)

class VirtualJoystick:
    """
    Joystick virtual de posición dinámica:
    el centro aparece donde el usuario toca, no en un punto fijo.
    El nodo sigue el dedo hasta MAX_TRAVEL píxeles del origen.
    """

    BASE_RADIUS = 72     # Radio del aro exterior
    KNOB_RADIUS = 28     # Radio del nodo interior
    MAX_TRAVEL  = 54     # Máxima distancia nodo ↔ origen

    # Paleta
    _C_BASE_IDLE = (255, 255, 255, 18)
    _C_BASE_LIVE = (255, 255, 255, 32)
    _C_RING      = (185, 200, 235, 150)
    _C_KNOB_FILL = (255, 255, 255, 110)
    _C_KNOB_RING = (220, 225, 255, 180)

    def __init__(self,
                 default_cx: float,
                 default_cy: float,
                 activation_zone: pygame.Rect) -> None:
        """
        default_cx/cy    – posición visual cuando el joystick está inactivo.
        activation_zone  – área de pantalla donde se puede activar (coords virtuales).
        """
        self.default_cx = default_cx
        self.default_cy = default_cy
        self.zone       = activation_zone

        # Estado interno
        self.active    = False
        self.origin_x  = float(default_cx)
        self.origin_y  = float(default_cy)
        self.knob_x    = float(default_cx)
        self.knob_y    = float(default_cy)

        # Salida pública  (−1 … +1, magnitud incluida)
        self.dx        = 0.0
        self.dy        = 0.0
        self.magnitude = 0.0

    def handle_down(self, x: float, y: float) -> bool:
        """Activa el joystick si el toque cae en su zona. Retorna True si capturó."""
        if self.zone.collidepoint(x, y):
            self.active   = True
            self.origin_x = x
            self.origin_y = y
            self.knob_x   = x
            self.knob_y   = y
            self._compute(x, y)
            return True
        return False

    def handle_move(self, x: float, y: float) -> None:
        if self.active:
            self._compute(x, y)

    def handle_up(self) -> None:
        self.active    = False
        self.dx = self.dy = self.magnitude = 0.0
        self.knob_x = self.origin_x = float(self.default_cx)
        self.knob_y = self.origin_y = float(self.default_cy)

    def get_vector(self) -> tuple:
        """Devuelve (dx, dy) escalados por magnitud."""
        return (self.dx, self.dy)

    def render(self, screen: pygame.Surface) -> None:
        if not self.active:
            _circle_alpha(screen, self._C_BASE_IDLE,
                          (int(self.default_cx), int(self.default_cy)),
                          self.BASE_RADIUS)
            _circle_alpha(screen, self._C_BASE_IDLE,
                          (int(self.default_cx), int(self.default_cy)),
                          self.KNOB_RADIUS)
            return

        ox, oy = int(self.origin_x), int(self.origin_y)
        kx, ky = int(self.knob_x),  int(self.knob_y)

        # Aro exterior (fijo en punto de toque)
        _circle_alpha(screen, self._C_BASE_LIVE, (ox, oy), self.BASE_RADIUS)
        pygame.draw.circle(screen, self._C_RING, (ox, oy), self.BASE_RADIUS, 2)

        # Línea de dirección (sutil)
        if self.magnitude > 0.1:
            pygame.draw.line(screen, (*self._C_RING[:3], 60),
                             (ox, oy), (kx, ky), 2)

        # Nodo interior
        _circle_alpha(screen, self._C_KNOB_FILL, (kx, ky), self.KNOB_RADIUS)
        pygame.draw.circle(screen, self._C_KNOB_RING, (kx, ky),
                           self.KNOB_RADIUS, 2)

    def _compute(self, x: float, y: float) -> None:
        raw_dx = x - self.origin_x
        raw_dy = y - self.origin_y
        dist   = math.hypot(raw_dx, raw_dy)

        if dist < 1.0:
            self.dx = self.dy = self.magnitude = 0.0
            self.knob_x, self.knob_y = self.origin_x, self.origin_y
            return

        inv  = 1.0 / dist
        nx, ny = raw_dx * inv, raw_dy * inv
        self.magnitude = min(1.0, dist / self.MAX_TRAVEL)
        self.dx = nx * self.magnitude
        self.dy = ny * self.magnitude

        clamped   = min(dist, self.MAX_TRAVEL)
        self.knob_x = self.origin_x + nx * clamped
        self.knob_y = self.origin_y + ny * clamped

class MobileButton:
    """Botón táctil circular con retroalimentación visual de prensado."""

    def __init__(self,
                 cx: float, cy: float,
                 radius: int,
                 label: str,
                 color=(90, 110, 160)) -> None:
        self.cx       = cx
        self.cy       = cy
        self.radius   = radius
        self.label    = label
        self.color    = color
        self.pressed  = False
        self._just_dn = False
        self._font: pygame.font.Font | None = None

    def hit(self, x: float, y: float) -> bool:
        return math.hypot(x - self.cx, y - self.cy) <= self.radius

    def handle_down(self, x: float, y: float) -> bool:
        if self.hit(x, y):
            self.pressed  = True
            self._just_dn = True
            return True
        return False

    def handle_up(self) -> None:
        self.pressed = False

    def consume(self) -> bool:
        """Retorna True una sola vez al presionar."""
        if self._just_dn:
            self._just_dn = False
            return True
        return False

    def tick(self) -> None:
        """Limpiar flag just_down (llamar al final de cada frame)."""
        self._just_dn = False

    def render(self, screen: pygame.Surface) -> None:
        if not self._font:
            self._font = pygame.font.Font(None, 22)

        cx, cy, r = int(self.cx), int(self.cy), self.radius
        fill_a = 170 if self.pressed else 85
        ring_a = 230 if self.pressed else 135

        _circle_alpha(screen, (*self.color, fill_a), (cx, cy), r)
        pygame.draw.circle(screen, (*self.color, ring_a), (cx, cy), r, 2)

        if self.label:
            surf = self._font.render(self.label, True, (230, 235, 248))
            screen.blit(surf, (cx - surf.get_width() // 2,
                               cy - surf.get_height() // 2))

class MobileControls:
    """
    Orquestador de controles táctiles.

    Salidas públicas (actualizadas cada frame en update()):
      movement       (dx, dy)  vector de movimiento  −1 … +1
      aim_angle      float|None  ángulo de apuntado en radianes
      fire           bool  disparar este frame (joystick derecho activo)
      dash_request   bool  solicitar dash  (se consume en gameplay)
      pause_request  bool  solicitar pausa (se consume en gameplay)

    Gestión de "dedos" (multi-touch):
      En PC (mouse) solo se rastrea 1 dedo a la vez (_mouse_cap).
      En Android se rastrean N dedos simultáneos (_finger_map).
    """

    # Coordenadas de referencia (1280×720 virtual)

    # Zonas de activación de joysticks
    _ZONE_MOVE = pygame.Rect(0,   430, 500, 290)
    _ZONE_AIM  = pygame.Rect(780, 430, 500, 290)

    # Posición por defecto (inactivo)
    _POS_MOVE = (150, 630)
    _POS_AIM  = (1130, 630)

    # Botones
    _POS_DASH  = (960, 548)
    _POS_PAUSE = (1242, 120)

    def __init__(self,
                 screen_w: int = 1280,
                 screen_h: int = 720) -> None:
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.enabled  = False

        # Controles
        self.joy_move = VirtualJoystick(*self._POS_MOVE, self._ZONE_MOVE)
        self.joy_aim  = VirtualJoystick(*self._POS_AIM,  self._ZONE_AIM)

        self.btn_dash  = MobileButton(*self._POS_DASH,  38, "DASH",
                                      color=(0, 155, 200))
        self.btn_pause = MobileButton(*self._POS_PAUSE, 28, "II",
                                      color=(90, 90, 130))

        # Salidas públicas
        self.movement      = (0.0, 0.0)
        self.aim_angle: float | None = None
        self.fire          = False
        self.dash_request  = False
        self.pause_request = False

        # Rastreo de capturas
        # Mouse (PC): un solo dedo simulado
        self._mouse_cap: str | None = None  # 'move'|'aim'|'dash'|'pause'|None

        # Touch real (Android): dict finger_id → control name
        self._finger_map: dict[int, str] = {}

        # Fuente para el banner de debug
        self._debug_font: pygame.font.Font | None = None

    def handle_event(self,
                     event: pygame.event.Event,
                     vpos: tuple[float, float],
                     player=None) -> bool:
        """
        Procesa un evento pygame usando 'vpos' (coords virtuales 1280×720).
        Retorna True si el evento fue capturado y no debe procesarse más.
        Solo activo cuando self.enabled = True.
        """
        if not self.enabled:
            return False

        x, y = vpos

        # Mouse (simulación de 1 dedo en PC)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self._down(x, y, player, cap_key='_mouse_cap')

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._up(self._mouse_cap)
            self._mouse_cap = None
            return False

        if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
            self._move(x, y, self._mouse_cap)
            return False

        # Touch real (Android multi-touch)
        if event.type == pygame.FINGERDOWN:
            fx = event.x * self.screen_w
            fy = event.y * self.screen_h
            fid = event.finger_id
            ctrl = self._down_finger(fx, fy, player)
            if ctrl:
                self._finger_map[fid] = ctrl
            return bool(ctrl)

        if event.type == pygame.FINGERUP:
            fid = event.finger_id
            ctrl = self._finger_map.pop(fid, None)
            if ctrl:
                self._up(ctrl)
            return False

        if event.type == pygame.FINGERMOTION:
            fid = event.finger_id
            ctrl = self._finger_map.get(fid)
            if ctrl:
                fx = event.x * self.screen_w
                fy = event.y * self.screen_h
                self._move(fx, fy, ctrl)
            return False

        return False

    def _down(self, x: float, y: float, player, cap_key: str) -> bool:
        """Maneja toque inicial y asigna captura."""
        ctrl = self._down_finger(x, y, player)
        if ctrl:
            setattr(self, cap_key, ctrl)
            return True
        return False

    def _down_finger(self, x: float, y: float, player) -> str | None:
        """Determina qué control captura el toque y lo activa. Retorna nombre o None."""
        # Pausa (máxima prioridad, esquina)
        if self.btn_pause.handle_down(x, y):
            self.pause_request = True
            return 'pause'

        # Dash (solo si desbloqueado)
        if player and getattr(player, 'dash_unlocked', False):
            if self.btn_dash.handle_down(x, y):
                self.dash_request = True
                return 'dash'

        # Joystick izquierdo
        if self.joy_move.handle_down(x, y):
            return 'move'

        # Joystick derecho
        if self.joy_aim.handle_down(x, y):
            return 'aim'

        return None

    def _move(self, x: float, y: float, ctrl: str | None) -> None:
        if ctrl == 'move': self.joy_move.handle_move(x, y)
        elif ctrl == 'aim': self.joy_aim.handle_move(x, y)

    def _up(self, ctrl: str | None) -> None:
        if ctrl == 'move':   self.joy_move.handle_up()
        elif ctrl == 'aim':  self.joy_aim.handle_up()
        elif ctrl == 'dash':  self.btn_dash.handle_up()
        elif ctrl == 'pause': self.btn_pause.handle_up()

    def update(self, player=None) -> None:
        """Actualiza salidas derivadas. Llamar UNA VEZ por frame antes de level.update()."""
        if not self.enabled:
            return

        # Movimiento
        self.movement = self.joy_move.get_vector()

        # Apuntado + disparo automático
        jdx, jdy = self.joy_aim.get_vector()
        if self.joy_aim.active and self.joy_aim.magnitude > 0.18:
            self.aim_angle = math.atan2(jdy, jdx)
            self.fire      = True
        else:
            self.aim_angle = None
            self.fire      = False

    def clear_requests(self) -> None:
        """Limpiar flags de petición al final del frame."""
        self.dash_request  = False
        self.pause_request = False
        self.btn_dash.tick()
        self.btn_pause.tick()

    # Detección de slots de arma
    def check_weapon_slot_tap(self,
                               x: float, y: float,
                               player) -> int:
        """
        Detecta si un toque cae sobre un slot de arma del HUD.
        Devuelve el índice (0-based) del arma tocada, o −1 si ninguna.
        Coordenadas en espacio virtual 1280×720.
        """
        if not player or not player.weapons:
            return -1

        SLOT_W, SLOT_H, GAP = 54, 54, 8
        n        = len(player.weapons)
        total_w  = n * SLOT_W + (n - 1) * GAP
        start_x  = self.screen_w // 2 - total_w // 2
        base_y   = self.screen_h - SLOT_H - 20
        PAD      = 12  # tolerancia extra para dedos

        for i in range(n):
            sx = start_x + i * (SLOT_W + GAP)
            r  = pygame.Rect(sx - PAD, base_y - PAD,
                             SLOT_W + PAD * 2, SLOT_H + PAD * 2)
            if r.collidepoint(x, y):
                return i
        return -1

    def render(self, screen: pygame.Surface, player=None) -> None:
        """Dibuja todos los controles táctiles sobre la pantalla."""
        if not self.enabled:
            return

        self.joy_move.render(screen)
        self.joy_aim.render(screen)
        self.btn_pause.render(screen)

        # Dash: color depende del cooldown
        if player and getattr(player, 'dash_unlocked', False):
            cd_timer = getattr(player, 'dash_cooldown_timer', 0)
            cd_max   = max(1, getattr(player, 'dash_cooldown', 45))
            ready    = cd_timer <= 0
            self.btn_dash.color = (0, 155, 200) if ready else (35, 62, 85)
            self.btn_dash.render(screen)
        elif player and not getattr(player, 'dash_unlocked', False):
            # Botón fantasma deshabilitado (dash no desbloqueado)
            pass

        # Separador central sutil entre zonas de joystick
        sep = pygame.Surface((1, 80), pygame.SRCALPHA)
        sep.fill((255, 255, 255, 16))
        screen.blit(sep, (self.screen_w // 2, self.screen_h - 110))

        # Etiquetas de zona (muy sutiles)
        self._render_zone_labels(screen)

    def _render_zone_labels(self, screen: pygame.Surface) -> None:
        if not hasattr(self, '_zone_font'):
            self._zone_font = pygame.font.Font(None, 18)
        pairs = [
            ("MOVER",  self._POS_MOVE[0], self._POS_MOVE[1] - VirtualJoystick.BASE_RADIUS - 10),
            ("APUNTAR", self._POS_AIM[0], self._POS_AIM[1] - VirtualJoystick.BASE_RADIUS - 10),
        ]
        for txt, tx, ty in pairs:
            surf = self._zone_font.render(txt, True, (120, 125, 145))
            screen.blit(surf, (int(tx) - surf.get_width() // 2, int(ty)))