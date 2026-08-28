"""
game/hit_effect.py - Screen-space hit markers and flash effects
"""


class HitMarker:
    """2D hit marker: 4 diagonal lines that fade out."""
    def __init__(self):
        self.active = False
        self.alpha  = 0.0
        self.timer  = 0.0
        self.duration = 0.30

    def trigger(self):
        self.active = True
        self.alpha  = 1.0
        self.timer  = 0.0

    def update(self, dt: float):
        if not self.active:
            return
        self.timer += dt
        t = self.timer / self.duration
        self.alpha = max(0.0, 1.0 - t)
        if self.timer >= self.duration:
            self.active = False
            self.alpha  = 0.0


class ScreenFlash:
    """Brief full-screen color flash."""
    def __init__(self):
        self.alpha = 0.0
        self.color = (1.0, 1.0, 1.0, 0.0)   # RGBA

    def trigger_hit(self):
        self.alpha = 0.50
        self.color = (1.0, 1.0, 1.0, self.alpha)

    def trigger_miss(self):
        self.alpha = 0.30
        self.color = (1.0, 0.1, 0.05, self.alpha)

    def update(self, dt: float):
        self.alpha = max(0.0, self.alpha - dt * 3.0)  # slower decay = longer visible
        r, g, b, _ = self.color
        self.color = (r, g, b, self.alpha)
