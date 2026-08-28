"""Target spawning and difficulty scaling for sphere targets."""

import math
import random

import numpy as np


_SPHERE_COLORS = [
    (1.0, 0.25, 0.1),
    (1.0, 0.15, 0.5),
    (0.2, 0.8, 1.0),
    (0.6, 0.2, 1.0),
    (0.1, 1.0, 0.4),
    (1.0, 0.6, 0.0),
]


class SphereTarget:
    def __init__(self, target_id: int, bounds, radius: float = 0.35):
        self.id = target_id
        self.bounds = bounds      # (x_range, y_range, z_range)
        self.base_radius = radius
        self.move_speed = 0.0
        
        self.pos = np.zeros(3, dtype='f4')
        self.color = (1.0, 0.3, 0.1)
        self.alive = True
        self.death_timer = 0.0
        self.death_duration = 0.18
        self.scale = 1.0
        self.hit_flash = 0.0
        self.velocity = np.zeros(3, dtype='f4')

        self.age = 0.0
        self.pulse_amount = 0.0
        self.pulse_rate = 0.0

        self.spawn()

    def spawn(self):
        xr, yr, zr = self.bounds
        self.pos = np.array([
            random.uniform(*xr),
            random.uniform(*yr),
            random.uniform(*zr),
        ], dtype='f4')
        self.color = random.choice(_SPHERE_COLORS)
        self.alive = True
        self.scale = 1.0
        self.hit_flash = 0.0
        self.age = 0.0

        if self.move_speed > 0.0:
            v = np.array([
                random.uniform(-1, 1),
                random.uniform(-0.3, 0.3),
                random.uniform(-1, 1),
            ], dtype='f4')
            norm = np.linalg.norm(v)
            if norm > 0:
                v /= norm
            self.velocity = v * self.move_speed
        else:
            self.velocity = np.zeros(3, dtype='f4')

    def hit(self):
        self.alive = False
        self.death_timer = 0.0
        self.hit_flash = 1.0

    def update(self, dt: float):
        if self.alive:
            self.age += dt
            if self.scale < 1.0:
                self.scale = min(1.0, self.scale + dt / 0.15)

            if self.move_speed > 0.0:
                self.pos += self.velocity * dt
                for axis, (lo, hi) in enumerate(self.bounds):
                    if self.pos[axis] < lo:
                        self.pos[axis] = lo
                        self.velocity[axis] *= -1
                    elif self.pos[axis] > hi:
                        self.pos[axis] = hi
                        self.velocity[axis] *= -1
        else:
            self.death_timer += dt
            t = min(1.0, self.death_timer / self.death_duration)
            self.scale = 1.0 - t
            if self.death_timer >= self.death_duration:
                self.spawn()

        if self.hit_flash > 0:
            self.hit_flash = max(0.0, self.hit_flash - dt * 5.0)

    def _pulse_scale(self):
        if self.pulse_amount > 0 and self.pulse_rate > 0:
            s = math.sin(math.pi * self.pulse_rate * self.age)
            return 1.0 - self.pulse_amount * s * s
        return 1.0

    def get_model_matrix(self):
        r = self.base_radius * self.scale * self._pulse_scale()
        model = np.zeros((4, 4), dtype='f4')
        model[0, 0] = r
        model[1, 1] = r
        model[2, 2] = r
        model[3, 0] = self.pos[0]
        model[3, 1] = self.pos[1]
        model[3, 2] = self.pos[2]
        model[3, 3] = 1.0
        return model

    def get_effective_radius(self):
        return self.base_radius * self.scale * self._pulse_scale()


class TargetManager:
    ARENA_BOUNDS = ((-10, 10), (0.7, 3.2), (-16, -10))

    def __init__(self, ctx, count: int = 8, mode: str = "arena"):
        self.ctx     = ctx
        self.count   = count
        self.mode    = "arena"
        self.targets = []
        self.level   = 1
        self._setup_targets()

    def set_mode(self, mode: str):
        # Kept for compatibility with existing calls.
        self.mode = "arena"
        self._setup_targets()
        self.apply_difficulty(self.level)

    def _setup_targets(self):
        self.targets.clear()
        for i in range(self.count):
            self.targets.append(SphereTarget(i, self.ARENA_BOUNDS, radius=0.50))

    def apply_difficulty(self, level: int):
        self.level = level
        sizes   = [0.55, 0.48, 0.38, 0.28, 0.20][level - 1]
        speeds  = [0.0,  1.0,  2.0,  3.5,  5.5 ][level - 1]
        counts  = [6,    8,    10,   12,   15   ][level - 1]
        pulse_c = [0.0,  0.0,  0.0,  0.50, 0.75][level - 1]
        pulse_a = [0.0,  0.0,  0.0,  0.35, 0.50][level - 1]
        pulse_r = [0.0,  0.0,  0.0,  1.2,  2.0 ][level - 1]

        while len(self.targets) < counts:
            self.targets.append(SphereTarget(len(self.targets), self.ARENA_BOUNDS, radius=sizes))
        while len(self.targets) > counts:
            self.targets.pop()

        for t in self.targets:
            t.base_radius = sizes
            t.move_speed  = speeds
            if random.random() < pulse_c:
                t.pulse_amount = pulse_a
                t.pulse_rate   = pulse_r + random.uniform(-0.2, 0.2)
            else:
                t.pulse_amount = 0.0
                t.pulse_rate   = 0.0
            if speeds > 0 and np.all(t.velocity == 0):
                v = np.array([random.uniform(-1, 1), random.uniform(-0.2, 0.2), random.uniform(-1, 1)], dtype='f4')
                v /= max(np.linalg.norm(v), 1e-6)
                t.velocity = v * speeds

    def update(self, dt: float):
        for t in self.targets:
            t.update(dt)

    def get_living_targets(self):
        return [t for t in self.targets if t.alive]
