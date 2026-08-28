"""
game/raycaster.py - Ray-sphere intersection for precise hit detection
"""
import numpy as np


def ray_sphere_intersect(ray_origin, ray_dir, sphere_center, sphere_radius):
    """
    Analytic ray-sphere intersection.
    Returns distance t > 0 if intersection, else None.
    """
    oc = ray_origin - sphere_center
    a = np.dot(ray_dir, ray_dir)
    b = 2.0 * np.dot(oc, ray_dir)
    c = np.dot(oc, oc) - sphere_radius * sphere_radius
    discriminant = b * b - 4 * a * c

    if discriminant < 0:
        return None

    sq = np.sqrt(discriminant)
    t1 = (-b - sq) / (2.0 * a)
    t2 = (-b + sq) / (2.0 * a)

    if t1 > 0.01:
        return t1
    if t2 > 0.01:
        return t2
    return None


def find_hit_target(targets, ray_origin, ray_dir):
    """
    Check all living targets and return the closest hit.
    Returns (target, distance, is_headshot) where is_headshot is always False.
    """
    closest_t = float('inf')
    hit_target = None

    ray_orig = np.array(ray_origin, dtype='f4')
    ray_d    = np.array(ray_dir,    dtype='f4')

    for target in targets:
        if not target.alive:
            continue
            
        s = target.scale
        if s <= 0.01:
            continue

        t_hit = ray_sphere_intersect(
            ray_orig,
            ray_d,
            np.array(target.pos, dtype='f4'),
            target.get_effective_radius(),
        )

        if t_hit is not None and t_hit < closest_t:
            closest_t = t_hit
            hit_target = target

    if hit_target is not None:
        return hit_target, closest_t, False
    return None, None, False
