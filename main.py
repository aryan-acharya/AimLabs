"""
main.py - 3D Aim Trainer entry point
Ties together: window, camera, shaders, meshes, game logic, HUD.
"""
import os
import sys
import numpy as np
import pyrr
import pygame
import moderngl

# Path setup
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SHADER_DIR  = os.path.join(BASE_DIR, 'shaders')

# Engine
from engine.window   import Window
from engine.camera   import Camera
from engine.shader   import ShaderManager
from engine.mesh     import SphereMesh, BoxMesh, SkyboxQuad
from engine.renderer import HUDRenderer

# Game
from game.target     import TargetManager
from game.raycaster  import find_hit_target
from game.gun        import Gun
from game.hit_effect import HitMarker, ScreenFlash
from game.score      import ScoreTracker
from game.difficulty import DifficultyManager
from game.sound      import SoundManager
from game.obstacle   import ObstacleManager


# Scene constants
WIDTH, HEIGHT = 1280, 720
GAME_DURATION = 60.0   # seconds

ARENA_W = 30.0
ARENA_H = 12.0
ARENA_D = 30.0

LIGHT_POS = np.array([0.0, 10.0, -8.0], dtype='f4')


def build_arena(ctx, phong_prog):
    """Return list of (BoxMesh, model_matrix, color) for floor + walls."""
    panels = []
    hw = ARENA_W / 2
    hd = ARENA_D / 2
    hh = ARENA_H / 2

    def add(cx, cy, cz, w, h, d, color):
        m = BoxMesh(ctx, phong_prog, w, h, d)
        t = pyrr.matrix44.create_from_translation([cx, cy, cz], dtype='f4')
        panels.append((m, t, color))

    floor_c  = (0.08, 0.08, 0.12)
    wall_c   = (0.06, 0.06, 0.10)
    ceil_c   = (0.05, 0.04, 0.09)
    accent_c = (0.10, 0.05, 0.18)

    add(0,    -0.1,  -hd,  ARENA_W, 0.2,  ARENA_D,  floor_c)   # floor
    add(0,    hh,    -hd,  ARENA_W, 0.2,  ARENA_D,  ceil_c)    # ceiling
    add(-hw,  hh/2,  -hd,  0.2,    ARENA_H, ARENA_D, accent_c) # left wall
    add( hw,  hh/2,  -hd,  0.2,    ARENA_H, ARENA_D, accent_c) # right wall
    add(0,    hh/2, -hd*2, ARENA_W, ARENA_H, 0.2,    wall_c)   # back wall (far)
    add(0,    hh/2,  5.0,  ARENA_W, ARENA_H, 0.2,    accent_c) # back wall (behind player)

    # Player barrier: hip-height wall at Z=-3 keeping player at a safe distance
    barrier_c = (0.15, 0.05, 0.40)   # deep purple, matching arena accent palette
    add(0, 0.5, -3.0, ARENA_W, 1.2, 0.15, barrier_c)          # barrier: height=1.0 (hip), floor-anchored

    return panels


