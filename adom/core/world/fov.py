"""Field of view via recursive shadowcasting (design plan §4.1).

Sight range is passed in by the caller, which is where the plan's
modifiers live: full radius by day, ~2 tiles at night, further adjusted
by Perception, torches and Farsight (see ``LightingService`` in
``core.rules``).  This module only answers "given this radius and these
opaque tiles, what can the origin see?"
"""

from __future__ import annotations

# The eight octant transforms for recursive shadowcasting.
_OCTANTS = [
    (1, 0, 0, 1), (0, 1, 1, 0), (0, -1, 1, 0), (-1, 0, 0, 1),
    (-1, 0, 0, -1), (0, -1, -1, 0), (0, 1, -1, 0), (1, 0, 0, -1),
]


def compute_fov(level, ox: int, oy: int, radius: int) -> set[tuple[int, int]]:
    """Return the set of visible ``(x, y)`` cells from ``(ox, oy)``."""
    visible: set[tuple[int, int]] = {(ox, oy)}
    for xx, xy, yx, yy in _OCTANTS:
        _cast_light(level, ox, oy, radius, 1, 1.0, 0.0, xx, xy, yx, yy, visible)
    return visible


def _cast_light(level, ox, oy, radius, row, start_slope, end_slope,
                xx, xy, yx, yy, visible):
    if start_slope < end_slope:
        return
    radius_sq = radius * radius
    for i in range(row, radius + 1):
        dx, dy = -i - 1, -i
        blocked = False
        new_start = start_slope
        while dx <= 0:
            dx += 1
            mx = ox + dx * xx + dy * xy
            my = oy + dx * yx + dy * yy
            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)
            if start_slope < r_slope:
                continue
            if end_slope > l_slope:
                break
            if dx * dx + dy * dy <= radius_sq and level.in_bounds(mx, my):
                visible.add((mx, my))
            if blocked:
                if not level.is_transparent(mx, my):
                    new_start = r_slope
                    continue
                blocked = False
                start_slope = new_start
            else:
                if not level.is_transparent(mx, my) and i < radius:
                    blocked = True
                    _cast_light(level, ox, oy, radius, i + 1, start_slope,
                                l_slope, xx, xy, yx, yy, visible)
                    new_start = r_slope
        if blocked:
            break
