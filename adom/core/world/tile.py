"""Tile definitions for the level grid (design plan §4.3).

Kept minimal for the foundational slice: floor, walls, doors, stairs,
water/lava, and the injected features the generator can place (altars,
forges, herb bushes).  Each tile knows whether it blocks movement and
whether it blocks sight, which is all the scheduler/FOV/combat code
needs.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TileType:
    key: str
    glyph: str
    walkable: bool
    transparent: bool
    name: str


# Terrain --------------------------------------------------------------
WALL = TileType("wall", "#", walkable=False, transparent=False, name="rock wall")
FLOOR = TileType("floor", ".", walkable=True, transparent=True, name="floor")
CORRIDOR = TileType("corridor", ".", walkable=True, transparent=True, name="corridor")
DOOR_CLOSED = TileType("door_closed", "+", walkable=True, transparent=False, name="door")
DOOR_OPEN = TileType("door_open", "'", walkable=True, transparent=True, name="open door")
STAIRS_DOWN = TileType("stairs_down", ">", walkable=True, transparent=True, name="staircase down")
STAIRS_UP = TileType("stairs_up", "<", walkable=True, transparent=True, name="staircase up")
WATER = TileType("water", "~", walkable=True, transparent=True, name="water")
LAVA = TileType("lava", "&", walkable=True, transparent=True, name="lava")

# Injected features (§4.3, §10.3) ------------------------------------
ALTAR = TileType("altar", "_", walkable=True, transparent=True, name="altar")
FORGE = TileType("forge", "\\", walkable=True, transparent=True, name="forge")
HERB_BUSH = TileType("herb_bush", "\"", walkable=True, transparent=True, name="herb bush")

ALL_TILES = {
    t.key: t
    for t in [
        WALL, FLOOR, CORRIDOR, DOOR_CLOSED, DOOR_OPEN, STAIRS_DOWN,
        STAIRS_UP, WATER, LAVA, ALTAR, FORGE, HERB_BUSH,
    ]
}
