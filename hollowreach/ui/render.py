"""ASCII renderer and message log (design plan §17.1 UI layer).

Renders the level as a grid of glyphs with fog-of-war: visible cells are
drawn bright, previously-seen cells dim (remembered), the rest blank.  A
status line surfaces HP/PP, dungeon level, speed and the Hollowreach
calendar; the message log shows recent events.

The renderer returns plain strings so it works headless (demo/tests) and
under curses alike.
"""

from __future__ import annotations

from collections import deque

from ..core.world import tile as tiles


class MessageLog:
    def __init__(self, capacity: int = 200):
        self._messages: deque[str] = deque(maxlen=capacity)

    def add(self, text: str) -> None:
        if text:
            self._messages.append(text)

    def recent(self, n: int = 5) -> list[str]:
        return list(self._messages)[-n:]


def render_level(level, player, visible: set[tuple[int, int]]) -> str:
    rows = []
    for y in range(level.height):
        chars = []
        for x in range(level.width):
            chars.append(_cell_glyph(level, player, visible, x, y))
        rows.append("".join(chars))
    return "\n".join(rows)


def _cell_glyph(level, player, visible, x, y) -> str:
    seen = (x, y) in visible
    if seen:
        actor = level.actor_at(x, y)
        if actor is not None and actor.is_alive:
            return actor.glyph
        pile = level.items_at(x, y)
        if pile:
            return getattr(pile[-1], "glyph", "*")
        return level.tile(x, y).glyph
    if level.explored[y][x]:
        # Remembered but not currently visible: terrain only, dimmed.
        return level.tile(x, y).glyph
    return " "


def status_line(pc) -> str:
    a = pc.actor
    warps = len(getattr(pc, "warps", []))
    blight = f"  Warps:{warps}" if warps else ""
    depth = a.level.depth if a.level else 0
    where = "Town" if depth == 0 else f"DL:{depth}"
    return (
        f"{a.name}  L{a.char_level} {pc.race.name} {pc.cls.name}  "
        f"HP:{a.hp}/{a.max_hp}  PP:{a.pp}/{a.max_pp}  "
        f"DV:{a.dv} PV:{a.pv}  Sp:{a.speed}  "
        f"{where}  Gold:{getattr(pc, 'gold', 0)}  "
        f"XP:{pc.xp}{blight}"
    )


def render_screen(level, pc, visible, log, message_lines: int = 4) -> str:
    parts = [render_level(level, pc.actor, visible), "", status_line(pc)]
    recent = log.recent(message_lines)
    if recent:
        parts.append("")
        parts.extend(recent)
    return "\n".join(parts)
