"""
engine/window.py - ModernGL + Pygame window and context management
"""
import pygame
import moderngl


class Window:
    def __init__(self, width=1280, height=720, title="AimLabs 3D"):
        self.width = width
        self.height = height
        self.title = title
        self.sound_enabled = False

        # Initialize pygame
        pygame.init()

        # Initialize audio safely
        try:
            pygame.mixer.init()
            self.sound_enabled = True
        except pygame.error:
            self.sound_enabled = False

        # Window title
        pygame.display.set_caption(self.title)

        # Request OpenGL 3.3 core
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK,
            pygame.GL_CONTEXT_PROFILE_CORE
        )
        pygame.display.gl_set_attribute(pygame.GL_DEPTH_SIZE, 24)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLEBUFFERS, 1)
        pygame.display.gl_set_attribute(pygame.GL_MULTISAMPLESAMPLES, 4)

        # Create display in windowed mode to avoid exclusive fullscreen focus
        # issues that can interfere with other desktop applications.
        self.screen = pygame.display.set_mode(
            (self.width, self.height),
            pygame.OPENGL | pygame.DOUBLEBUF | pygame.HWSURFACE
        )

        # Create ModernGL context
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (
            moderngl.SRC_ALPHA,
            moderngl.ONE_MINUS_SRC_ALPHA
        )

        # Mouse settings
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)
        pygame.mouse.set_pos(self.width // 2, self.height // 2)
        pygame.event.get()  # clear initial mouse movement event

        self.clock = pygame.time.Clock()
        self.running = True

    def swap_buffers(self):
        pygame.display.flip()

    def get_dt(self, fps_cap=144):
        ms = self.clock.tick(fps_cap)
        return min(ms / 1000.0, 0.05)

    def get_fps(self):
        return self.clock.get_fps()

    def release_mouse(self):
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)

    def capture_mouse(self):
        pygame.mouse.set_visible(False)
        pygame.event.set_grab(True)

    def destroy(self):
        try:
            self.ctx.release()
        except Exception:
            pass

        pygame.quit()
