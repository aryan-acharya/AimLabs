"""
game/gun.py - AK-47 first-person gun model (procedural boxes),
              two-colour rendering (metal + wood), recoil + reload mechanics.
"""
import numpy as np
import pyrr
import moderngl


# Box geometry helper
def _box_mesh(cx, cy, cz, w, h, d):
    """Return (verts_list, idxs_list) for one axis-aligned box."""
    hw, hh, hd = w / 2, h / 2, d / 2
    faces = [
        # Front +Z
        ([-hw,-hh, hd],[0,0,1],[0,0]), ([ hw,-hh, hd],[0,0,1],[1,0]),
        ([ hw, hh, hd],[0,0,1],[1,1]), ([-hw, hh, hd],[0,0,1],[0,1]),
        # Back -Z
        ([ hw,-hh,-hd],[0,0,-1],[0,0]),([-hw,-hh,-hd],[0,0,-1],[1,0]),
        ([-hw, hh,-hd],[0,0,-1],[1,1]),([ hw, hh,-hd],[0,0,-1],[0,1]),
        # Left -X
        ([-hw,-hh,-hd],[-1,0,0],[0,0]),([-hw,-hh, hd],[-1,0,0],[1,0]),
        ([-hw, hh, hd],[-1,0,0],[1,1]),([-hw, hh,-hd],[-1,0,0],[0,1]),
        # Right +X
        ([ hw,-hh, hd],[1,0,0],[0,0]),([ hw,-hh,-hd],[1,0,0],[1,0]),
        ([ hw, hh,-hd],[1,0,0],[1,1]),([ hw, hh, hd],[1,0,0],[0,1]),
        # Top +Y
        ([-hw, hh, hd],[0,1,0],[0,0]),([ hw, hh, hd],[0,1,0],[1,0]),
        ([ hw, hh,-hd],[0,1,0],[1,1]),([-hw, hh,-hd],[0,1,0],[0,1]),
        # Bottom -Y
        ([-hw,-hh,-hd],[0,-1,0],[0,0]),([ hw,-hh,-hd],[0,-1,0],[1,0]),
        ([ hw,-hh, hd],[0,-1,0],[1,1]),([-hw,-hh, hd],[0,-1,0],[0,1]),
    ]
    verts, idxs, base = [], [], 0
    for fi in range(6):
        for p, n, uv in faces[fi*4:fi*4+4]:
            verts.extend([p[0]+cx, p[1]+cy, p[2]+cz] + n + uv)
        idxs.extend([base, base+1, base+2, base, base+2, base+3])
        base += 4
    return verts, idxs


def _build_group(boxes):
    """Merge a list of (cx,cy,cz,w,h,d) boxes into one flat vertex+index arrays."""
    all_v, all_i = [], []
    for args in boxes:
        v, i = _box_mesh(*args)
        offset = len(all_v) // 8
        all_v.extend(v)
        all_i.extend(x + offset for x in i)
    return (np.array(all_v, dtype='f4'),
            np.array(all_i,  dtype='i4'))


# AK-47 part definitions split by material

# Dark metal: receiver, barrel, gas tube, handguard, sight rail, mag body
METAL_PARTS = [
    # cx cy cz w h d
    (0.17, -0.190, -0.420, 0.055, 0.065, 0.280),   # receiver body
    (0.17, -0.175, -0.680, 0.025, 0.025, 0.500),   # long barrel
    (0.17, -0.155, -0.620, 0.018, 0.015, 0.360),   # gas tube above barrel
    (0.17, -0.178, -0.520, 0.038, 0.038, 0.140),   # front handguard
    (0.17, -0.158, -0.400, 0.042, 0.012, 0.220),   # top sight / dust-cover rail
    (0.17, -0.285, -0.420, 0.030, 0.055, 0.085),   # mag upper segment
    (0.17, -0.315, -0.460, 0.030, 0.040, 0.075),   # mag lower / forward curve
]

# Warm wood / polymer: pistol grip, rear stock
WOOD_PARTS = [
    (0.17, -0.265, -0.380, 0.030, 0.090, 0.055),   # pistol grip
    (0.17, -0.205, -0.210, 0.048, 0.048, 0.160),   # rear stock body
    (0.17, -0.210, -0.090, 0.048, 0.060, 0.035),   # stock butt plate
]

# AK-47 colours
COLOR_METAL = (0.10, 0.11, 0.09)   # dark olive-black steel
COLOR_WOOD  = (0.42, 0.24, 0.10)   # warm walnut brown


