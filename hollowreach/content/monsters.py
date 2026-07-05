"""Monster definitions (design plan §12).

A small starter bestiary keyed to dungeon level (DL) for spawn tables
(§4.3, §12.5).  Each entry carries HP dice, DV/PV, speed, attack dice,
XP value, alignment, size, type tags and a corpse effect.  Breeders and
uniques are flagged.  The full ~600-monster roster is ported the same
way from the mechanics reference (docs/DESIGN_MECHANICS.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MonsterDef:
    id: str
    name: str
    glyph: str
    hp_dice: str
    dv: int
    pv: int
    speed: int
    attack: str          # damage dice for its melee attack
    xp_value: int
    alignment: str
    size: str            # tiny | small | medium | large
    types: tuple
    spawn_dl: int        # earliest DL this appears
    corpse_effect: str = ""
    breeder: bool = False
    summoner: bool = False
    unique: bool = False
    abilities: tuple = ()
    kills_to_level: int = 20   # uberjackal effect (§12.4)


MONSTERS = {
    "rat": MonsterDef(
        "rat", "rat", "r", "1d3", dv=2, pv=0, speed=100, attack="1d3",
        xp_value=2, alignment="neutral", size="tiny", types=("animal",),
        spawn_dl=1, breeder=True, kills_to_level=40,
    ),
    "giant_rat": MonsterDef(
        "giant_rat", "giant rat", "r", "1d4", dv=3, pv=0, speed=110, attack="1d4",
        xp_value=3, alignment="neutral", size="small", types=("animal",),
        spawn_dl=1, breeder=True, kills_to_level=40,
    ),
    "kobold": MonsterDef(
        "kobold", "kobold", "k", "1d6", dv=4, pv=1, speed=100, attack="1d5",
        xp_value=4, alignment="chaotic", size="small", types=("humanoid",),
        spawn_dl=1,
    ),
    "goblin": MonsterDef(
        "goblin", "goblin", "g", "1d6+2", dv=5, pv=1, speed=100, attack="1d6",
        xp_value=5, alignment="chaotic", size="small", types=("humanoid",),
        spawn_dl=1,
    ),
    "jackal": MonsterDef(
        "jackal", "jackal", "d", "1d4", dv=5, pv=0, speed=120, attack="1d4",
        xp_value=3, alignment="chaotic", size="small", types=("animal",),
        spawn_dl=1, kills_to_level=30,
    ),
    "giant_bat": MonsterDef(
        "giant_bat", "giant bat", "B", "1d5", dv=8, pv=0, speed=140, attack="1d4",
        xp_value=5, alignment="neutral", size="small", types=("animal",),
        spawn_dl=2,
    ),
    "orc": MonsterDef(
        "orc", "orc", "o", "2d6", dv=5, pv=2, speed=100, attack="1d8",
        xp_value=9, alignment="chaotic", size="medium", types=("humanoid",),
        spawn_dl=3,
    ),
    "wolf": MonsterDef(
        "wolf", "wolf", "d", "2d5", dv=7, pv=1, speed=130, attack="1d6",
        xp_value=8, alignment="neutral", size="medium", types=("animal",),
        spawn_dl=3,
    ),
    "giant_frog": MonsterDef(
        "giant_frog", "giant frog", "F", "2d4", dv=4, pv=1, speed=90, attack="1d6",
        xp_value=6, alignment="neutral", size="medium", types=("animal",),
        spawn_dl=2,
    ),
    "gnoll": MonsterDef(
        "gnoll", "gnoll", "g", "2d7", dv=6, pv=3, speed=100, attack="1d10",
        xp_value=12, alignment="chaotic", size="medium", types=("humanoid",),
        spawn_dl=4,
    ),
}


def spawn_table_for_dl(dl: int) -> list:
    """Monsters eligible at dungeon level ``dl`` with rough weights."""
    table = []
    for mon in MONSTERS.values():
        if mon.unique:
            continue
        if mon.spawn_dl <= dl:
            # Weaker (lower-DL) monsters thin out as you descend.
            weight = max(1, 8 - (dl - mon.spawn_dl))
            table.append((mon.id, weight))
    return table