# Main game class
class AimTrainer:
    def __init__(self):
        self.win    = Window(WIDTH, HEIGHT, "AimLabs 3D  |  Python + ModernGL")
        self.ctx    = self.win.ctx
        self.shaders = ShaderManager(self.ctx, SHADER_DIR)

        # Load shader programs
        self.phong_prog  = self.shaders.load('phong')
        self.sky_prog    = self.shaders.load('skybox')
        self.hud_prog    = self.shaders.load('hud')

        # Camera
        self.camera = Camera(pos=(0, 1.7, 2), aspect=WIDTH/HEIGHT)

        # Geometry
        self.skybox       = SkyboxQuad(self.ctx, self.sky_prog)
        self.sphere_mesh  = SphereMesh(self.ctx, self.phong_prog, stacks=24, slices=24)
        self.arena_panels = build_arena(self.ctx, self.phong_prog)
        self.gun          = Gun(self.ctx, self.phong_prog)

        # Game systems
        self.targets    = TargetManager(self.ctx, count=8, mode="arena")
        self.obstacles  = ObstacleManager(mode="arena")
        self.score      = ScoreTracker(GAME_DURATION)
        self.difficulty = DifficultyManager(hits_per_level=8)
        self.sounds     = SoundManager()
        self.hit_marker = HitMarker()
        self.flash      = ScreenFlash()

        # HUD
        self.hud = HUDRenderer(self.ctx, self.hud_prog, WIDTH, HEIGHT)

        # State
        self.time        = 0.0
        self.paused      = False
        self.mouse_captured = True

        # Upload static phong uniforms
        self.phong_prog['light_pos'].value   = tuple(LIGHT_POS)
        self.phong_prog['ambient_strength'].value  = 0.35
        self.phong_prog['specular_strength'].value = 0.70

    # Input
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.win.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.score.game_over:
                        self.win.running = False
                    elif self.paused:
                        # ESC while paused exits the game.
                        self.win.running = False
                    else:
                        # ESC during gameplay pauses and releases mouse.
                        self.paused = True
                        self.win.release_mouse()

                elif event.key == pygame.K_r:
                    if self.score.game_over:
                        self.restart()
                    elif not self.gun.is_reloading:
                        self.gun.start_reload()
                        self.sounds.play_reload()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # left click = shoot
                    if not self.paused and not self.score.game_over:
                        self.shoot()
                    elif self.paused:
                        self.paused = False
                        self.win.capture_mouse()

            elif event.type == pygame.MOUSEMOTION:
                if not self.paused and not self.score.game_over:
                    dx, dy = event.rel
                    self.camera.process_mouse(dx, dy)

    def shoot(self):
        """Fire a ray from camera center  blocked when reloading or out of ammo."""
        if not self.gun.can_fire():
            return   # blocked: reloading or empty mag
        self.score.record_shot()
        self.gun.fire()
        self.sounds.play_shoot()

        # Auto-reload starts when the mag becomes empty after a shot.
        if self.gun.is_reloading and self.gun.reload_timer == 0.0:
            self.sounds.play_reload()

        ray_dir = self.camera.get_ray_direction()
        living  = self.targets.get_living_targets()

        # Find closest target hit.
        hit_target, target_dist, _ = find_hit_target(living, self.camera.pos, ray_dir)
        target_dist = target_dist if target_dist is not None else float('inf')

        # Find closest obstacle hit.
        hit_obs, obs_dist = None, float('inf')
        for obs in self.obstacles.get_visible():
            ok, t = obs.ray_intersects(self.camera.pos, ray_dir)
            if ok and t < obs_dist:
                hit_obs, obs_dist = obs, t

        # Resolve by distance: nearer hit wins.
        if hit_obs is not None and obs_dist <= target_dist:
            self.score.record_penalty()
            self.flash.trigger_miss()
        elif hit_target is not None:
            hit_target.hit()
            self.score.record_hit()
            self.sounds.play_hit()
            self.hit_marker.trigger()
            self.flash.trigger_hit()
            changed = self.difficulty.update_from_hits(self.score.hits)
            if changed:
                self.targets.apply_difficulty(self.difficulty.get_level())
        else:
            self.score.record_miss()
            self.flash.trigger_miss()


    # Update
    def update(self, dt: float):
        if self.paused or self.score.game_over:
            return

        self.time += dt
        keys = pygame.key.get_pressed()
        self.camera.process_keys(keys, dt, pygame)

        self.targets.update(dt)
        self.obstacles.update(dt, self.difficulty.get_level())
        self.gun.update(dt)
        self.hit_marker.update(dt)
        self.flash.update(dt)
        self.score.update(dt)

    # Render
    def render(self):
        ctx = self.ctx
        ctx.clear(0.01, 0.01, 0.03, 1.0)
        ctx.enable(moderngl.DEPTH_TEST)

        view = self.camera.get_view_matrix()
        proj = self.camera.get_projection_matrix()

        # 1. Skybox (no depth write)
        ctx.depth_func = '<='
        ctx.disable(moderngl.DEPTH_TEST)
        self.sky_prog['time'].value = self.time
        self.skybox.render()
        ctx.enable(moderngl.DEPTH_TEST)
        ctx.depth_func = '<'

        # 2. Arena panels
        self.phong_prog['m_view'].write(view.tobytes())
        self.phong_prog['m_proj'].write(proj.tobytes())
        self.phong_prog['cam_pos'].value = tuple(self.camera.pos)

        for mesh, model_mat, color in self.arena_panels:
            self.phong_prog['m_model'].write(model_mat.tobytes())
            self.phong_prog['object_color'].value = color
            self.phong_prog['hit_flash'].value    = 0.0
            mesh.render()

        # 3. Obstacles
        self.phong_prog['stripe_mode'].value = 1
        for obs in self.obstacles.get_visible():
            self.phong_prog['m_model'].write(obs.get_model_matrix().tobytes())
            self.phong_prog['hit_flash'].value = 0.0
            self.sphere_mesh.render()
        self.phong_prog['stripe_mode'].value = 0

        # 4. Targets
        for target in self.targets.targets:
            if not target.alive:
                continue
            model = target.get_model_matrix()
            self.phong_prog['m_model'].write(model.tobytes())
            self.phong_prog['object_color'].value = target.color
            self.phong_prog['hit_flash'].value    = target.hit_flash
            self.sphere_mesh.render()

        # 4. Gun (view-space, fixed to camera, always drawn on top)
        # Disable depth test so the gun always appears over world geometry
        # WITHOUT clearing the framebuffer (which would erase everything).
        ctx.disable(moderngl.DEPTH_TEST)
        gun_view = pyrr.matrix44.create_identity(dtype='f4')
        self.phong_prog['m_view'].write(gun_view.tobytes())
        gun_proj = pyrr.matrix44.create_perspective_projection_matrix(
            60, WIDTH/HEIGHT, 0.01, 10.0, dtype='f4'
        )
        self.phong_prog['m_proj'].write(gun_proj.tobytes())
        self.phong_prog['m_model'].write(self.gun.get_model_matrix().tobytes())
        self.phong_prog['hit_flash'].value    = 0.0
        self.phong_prog['cam_pos'].value      = (0.0, 0.0, 0.0)
        self.gun.render()   # gun sets its own colours per material group
        ctx.enable(moderngl.DEPTH_TEST)

        # Restore world view/proj for next frame safety
        self.phong_prog['m_view'].write(view.tobytes())
        self.phong_prog['m_proj'].write(proj.tobytes())

        # 5. HUD layer
        ctx.disable(moderngl.DEPTH_TEST)

        self.hud.draw_flash(self.flash.color)
        self.hud.draw_vignette()

        if self.score.game_over:
            self.hud.draw_end_screen(self.score.get_summary())
        elif self.paused:
            self.hud.draw_pause_screen()
        elif not self.score.game_started:
            # Pre-game: show crosshair + instructions overlay
            self.hud.draw_crosshair(0)
            self.hud.draw_ready_screen()
        else:
            self.hud.draw_crosshair(self.hit_marker.alpha)
            self.hud.draw_hud(
                score          = self.score.hits,
                accuracy       = self.score.accuracy,
                time_left      = self.score.time_left,
                streak         = self.score.streak,
                level_name     = self.difficulty.get_display_name(),
                fps            = self.win.get_fps(),
                ammo           = self.gun.ammo,
                mag_size       = self.gun.MAG_SIZE,
                is_reloading   = self.gun.is_reloading,
                reload_progress= self.gun.reload_progress,
            )

        ctx.enable(moderngl.DEPTH_TEST)

    # Restart
    def restart(self):
        self.score.reset()
        self.difficulty.current_level = 1
        self.targets._setup_targets()
        self.hit_marker.active = False
        self.flash.alpha = 0.0
        self.time = 0.0
        self.win.capture_mouse()

    # Main loop
    def run(self):
        while self.win.running:
            dt = self.win.get_dt(fps_cap=144)
            self.handle_events()
            self.update(dt)
            self.render()
            self.win.swap_buffers()
        self.cleanup()

    def cleanup(self):
        self.shaders.destroy()
        self.sphere_mesh.destroy()
        self.skybox.destroy()
        self.gun.destroy()
        for mesh, _, _ in self.arena_panels:
            mesh.destroy()
        self.hud.destroy()
        self.win.destroy()


if __name__ == '__main__':
    game = AimTrainer()
    game.run()
