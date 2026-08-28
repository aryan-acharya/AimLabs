"""Blinking sphere obstacles that apply a score penalty when hit."""
import numpy as np
import random


OBS_R = 0.65    # obstacle sphere radius (visually bigger than targets)

# Spawn bounds same zone as targets so they blend in as threats
_X_RANGE = (-10.0,  10.0)
_Y_RANGE = (  0.8,   4.5)
_Z_RANGE = ( -5.0, -11.0)

def _random_pos(mode: str = 'arena'):
    return np.array([
        random.uniform(*_X_RANGE),
        random.uniform(*_Y_RANGE),
        random.uniform(*_Z_RANGE),
    ], dtype='f4')


class Obstacle:
    def __init__(self, mode: str = 'arena'):
        self.mode     = 'arena'
        self.pos      = _random_pos(mode)
        self.visible  = False
        self.timer    = random.uniform(0.0, 4.0)   # stagger starts
        self.show_dur = random.uniform(2.0, 7.0)
        self.hide_dur = random.uniform(1.0, 3.5)
        self.phase    = 'hidden'                    # 'hidden' | 'visible'

    def set_mode(self, mode: str):
        self.mode = 'arena'
        self.pos = _random_pos(self.mode)
        self.visible = False
        self.phase = 'hidden'
        self.timer = 0.0

    def update(self, dt: float):
        self.timer += dt
        if self.phase == 'hidden':
            if self.timer >= self.hide_dur:
                self.pos      = _random_pos(self.mode)  # new random spot each appearance
                self.phase    = 'visible'
                self.visible  = True
                self.timer    = 0.0
                self.show_dur = random.uniform(2.0, 7.0)
        else:
            if self.timer >= self.show_dur:
                self.phase    = 'hidden'
                self.visible  = False
                self.timer    = 0.0
                self.hide_dur = random.uniform(1.0, 3.5)

    def get_model_matrix(self):
        """Scale + translate matrix in the same format as targets."""
        m = np.zeros((4, 4), dtype='f4')
        scale = OBS_R
        m[0, 0] = scale
        m[1, 1] = scale
        m[2, 2] = scale
        m[3, 0] = self.pos[0]
        m[3, 1] = self.pos[1]
        m[3, 2] = self.pos[2]
        m[3, 3] = 1.0
        return m

    def ray_intersects(self, ray_origin: np.ndarray, ray_dir: np.ndarray):
        """Analytic ray-sphere test. Returns (hit: bool, distance: float)."""
        oc = ray_origin - self.pos
        a  = float(np.dot(ray_dir, ray_dir))
        b  = 2.0 * float(np.dot(oc, ray_dir))
        c  = float(np.dot(oc, oc)) - OBS_R * OBS_R
        disc = b * b - 4 * a * c
        if disc < 0:
            return False, -1.0
        sq = np.sqrt(disc)
        t1 = (-b - sq) / (2.0 * a)
        t2 = (-b + sq) / (2.0 * a)
        if t1 > 0.01:
            return True, float(t1)
        if t2 > 0.01:
            return True, float(t2)
        return False, -1.0


class ObstacleManager:
    MAX_OBSTACLES = 5

    def __init__(self, mode: str = 'arena'):
        self.mode = 'arena'
        self.obstacles = [Obstacle(mode) for _ in range(self.MAX_OBSTACLES)]

    def set_mode(self, mode: str):
        self.mode = 'arena'
        for obs in self.obstacles:
            obs.set_mode(mode)

    def update(self, dt: float, level: int = 1):
        for obs in self.obstacles:
            if level <= 2:
                # Easy / Normal: keep all obstacles hidden
                obs.visible = False
            else:
                obs.update(dt)

    def get_visible(self):
        return [obs for obs in self.obstacles if obs.visible]
