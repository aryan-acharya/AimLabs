"""
engine/camera.py - First-person camera with mouse look and WASD movement
"""
import math
import numpy as np
import pyrr


class Camera:
    def __init__(self, pos=(0, 1.7, 0), fov=75, aspect=16/9, near=0.05, far=500.0):
        self.pos = np.array(pos, dtype='f4')
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far

        self.yaw = -90.0    # degrees, looking toward -Z
        self.pitch = 0.0

        self.sensitivity = 0.12
        self.speed = 8.0
        self.sprint_mult = 2.0

        self._update_vectors()

    def _update_vectors(self):
        yaw_r = math.radians(self.yaw)
        pitch_r = math.radians(self.pitch)

        self.forward = np.array([
            math.cos(pitch_r) * math.cos(yaw_r),
            math.sin(pitch_r),
            math.cos(pitch_r) * math.sin(yaw_r),
        ], dtype='f4')
        self.forward /= np.linalg.norm(self.forward)

        world_up = np.array([0, 1, 0], dtype='f4')
        self.right = np.cross(self.forward, world_up)
        self.right /= np.linalg.norm(self.right)
        self.up = np.cross(self.right, self.forward)

    def process_mouse(self, dx, dy):
        self.yaw   += dx * self.sensitivity
        self.pitch -= dy * self.sensitivity
        self.pitch  = max(-80.0, min(80.0, self.pitch))
        self._update_vectors()

    def process_keys(self, keys, dt, pygame, mode='arena'):
        speed = self.speed * (self.sprint_mult if keys[pygame.K_LSHIFT] else 1.0)
        # Flatten forward for horizontal movement
        flat_fwd = np.array([self.forward[0], 0, self.forward[2]], dtype='f4')
        norm = np.linalg.norm(flat_fwd)
        if norm > 0:
            flat_fwd /= norm

        flat_right = np.array([self.right[0], 0, self.right[2]], dtype='f4')
        rnorm = np.linalg.norm(flat_right)
        if rnorm > 0:
            flat_right /= rnorm

        move = np.zeros(3, dtype='f4')
        if keys[pygame.K_w]:
            move += flat_fwd
        if keys[pygame.K_s]:
            move -= flat_fwd
        if keys[pygame.K_a]:
            move -= flat_right
        if keys[pygame.K_d]:
            move += flat_right

        mnorm = np.linalg.norm(move)
        if mnorm > 0:
            move /= mnorm

        next_pos = self.pos + move * speed * dt

        # Keep movement inside the arena lane.
        next_pos[0] = max(-13.85, min(13.85, next_pos[0]))
        next_pos[2] = max(-2.85, min(3.85, next_pos[2]))
        next_pos[1] = max(0.5, next_pos[1])

        self.pos = next_pos

    def get_view_matrix(self):
        return pyrr.matrix44.create_look_at(
            self.pos,
            self.pos + self.forward,
            self.up,
            dtype='f4'
        )

    def get_projection_matrix(self):
        return pyrr.matrix44.create_perspective_projection_matrix(
            self.fov, self.aspect, self.near, self.far, dtype='f4'
        )

    def get_ray_direction(self):
        """Return normalized forward vector as the shooting ray direction."""
        return self.forward.copy()
