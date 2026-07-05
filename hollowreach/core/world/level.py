"""A single dungeon level: the tile grid plus its occupants.

Levels are **persistent** once generated (design plan §4.3) — the game
keeps the map, remembered tiles, and item piles for the rest of the run.
This class is just the container; generation lives in
``core.generation`` and monster/PC logic lives in ``core.model``.
"""

from __future__ import annotations

from typing import Iterable

from .tile import WALL, TileType, DOOR_CLOSED, DOOR_OPEN


class Level:
    def __init__(self, width: int, height: int, depth: int = 1):
        self.width = width
        self.height = height
        self.depth = depth  # dungeon level (DL) — drives spawn tables (§4.3)
        self._tiles: list[list[TileType]] = [
            [WALL for _ in range(width)] for _ in range(height)
        ]
        # Fog-of-war: tiles the PC has ever seen (remembered even in dark).
        self.explored: list[list[bool]] = [
            [False for _ in range(width)] for _ in range(height)
        ]
        self.actors: list = []  # monsters + the PC
        self.items: dict[tuple[int, int], list] = {}  # floor item piles
        self.stairs_down: "tuple[int, int] | None" = None
        self.stairs_up: "tuple[int, int] | None" = None
        # Endgame (§14): populated on the bottom level.
        self.is_final: bool = False
        self.gate: "tuple[int, int] | None" = None
        self.boss = None

    # -- geometry ---------------------------------------------------------
    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def tile(self, x: int, y: int) -> TileType:
        return self._tiles[y][x]

    def set_tile(self, x: int, y: int, tile: TileType) -> None:
        self._tiles[y][x] = tile

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self._tiles[y][x].walkable

    def is_transparent(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self._tiles[y][x].transparent

    def blocks_move(self, x: int, y: int) -> bool:
        return not self.is_walkable(x, y)

    # -- occupancy --------------------------------------------------------
    def actor_at(self, x: int, y: int):
        for actor in self.actors:
            if actor.is_alive and actor.x == x and actor.y == y:
                return actor
        return None

    def add_actor(self, actor) -> None:
        self.actors.append(actor)
        actor.level = self

    def remove_actor(self, actor) -> None:
        if actor in self.actors:
            self.actors.remove(actor)

    def monsters(self) -> Iterable:
        return [a for a in self.actors if a.is_alive and not a.is_player]

    # -- items ------------------------------------------------------------
    def items_at(self, x: int, y: int) -> list:
        return self.items.get((x, y), [])

    def add_item(self, x: int, y: int, item) -> None:
        self.items.setdefault((x, y), []).append(item)

    def take_top_item(self, x: int, y: int):
        pile = self.items.get((x, y))
        if not pile:
            return None
        item = pile.pop()
        if not pile:
            del self.items[(x, y)]
        return item

    # -- interaction ------------------------------------------------------
    def open_door(self, x: int, y: int) -> bool:
        if self.tile(x, y) is DOOR_CLOSED:
            self.set_tile(x, y, DOOR_OPEN)
            return True
        return False
