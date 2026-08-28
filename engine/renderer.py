"""
engine/renderer.py - Scene rendering pipeline with HUD overlay
"""
import numpy as np
import pygame
import pyrr
import moderngl


class HUDRenderer:
    """
    Renders 2D text and shapes for the HUD using Pygame surfaces uploaded as GL textures.
    Also handles crosshair and hit markers.
    """

    def __init__(self, ctx: moderngl.Context, hud_program: moderngl.Program,
                 width: int, height: int):
        self.ctx = ctx
        self.prog = hud_program
        self.width = width
        self.height = height

        # Font setup
        pygame.font.init()
        self.font_large  = pygame.font.SysFont('Segoe UI', 36, bold=True)
        self.font_medium = pygame.font.SysFont('Segoe UI', 26, bold=True)
        self.font_small  = pygame.font.SysFont('Segoe UI', 20)
        self.font_tiny   = pygame.font.SysFont('Segoe UI', 16)
        self.font_end    = pygame.font.SysFont('Segoe UI', 60, bold=True)
        self.font_sub    = pygame.font.SysFont('Segoe UI', 32)
        self.font_ammo   = pygame.font.SysFont('Consolas', 32, bold=True)

        # Full-screen quad VAO for overlays
        quad_verts = np.array([
            -1, -1,  0, 0,
             1, -1,  1, 0,
             1,  1,  1, 1,
            -1,  1,  0, 1,
        ], dtype='f4')
        quad_idxs = np.array([0,1,2, 0,2,3], dtype='i4')
        self.quad_vbo = ctx.buffer(quad_verts.tobytes())
        self.quad_ibo = ctx.buffer(quad_idxs.tobytes())
        self.quad_vao = ctx.vertex_array(
            hud_program,
            [(self.quad_vbo, '2f 2f', 'in_position', 'in_uv')],
            self.quad_ibo
        )

        # Texture placeholder
        self._hud_tex = None
        self._hud_state_key = None
        self._fps_last_update_ms = 0
        self._fps_display = 0.0

    def _render_text_surface(self, score, accuracy, time_left, streak, level_name, fps,
                             ammo=30, mag_size=30, is_reloading=False, reload_progress=1.0):
        """Produce one combined Pygame surface for HUD text and ammo panel."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        def draw_shadowed(font, text, color, x, y):
            shadow = font.render(text, True, (0, 0, 0))
            surf.blit(shadow, (x+2, y+2))
            label = font.render(text, True, color)
            surf.blit(label, (x, y))

        # Score
        draw_shadowed(self.font_large,  f"SCORE  {score:04d}", (255, 220, 60),  20, 20)
        # Accuracy
        draw_shadowed(self.font_medium, f"ACC    {accuracy:.1f}%", (100, 220, 255), 20, 68)
        # Streak
        if streak >= 3:
            draw_shadowed(self.font_medium, f"STREAK  x{streak}", (255, 100, 220), 20, 100)
        # Difficulty
        draw_shadowed(self.font_small,  f"LEVEL   {level_name}", (180, 180, 180), 20, 132)

        # Timer (top right)
        mins = int(time_left) // 60
        secs = int(time_left) % 60
        timer_str = f"{mins}:{secs:02d}"
        timer_color = (255, 80, 80) if time_left <= 10 else (255, 255, 255)
        timer_surf = self.font_large.render(timer_str, True, timer_color)
        surf.blit(timer_surf, (self.width - timer_surf.get_width() - 20, 20))

        # FPS (bottom right, subtle)
        fps_surf = self.font_small.render(f"{fps:.0f} FPS", True, (120, 120, 120))
        surf.blit(fps_surf, (self.width - fps_surf.get_width() - 10,
                              self.height - fps_surf.get_height() - 10))

        # Ammo panel (bottom-right)
        margin_r = 18
        margin_b = 18
        bar_w    = 180
        bar_h    = 10
        pad      = 6

        if is_reloading:
            ammo_color = (255, 160, 30)
            ammo_str   = "RELOADING..."
        elif ammo <= 10:
            ammo_color = (255, 80, 80)
            ammo_str   = f"{ammo} / \u221e"
        else:
            ammo_color = (255, 255, 255)
            ammo_str   = f"{ammo} / \u221e"

        ammo_surf = self.font_ammo.render(ammo_str, True, ammo_color)
        shadow = self.font_ammo.render(ammo_str, True, (0, 0, 0))
        ax = self.width  - ammo_surf.get_width()  - margin_r
        ay = self.height - ammo_surf.get_height() - margin_b - bar_h - pad - 4
        surf.blit(shadow, (ax + 2, ay + 2))
        surf.blit(ammo_surf, (ax, ay))

        bar_x = self.width - bar_w - margin_r
        bar_y = self.height - bar_h - margin_b
        pygame.draw.rect(surf, (50, 50, 50, 200), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        if is_reloading:
            fill_w  = int(bar_w * reload_progress)
            bar_col = (255, 140, 20, 220)
        else:
            fill_frac = ammo / mag_size
            fill_w    = int(bar_w * fill_frac)
            if ammo <= 10:
                bar_col = (255, 60, 60, 220)
            else:
                bar_col = (60, 220, 120, 220)

        if fill_w > 0:
            pygame.draw.rect(surf, bar_col, (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        pygame.draw.rect(surf, (120, 120, 120, 180),
                         (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        if not is_reloading and ammo < mag_size:
            hint = self.font_tiny.render("[R] Reload", True, (160, 160, 160))
            surf.blit(hint, (bar_x, bar_y - hint.get_height() - 2))

        return surf

    def _upload_surface(self, surf: pygame.Surface):
        """Upload a Pygame surface as a ModernGL texture."""
        if self._hud_tex:
            self._hud_tex.release()
        data = pygame.image.tobytes(surf, 'RGBA', True)
        self._hud_tex = self.ctx.texture(
            (self.width, self.height), 4, data
        )
        self._hud_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)

    def draw_hud(self, score, accuracy, time_left, streak, level_name, fps,
                 ammo=30, mag_size=30, is_reloading=False, reload_progress=1.0):
        now_ms = pygame.time.get_ticks()
        if (now_ms - self._fps_last_update_ms) >= 250:
            self._fps_display = fps
            self._fps_last_update_ms = now_ms

        # Rebuild/upload HUD texture only when displayed values materially change.
        state_key = (
            int(score),
            round(float(accuracy), 1),
            int(float(time_left) * 10.0),
            int(streak),
            str(level_name),
            int(round(self._fps_display)),
            int(ammo),
            int(mag_size),
            bool(is_reloading),
            int(float(reload_progress) * 100.0),
        )

        if state_key != self._hud_state_key or self._hud_tex is None:
            surf = self._render_text_surface(
                score, accuracy, time_left, streak, level_name, self._fps_display,
                ammo=ammo, mag_size=mag_size,
                is_reloading=is_reloading, reload_progress=reload_progress,
            )
            self._upload_surface(surf)
            self._hud_state_key = state_key

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = True
        self.prog['color'].value = (1.0, 1.0, 1.0, 1.0)
        self.prog['screen_size'].value = (self.width, self.height)
        self.prog['offset'].value = (0.0, 0.0)
        self.prog['scale'].value  = (self.width / 2, self.height / 2)
        self._hud_tex.use(0)
        self.prog['tex'].value = 0
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_ammo_hud(self, ammo: int, mag_size: int,
                      is_reloading: bool, reload_progress: float):
        """
        Bottom-right corner ammo display:
          - Bullet count  e.g.  [III III III ...] or grayed-out slots
          - Ammo number   e.g.  24 / 
          - Orange progress bar + RELOADING text while reloading
        """
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        margin_r = 18
        margin_b = 18
        bar_w    = 180
        bar_h    = 10
        pad      = 6

        # Ammo number
        if is_reloading:
            ammo_color = (255, 160, 30)      # orange while reloading
            ammo_str   = "RELOADING..."
        elif ammo <= 10:
            ammo_color = (255, 80, 80)       # red when low
            ammo_str   = f"{ammo} / \u221e"
        else:
            ammo_color = (255, 255, 255)
            ammo_str   = f"{ammo} / \u221e"

        ammo_surf = self.font_ammo.render(ammo_str, True, ammo_color)
        # Shadow
        shadow = self.font_ammo.render(ammo_str, True, (0, 0, 0))
        ax = self.width  - ammo_surf.get_width()  - margin_r
        ay = self.height - ammo_surf.get_height() - margin_b - bar_h - pad - 4
        surf.blit(shadow, (ax + 2, ay + 2))
        surf.blit(ammo_surf, (ax, ay))

        # Reload progress bar track
        bar_x = self.width - bar_w - margin_r
        bar_y = self.height - bar_h - margin_b
        # Background track
        pygame.draw.rect(surf, (50, 50, 50, 200), (bar_x, bar_y, bar_w, bar_h), border_radius=4)

        # Filled portion
        if is_reloading:
            fill_w   = int(bar_w * reload_progress)
            bar_col  = (255, 140, 20, 220)    # orange fill
        else:
            fill_frac = ammo / mag_size
            fill_w    = int(bar_w * fill_frac)
            if ammo <= 10:
                bar_col = (255, 60, 60, 220)  # red when low
            else:
                bar_col = (60, 220, 120, 220) # green normally

        if fill_w > 0:
            pygame.draw.rect(surf, bar_col,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=4)

        # Border
        pygame.draw.rect(surf, (120, 120, 120, 180),
                         (bar_x, bar_y, bar_w, bar_h), width=1, border_radius=4)

        # R-to-reload hint (only when not reloading and ammo < mag)
        if not is_reloading and ammo < mag_size:
            hint = self.font_tiny.render("[R] Reload", True, (160, 160, 160))
            surf.blit(hint, (bar_x, bar_y - hint.get_height() - 2))

        self._upload_surface(surf)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = True
        self.prog['color'].value       = (1.0, 1.0, 1.0, 1.0)
        self.prog['screen_size'].value = (self.width, self.height)
        self.prog['offset'].value      = (0.0, 0.0)
        self.prog['scale'].value       = (self.width / 2, self.height / 2)
        self._hud_tex.use(0)
        self.prog['tex'].value = 0
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_crosshair(self, hit_marker_alpha: float = 0.0):
        """Draw a bright crosshair at screen center."""
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = False

        cx, cy = self.width / 2, self.height / 2
        gap   = 4   # gap from center
        arm   = 6   # arm length
        thick = 2    # half-thickness

        arms = [
            (gap, gap+arm, -thick, thick),
            (-gap-arm, -gap, -thick, thick),
            (-thick, thick, gap, gap+arm),
            (-thick, thick, -gap-arm, -gap),
        ]

        self.prog['color'].value = (0.0, 1.0, 0.8, 1.0)  # bright cyan crosshair
        for ax0, ax1, ay0, ay1 in arms:
            self._draw_rect(cx+ax0, cy+ay0, ax1-ax0, ay1-ay0)

        # Center dot
        self.prog['color'].value = (1.0, 1.0, 1.0, 1.0)
        self._draw_rect(cx - 2, cy - 2, 4, 4)

        self.ctx.enable(moderngl.DEPTH_TEST)

    def _draw_rect(self, x, y, w, h):
        """Draw a pixel-space rectangle using the HUD shader."""
        self.prog['screen_size'].value = (self.width,  self.height)
        self.prog['offset'].value  = (x + w/2 - self.width/2,
                                       y + h/2 - self.height/2)
        self.prog['scale'].value   = (w/2, h/2)
        self.quad_vao.render(moderngl.TRIANGLES)

    def draw_flash(self, color4):
        """Full-screen color flash with alpha blend."""
        r, g, b, a = color4
        if a <= 0.005:
            return
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = False
        self.prog['color'].value = (r, g, b, a)
        self.prog['screen_size'].value = (self.width,  self.height)
        self.prog['offset'].value  = (0.0, 0.0)
        self.prog['scale'].value   = (self.width/2, self.height/2)
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_vignette(self):
        """Subtle purple atmospheric strip at bottom  gives space ambience."""
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = False
        # Bottom strip: 120px tall, semi-transparent purple
        strip_h = 120
        self.prog['color'].value = (0.25, 0.05, 0.55, 0.18)
        self._draw_rect(0, self.height - strip_h, self.width, strip_h)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_ready_screen(self):
        """Pre-game overlay shown before the first shot is fired."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        # Subtle dark veil
        surf.fill((0, 0, 0, 120))

        def center(font, text, color, y):
            s = font.render(text, True, color)
            surf.blit(s, ((self.width - s.get_width()) // 2, y))

        cy = self.height // 2
        center(self.font_end,    "READY?",                       (255, 220, 60),  cy - 120)
        center(self.font_medium, "Left Click: Fire to Start",    (255, 255, 255), cy -  20)
        center(self.font_medium, "WASD: Move",                   (200, 200, 200), cy +  20)
        center(self.font_medium, "Shift: Sprint",                (200, 200, 200), cy +  56)
        center(self.font_small,  "ESC: Pause | R: Reload",       (140, 140, 140), cy + 100)

        self._upload_surface(surf)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = True
        self.prog['color'].value       = (1.0, 1.0, 1.0, 1.0)
        self.prog['screen_size'].value = (self.width, self.height)
        self.prog['offset'].value      = (0.0, 0.0)
        self.prog['scale'].value       = (self.width / 2, self.height / 2)
        self._hud_tex.use(0)
        self.prog['tex'].value = 0
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_pause_screen(self):
        """Mid-game pause overlay with resume and quit instructions."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 160))   # semi-transparent dark overlay

        def center(font, text, color, y):
            s = font.render(text, True, color)
            surf.blit(s, ((self.width - s.get_width()) // 2, y))

        cy = self.height // 2
        center(self.font_end,    "PAUSED",                         (255, 220, 60),  cy - 130)
        center(self.font_medium, "Click: Resume",                  (100, 220, 255), cy -  20)
        center(self.font_medium, "ESC: Quit Game",                (255, 130, 130), cy +  24)
        center(self.font_small,  "R to Reload when you resume",    (160, 160, 160), cy +  74)

        self._upload_surface(surf)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = True
        self.prog['color'].value       = (1.0, 1.0, 1.0, 1.0)
        self.prog['screen_size'].value = (self.width, self.height)
        self.prog['offset'].value      = (0.0, 0.0)
        self.prog['scale'].value       = (self.width / 2, self.height / 2)
        self._hud_tex.use(0)
        self.prog['tex'].value = 0
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def draw_end_screen(self, summary: dict):
        """Render a full end-screen overlay."""
        surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 200))

        def center_text(font, text, color, y):
            s = font.render(text, True, color)
            surf.blit(s, ((self.width - s.get_width()) // 2, y))

        center_text(self.font_end, "TIME'S UP!", (255, 220, 60), self.height//2 - 160)
        center_text(self.font_sub, f"Score:     {summary['hits']}", (255, 255, 255), self.height//2 - 80)
        center_text(self.font_sub, f"Accuracy:  {summary['accuracy']:.1f}%", (100, 220, 255), self.height//2 - 40)
        center_text(self.font_sub, f"Shots:     {summary['shots']}", (200, 200, 200), self.height//2)
        center_text(self.font_sub, f"Best Streak: {summary['best_streak']}", (255, 100, 220), self.height//2 + 40)
        center_text(self.font_medium, "Press R to Restart  |  ESC to Quit", (150, 150, 150), self.height//2 + 120)

        self._upload_surface(surf)
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.prog['use_texture'].value = True
        self.prog['color'].value = (1.0, 1.0, 1.0, 1.0)
        self.prog['screen_size'].value = (self.width, self.height)
        self.prog['offset'].value = (0.0, 0.0)
        self.prog['scale'].value  = (self.width/2, self.height/2)
        self._hud_tex.use(0)
        self.prog['tex'].value = 0
        self.quad_vao.render(moderngl.TRIANGLES)
        self.ctx.enable(moderngl.DEPTH_TEST)

    def destroy(self):
        self.quad_vao.release()
        self.quad_vbo.release()
        self.quad_ibo.release()
        if self._hud_tex:
            self._hud_tex.release()