# Gun class
class Gun:
    MAG_SIZE      = 30
    RELOAD_TIME   = 2.0   # seconds

    def __init__(self, ctx: moderngl.Context, program: moderngl.Program):
        self.program = program

        # Build two separate VAOs one per material group
        mv, mi = _build_group(METAL_PARTS)
        wv, wi = _build_group(WOOD_PARTS)

        self.metal_vbo = ctx.buffer(mv.tobytes())
        self.metal_ibo = ctx.buffer(mi.tobytes())
        self.metal_vao = ctx.vertex_array(
            program,
            [(self.metal_vbo, '3f 3f 2x4', 'in_position', 'in_normal')],
            self.metal_ibo
        )
        self.metal_count = len(mi)

        self.wood_vbo = ctx.buffer(wv.tobytes())
        self.wood_ibo = ctx.buffer(wi.tobytes())
        self.wood_vao = ctx.vertex_array(
            program,
            [(self.wood_vbo, '3f 3f 2x4', 'in_position', 'in_normal')],
            self.wood_ibo
        )
        self.wood_count = len(wi)

        # Recoil state
        self.recoil_offset = 0.0
        self.recoil_speed  = 0.0
        self.recoil_return = 6.0

        # Ammo / reload state
        self.ammo         = self.MAG_SIZE
        self.is_reloading = False
        self.reload_timer = 0.0          # counts UP toward RELOAD_TIME
        self.reload_drop  = 0.0          # y-offset during reload animation

    # Public API
    def can_fire(self) -> bool:
        return self.ammo > 0 and not self.is_reloading

    def fire(self):
        """Consume one bullet and apply recoil.  Auto-reloads when empty."""
        if not self.can_fire():
            return
        self.ammo -= 1
        self.recoil_offset = 0.10
        self.recoil_speed  = -0.5
        if self.ammo == 0:
            self._begin_reload()

    def start_reload(self):
        """Manually trigger reload (R key). Ignored if mag is full or already reloading."""
        if not self.is_reloading and self.ammo < self.MAG_SIZE:
            self._begin_reload()

    def _begin_reload(self):
        self.is_reloading = True
        self.reload_timer = 0.0

    @property
    def reload_progress(self) -> float:
        """0.0  1.0 fraction of reload completed."""
        if not self.is_reloading:
            return 1.0
        return min(self.reload_timer / self.RELOAD_TIME, 1.0)

    # Update
    def update(self, dt: float):
        # Recoil spring
        self.recoil_offset += self.recoil_speed * dt
        self.recoil_speed  += (0 - self.recoil_speed) * self.recoil_return * dt
        self.recoil_offset  = max(0.0, self.recoil_offset * (1 - self.recoil_return * dt * 0.5))
        if abs(self.recoil_offset) < 0.001:
            self.recoil_offset = 0.0
            self.recoil_speed  = 0.0

        # Reload countdown
        if self.is_reloading:
            self.reload_timer += dt
            # Animate gun dropping slightly during reload
            frac = self.reload_timer / self.RELOAD_TIME
            peak = 0.5                           # midpoint of animation
            if frac <= peak:
                self.reload_drop = -0.06 * (frac / peak)
            else:
                self.reload_drop = -0.06 * (1.0 - (frac - peak) / (1.0 - peak))

            if self.reload_timer >= self.RELOAD_TIME:
                self.ammo         = self.MAG_SIZE
                self.is_reloading = False
                self.reload_timer = 0.0
                self.reload_drop  = 0.0
        else:
            self.reload_drop = 0.0

    # Transform
    def get_model_matrix(self):
        trans = pyrr.matrix44.create_from_translation(
            [0.0, self.reload_drop, self.recoil_offset], dtype='f4'
        )
        return trans

    # Render
    def render(self):
        """Render both material groups with their own colours."""
        prog = self.program

        # Metal parts
        prog['object_color'].value = COLOR_METAL
        self.metal_vao.render(moderngl.TRIANGLES)

        # Wood / polymer parts
        prog['object_color'].value = COLOR_WOOD
        self.wood_vao.render(moderngl.TRIANGLES)

    # Cleanup
    def destroy(self):
        self.metal_vao.release(); self.metal_vbo.release(); self.metal_ibo.release()
        self.wood_vao.release();  self.wood_vbo.release();  self.wood_ibo.release()
