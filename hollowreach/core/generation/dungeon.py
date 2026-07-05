"""Random dungeon generation (design plan §4.3).

Produces a persistent level with rooms joined by corridors, up/down
stairs, and a few injected **features** (altars, forges, herb bushes) —
the "level features injected by generator" the plan lists.  Interiors are
randomized per generation but, once made, a level is kept for the rest of
the run.  Monster and item density are keyed to the dungeon level (DL).

This is a classic rooms-and-corridors generator (BSP-free, simple and
robust) — enough for the foundational slice; caverns/vaults are added as
additional generators behind the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.rng import Rng
from ..world.level import Level
from ..world import tile
from ..model.character import make_monster
from .loot import roll_loot
from ...content.monsters import MONSTERS, spawn_table_for_dl


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    def intersects(self, other: "Room", pad: int = 1) -> bool:
        return (
            self.x - pad <= other.x + other.w
            and self.x + self.w + pad >= other.x
            and self.y - pad <= other.y + other.h
            and self.y + self.h + pad >= other.y
        )

    def random_floor(self, rng: Rng) -> tuple[int, int]:
        return (rng.randint(self.x, self.x + self.w - 1),
                rng.randint(self.y, self.y + self.h - 1))


def generate_level(rng: Rng, depth: int = 1, width: int = 70, height: int = 21,
                   max_rooms: int = 12, is_final: bool = False) -> Level:
    level = Level(width, height, depth=depth)
    level.is_final = is_final
    level.gate = None
    level.boss = None
    rooms: list[Room] = []

    for _ in range(max_rooms * 3):
        if len(rooms) >= max_rooms:
            break
        w = rng.randint(4, 11)
        h = rng.randint(3, 6)
        x = rng.randint(1, width - w - 1)
        y = rng.randint(1, height - h - 1)
        room = Room(x, y, w, h)
        if any(room.intersects(r) for r in rooms):
            continue
        _carve_room(level, room)
        if rooms:
            _connect(level, rng, rooms[-1], room)
        rooms.append(room)

    if not rooms:  # degenerate guard
        rooms.append(Room(1, 1, width - 2, height - 2))
        _carve_room(level, rooms[0])

    _place_stairs(level, rng, rooms, is_final)
    _inject_features(level, rng, rooms, depth)
    _populate(level, rng, rooms, depth)
    _place_items(level, rng, rooms, depth)
    if is_final:
        _place_gate_and_boss(level, rng, rooms)
    level.rooms = rooms  # kept for spawn placement / debugging
    return level


def _place_gate_and_boss(level: Level, rng: Rng, rooms: list[Room]) -> None:
    """Set the Sundered Gate and its guardian in the deepest room (§14)."""
    gate_room = rooms[-1]
    gx, gy = gate_room.cx, gate_room.cy
    level.set_tile(gx, gy, tile.GATE)
    level.gate = (gx, gy)

    boss = make_monster(MONSTERS["vurgast"], rng, depth=level.depth)
    # Plant the guardian next to the Gate, on open floor.
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1)):
        bx, by = gx + dx, gy + dy
        if level.is_walkable(bx, by) and level.actor_at(bx, by) is None:
            boss.x, boss.y = bx, by
            break
    else:
        boss.x, boss.y = gx, gy
    level.add_actor(boss)
    level.boss = boss


def _place_items(level: Level, rng: Rng, rooms: list[Room], depth: int) -> None:
    """Scatter loot piles keyed to dungeon level (§4.3, §11)."""
    count = rng.randint(2, 4) + depth // 3
    for _ in range(count):
        room = rng.choice(rooms)
        ix, iy = room.random_floor(rng)
        if not level.is_walkable(ix, iy):
            continue
        if level.tile(ix, iy) in (tile.STAIRS_UP, tile.STAIRS_DOWN):
            continue
        level.add_item(ix, iy, roll_loot(rng, depth))


def _carve_room(level: Level, room: Room) -> None:
    for yy in range(room.y, room.y + room.h):
        for xx in range(room.x, room.x + room.w):
            level.set_tile(xx, yy, tile.FLOOR)


def _connect(level: Level, rng: Rng, a: Room, b: Room) -> None:
    x1, y1 = a.cx, a.cy
    x2, y2 = b.cx, b.cy
    if rng.one_in(2):
        _h_corridor(level, x1, x2, y1)
        _v_corridor(level, y1, y2, x2)
    else:
        _v_corridor(level, y1, y2, x1)
        _h_corridor(level, x1, x2, y2)


def _h_corridor(level: Level, x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        if level.tile(x, y) is tile.WALL:
            level.set_tile(x, y, tile.CORRIDOR)


def _v_corridor(level: Level, y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        if level.tile(x, y) is tile.WALL:
            level.set_tile(x, y, tile.CORRIDOR)


def _place_stairs(level: Level, rng: Rng, rooms: list[Room],
                  is_final: bool = False) -> None:
    up_room = rooms[0]
    ux, uy = up_room.cx, up_room.cy
    level.set_tile(ux, uy, tile.STAIRS_UP)
    level.stairs_up = (ux, uy)
    if is_final:
        level.stairs_down = None   # the bottom: only the Gate lies beyond
        return
    down_room = rooms[-1]
    dx, dy = down_room.random_floor(rng)
    level.set_tile(dx, dy, tile.STAIRS_DOWN)
    level.stairs_down = (dx, dy)


def _inject_features(level: Level, rng: Rng, rooms: list[Room], depth: int) -> None:
    # Occasional altar / forge / herb bush, weighted low (§4.3, §10.3).
    if rng.one_in(6) and len(rooms) > 2:
        room = rng.choice(rooms[1:-1])
        fx, fy = room.random_floor(rng)
        level.set_tile(fx, fy, tile.ALTAR)
    if rng.one_in(8) and len(rooms) > 2:
        room = rng.choice(rooms[1:-1])
        fx, fy = room.random_floor(rng)
        if level.tile(fx, fy) is tile.FLOOR:
            level.set_tile(fx, fy, tile.FORGE)
    for _ in range(rng.rnd(3) - 1):
        room = rng.choice(rooms)
        fx, fy = room.random_floor(rng)
        if level.tile(fx, fy) is tile.FLOOR:
            level.set_tile(fx, fy, tile.HERB_BUSH)


def _populate(level: Level, rng: Rng, rooms: list[Room], depth: int) -> None:
    table = spawn_table_for_dl(depth)
    if not table:
        return
    # Density grows slowly with depth; never spawn on the up-stair room.
    count = rng.randint(3, 5) + depth // 2
    for _ in range(count):
        room = rng.choice(rooms[1:]) if len(rooms) > 1 else rooms[0]
        mx, my = room.random_floor(rng)
        if not level.is_walkable(mx, my) or level.actor_at(mx, my):
            continue
        if level.tile(mx, my) in (tile.STAIRS_UP, tile.STAIRS_DOWN):
            continue
        mon_id = rng.weighted_choice(table)
        mdef = MONSTERS[mon_id]
        monster = make_monster(mdef, rng, depth=depth)
        monster.x, monster.y = mx, my
        level.add_actor(monster)
