"""
engine/shader.py - Shader loader and program cache
"""
import os
import moderngl


class ShaderManager:
    def __init__(self, ctx: moderngl.Context, shader_dir: str):
        self.ctx = ctx
        self.shader_dir = shader_dir
        self._cache = {}

    def load(self, name: str) -> moderngl.Program:
        """Load and compile a shader program by base name (looks for name.vert / name.frag)."""
        if name in self._cache:
            return self._cache[name]

        vert_path = os.path.join(self.shader_dir, f"{name}.vert")
        frag_path = os.path.join(self.shader_dir, f"{name}.frag")

        with open(vert_path, 'r') as f:
            vert_src = f.read()
        with open(frag_path, 'r') as f:
            frag_src = f.read()

        program = self.ctx.program(
            vertex_shader=vert_src,
            fragment_shader=frag_src
        )
        self._cache[name] = program
        return program

    def destroy(self):
        for prog in self._cache.values():
            prog.release()
        self._cache.clear()
