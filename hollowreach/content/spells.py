"""Spell definitions (original content, design ref §8).

Spells are fuelled by Power Points (PP, driven by Mana + Willpower).  Each
spell is learned from a spellbook, which grants a number of **castings**;
casting spends PP and one casting, and repeated casting raises the
spell's **power** (effectiveness).  Kinds:

* ``bolt``   — fires in a chosen direction, striking every foe in the line
  until it meets a wall.
* ``ball``   — flies to the first obstacle and bursts, hitting an area
  whose radius grows with Willpower.
* ``heal``   — restores the caster's own hit points.
* ``light``  — reveals the surroundings.
* ``teleport`` — blinks the caster elsewhere on the level.

Elements (fire / cold / shock / light / force) interact with monster
types via the resistance table in ``core/rules/magic.py``; ``force`` is
the reliable element nothing resists.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpellDef:
    id: str
    name: str
    tradition: str      # "arcane" | "clerical" | "any"
    kind: str           # bolt | ball | heal | light | teleport
    element: str        # force | fire | cold | shock | light | none
    pp: int
    dice: str = ""      # damage / heal dice
    reach: int = 0      # bolt/ball travel range in tiles
    radius_base: int = 0
    note: str = ""


SPELLS = {
    "wisp_light": SpellDef(
        "wisp_light", "Wisp Light", "any", "light", "none", 3,
        note="a drifting mote lights your surroundings"),
    "mind_dart": SpellDef(
        "mind_dart", "Mind Dart", "arcane", "bolt", "force", 6, "2d4", reach=8,
        note="a dart of raw force; nothing resists it"),
    "cinderbolt": SpellDef(
        "cinderbolt", "Cinderbolt", "arcane", "bolt", "fire", 9, "3d5", reach=8,
        note="a lance of flame"),
    "rimebolt": SpellDef(
        "rimebolt", "Rimebolt", "arcane", "bolt", "cold", 11, "3d6", reach=8,
        note="a spike of killing cold"),
    "stormbolt": SpellDef(
        "stormbolt", "Stormbolt", "arcane", "bolt", "shock", 11, "3d5", reach=8,
        note="a crackling arc"),
    "emberburst": SpellDef(
        "emberburst", "Emberburst", "arcane", "ball", "fire", 14, "3d4",
        reach=6, radius_base=1, note="a bursting bloom of fire"),
    "blink": SpellDef(
        "blink", "Blink", "any", "teleport", "none", 8,
        note="a short, disorienting jump"),
    "mend_wounds": SpellDef(
        "mend_wounds", "Mend Wounds", "clerical", "heal", "none", 6, "2d8",
        note="knits flesh and closes wounds"),
    "greater_mending": SpellDef(
        "greater_mending", "Greater Mending", "clerical", "heal", "none", 12,
        "4d8", note="a surge of restoring grace"),
    "smite": SpellDef(
        "smite", "Smite", "clerical", "bolt", "light", 9, "3d5", reach=7,
        note="holy light; it sears the hollowed and undead"),
}

# Spells a class knows at creation (and gets spellbooks for).
STARTING_SPELLS = {
    "wizard": ["mind_dart", "cinderbolt", "wisp_light"],
    "priest": ["mend_wounds", "smite", "wisp_light"],
    "healer": ["mend_wounds"],
}
