"""
engine/mesh.py - VBO/VAO mesh primitives: sphere, quad, box, gun
"""
import numpy as np
import math
import moderngl


def _make_sphere(stacks=24, slices=24, radius=1.0):
    """
    Generate a UV sphere.
    Returns interleaved float32 array: [x, y, z, nx, ny, nz, u, v] per vertex
    and an index array.
    """
    vertices = []
    indices = []

    for i in range(stacks + 1):
        phi = math.pi / 2 - i * math.pi / stacks  # +pi/2 to -pi/2
        y = radius * math.sin(phi)
        xz = radius * math.cos(phi)
        for j in range(slices + 1):
            theta = j * 2 * math.pi / slices
            x = xz * math.cos(theta)
            z = xz * math.sin(theta)
            nx, ny, nz = x / radius, y / radius, z / radius
            u = j / slices
            v = i / stacks
            vertices.extend([x, y, z, nx, ny, nz, u, v])

    for i in range(stacks):
        for j in range(slices):
            first = i * (slices + 1) + j
            second = first + slices + 1
            indices.extend([first, second, first + 1,
                             second, second + 1, first + 1])

    return np.array(vertices, dtype='f4'), np.array(indices, dtype='i4')


def _make_box(w=1.0, h=1.0, d=1.0):
    """Simple box with normals (6 faces, 2 tris each)."""
    hw, hh, hd = w/2, h/2, d/2
    faces = [
        # pos, normal, uv
        # Front
        ([-hw,-hh, hd],[0,0,1],[0,0]), ([ hw,-hh, hd],[0,0,1],[1,0]),
        ([ hw, hh, hd],[0,0,1],[1,1]), ([-hw, hh, hd],[0,0,1],[0,1]),
        # Back
        ([ hw,-hh,-hd],[0,0,-1],[0,0]),([-hw,-hh,-hd],[0,0,-1],[1,0]),
        ([-hw, hh,-hd],[0,0,-1],[1,1]),([ hw, hh,-hd],[0,0,-1],[0,1]),
        # Left
        ([-hw,-hh,-hd],[-1,0,0],[0,0]),([-hw,-hh, hd],[-1,0,0],[1,0]),
        ([-hw, hh, hd],[-1,0,0],[1,1]),([-hw, hh,-hd],[-1,0,0],[0,1]),
        # Right
        ([ hw,-hh, hd],[1,0,0],[0,0]),([ hw,-hh,-hd],[1,0,0],[1,0]),
        ([ hw, hh,-hd],[1,0,0],[1,1]),([ hw, hh, hd],[1,0,0],[0,1]),
        # Top
        ([-hw, hh, hd],[0,1,0],[0,0]),([ hw, hh, hd],[0,1,0],[1,0]),
        ([ hw, hh,-hd],[0,1,0],[1,1]),([-hw, hh,-hd],[0,1,0],[0,1]),
        # Bottom
        ([-hw,-hh,-hd],[0,-1,0],[0,0]),([ hw,-hh,-hd],[0,-1,0],[1,0]),
        ([ hw,-hh, hd],[0,-1,0],[1,1]),([-hw,-hh, hd],[0,-1,0],[0,1]),
    ]
    verts = []
    idxs  = []
    for fi in range(6):
        base = fi * 4
        f = faces[fi*4:fi*4+4]
        for p, n, uv in f:
            verts.extend(p + n + uv)
        idxs.extend([base, base+1, base+2, base, base+2, base+3])
    return np.array(verts, dtype='f4'), np.array(idxs, dtype='i4')


class SphereMesh:
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program,
                 stacks=24, slices=24):
        verts, idxs = _make_sphere(stacks, slices, radius=1.0)
        self.vbo = ctx.buffer(verts.tobytes())
        self.ibo = ctx.buffer(idxs.tobytes())
        self.vao = ctx.vertex_array(
            program,
            [(self.vbo, '3f 3f 2x4', 'in_position', 'in_normal')],
            self.ibo
        )
        self.index_count = len(idxs)

    def render(self):
        self.vao.render(moderngl.TRIANGLES)

    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.ibo.release()


class BoxMesh:
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program,
                 w=1.0, h=1.0, d=1.0):
        verts, idxs = _make_box(w, h, d)
        self.vbo = ctx.buffer(verts.tobytes())
        self.ibo = ctx.buffer(idxs.tobytes())
        self.vao = ctx.vertex_array(
            program,
            [(self.vbo, '3f 3f 2x4', 'in_position', 'in_normal')],
            self.ibo
        )
        self.index_count = len(idxs)

    def render(self):
        self.vao.render(moderngl.TRIANGLES)

    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.ibo.release()


class QuadMesh:
    """Screen-space full-screen quad for skybox / HUD."""
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        # Screen-space quad (-1 to 1 in XY), with UV
        verts = np.array([
            -1, -1,  0, 0,
             1, -1,  1, 0,
             1,  1,  1, 1,
            -1,  1,  0, 1,
        ], dtype='f4')
        idxs = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
        self.vbo = ctx.buffer(verts.tobytes())
        self.ibo = ctx.buffer(idxs.tobytes())
        attrs = program._attribute_names if hasattr(program, '_attribute_names') else []
        if 'in_uv' in str(program):
            fmt = '2f 2f'
            names = ('in_position', 'in_uv')
        else:
            fmt = '2f 2f'
            names = ('in_position', 'in_uv')
        self.vao = ctx.vertex_array(
            program,
            [(self.vbo, '2f 2f', 'in_position', 'in_uv')],
            self.ibo
        )

    def render(self):
        self.vao.render(moderngl.TRIANGLES)

    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.ibo.release()


class SkyboxQuad:
    """Full-screen quad using only position (no UV attr)."""
    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        verts = np.array([
            -1, -1,
             1, -1,
             1,  1,
            -1,  1,
        ], dtype='f4')
        idxs = np.array([0, 1, 2, 0, 2, 3], dtype='i4')
        self.vbo = ctx.buffer(verts.tobytes())
        self.ibo = ctx.buffer(idxs.tobytes())
        self.vao = ctx.vertex_array(
            program,
            [(self.vbo, '2f', 'in_position')],
            self.ibo
        )

    def render(self):
        self.vao.render(moderngl.TRIANGLES)

    def destroy(self):
        self.vao.release()
        self.vbo.release()
        self.ibo.release()
