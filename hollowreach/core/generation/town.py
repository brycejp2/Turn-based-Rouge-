"""Hearthvale generation — the safe surface hub (design ref §4.4).

Builds the village the run starts in: a cluster of buildings joined by
paths, the townsfolk placed inside, and the mouth of the Sundered Depths
(a down-staircase) at the far end.  No monsters, no Blight — a place to
trade, take quests, and steel yourself before the next dive.
"""

from __future__ import annotations

from ..engine.rng import Rng
from ..world.level import Level
from ..world import tile
from ..model.attributes import Attributes
from ..model.actor import Actor
from .dungeon import Room, _carve_room, _connect
from ...content.towns import NPCS


def make_npc(npc_id: str) -> Actor:
    ndef = NPCS[npc_id]
    actor = Actor(name=ndef.name, glyph=ndef.glyph,
                  attributes=Attributes({}), is_player=False)
    actor.hostile = False
    actor.npc_id = npc_id
    actor.role = ndef.role
    actor.max_hp = actor.hp = 1000     # townsfolk are not to be trifled with
    return actor


def generate_town(rng: Rng, width: int = 70, height: int = 21) -> Level:
    level = Level(width, height, depth=0)

    # A handful of tidy buildings across the village.
    rooms: list[Room] = []
    for _ in range(40):
        if len(rooms) >= 7:
            break
        w = rng.randint(5, 9)
        h = rng.randint(4, 6)
        x = rng.randint(2, width - w - 2)
        y = rng.randint(2, height - h - 2)
        room = Room(x, y, w, h)
        if any(room.intersects(r, pad=2) for r in rooms):
            continue
        _carve_room(level, room)
        if rooms:
            _connect(level, rng, rooms[-1], room)
        rooms.append(room)

    # The dungeon mouth sits in the last (farthest) building.
    mouth = rooms[-1]
    mx, my = mouth.cx, mouth.cy
    level.set_tile(mx, my, tile.STAIRS_DOWN)
    level.stairs_down = (mx, my)
    level.stairs_up = None

    # Place the townsfolk, one per building near the front of the village.
    placements = ["maroc", "bram", "ferelith", "sarn"]
    for npc_id, room in zip(placements, rooms):
        npc = make_npc(npc_id)
        px, py = _free_floor(level, room, rng)
        npc.x, npc.y = px, py
        level.add_actor(npc)

    level.rooms = rooms
    level.is_town = True
    return level


def _free_floor(level: Level, room: Room, rng: Rng) -> tuple:
    for _ in range(40):
        x, y = room.random_floor(rng)
        if level.tile(x, y) is tile.FLOOR and level.actor_at(x, y) is None:
            return x, y
    return room.cx, room.cy
