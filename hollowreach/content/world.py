"""The world of *Hollowreach* — original setting and lore.

This module is the single source of truth for the game's identity and
every proper noun.  It deliberately contains **no** third-party IP: the
mechanics are drawn from the classic roguelike tradition, but the world,
names, factions and story below are original to this project.  Rename the
game or reskin the setting by editing this one file.

Design note: the mechanics reference in ``docs/DESIGN_MECHANICS.md`` uses
another roguelike's terminology for the *systems*; none of that game's
named content ships here — this file is what the player actually sees.
"""

from __future__ import annotations

# -- identity ---------------------------------------------------------------
GAME_TITLE = "Hollowreach"
GAME_SLUG = "hollowreach"
TAGLINE = "Descend into the Hollow. Seal the rift — or be unmade by it."
VERSION_NAME = "Prologue"

# -- premise ----------------------------------------------------------------
# The afflicted region (a mountain-ringed valley the hero descends into).
REGION = "the Hollowreach"
# The tear in the world through which corruption pours.
RIFT = "the Sundered Gate"
# The spreading corruption / mutation force ("blight").
BLIGHT = "the Hollowing"
BLIGHT_ADJECTIVE = "hollowed"
# The dark power behind the rift (final antagonist).
DARK_POWER = "Vurgast the Unmade"
# The sage who found the rift and could not close it.
SAGE = "Sarn the Lorekeeper"

# -- key places -------------------------------------------------------------
START_VILLAGE = "Hearthvale"       # peaceful starting hub
MAIN_HUB = "Stoneholt"             # mid-game dwarven hold
DUNGEON_SPINE = "the Sundered Depths"   # the deep dungeon to the rift

# -- the descent objective --------------------------------------------------
# The bottom of the Sundered Depths, where the Gate and its guardian wait.
BOTTOM_DEPTH = 15
BOSS_ID = "vurgast"          # Vurgast the Unmade
BOSS_NAME = "Vurgast the Unmade"

# -- the three paths (alignment flavour over the lawful/neutral/chaotic keys)
ALIGNMENT_LABELS = {
    "lawful": "the Warden's Path",     # order, protection
    "neutral": "the Keeper's Path",    # balance
    "chaotic": "the Hollow's Path",    # embracing corruption
}

# -- opening narration shown when a new run begins --------------------------
def opening_lines(hero_name: str) -> list[str]:
    return [
        f"Welcome to {REGION}, {hero_name}.",
        f"{SAGE} found {RIFT} open and could not close it; {BLIGHT} now "
        f"seeps into the world.",
        f"Descend into {DUNGEON_SPINE}, reach the Gate, and seal it — "
        f"before the Hollowing claims you too.",
    ]


def death_epitaph(hero_name: str, depth: int) -> list[str]:
    return [
        f"{hero_name} fell in {DUNGEON_SPINE}, at depth {depth}.",
        f"{REGION} waits still for one who can close {RIFT}.",
    ]


def gate_arrival_lines() -> list[str]:
    return [
        f"You descend into the deepest dark and there it stands: {RIFT}, "
        f"a wound in the world weeping {BLIGHT}.",
        f"{BOSS_NAME} uncoils before it. \"Turn back,\" it grinds. "
        f"\"All roads end in the Hollow.\"",
    ]


def boss_slain_lines() -> list[str]:
    return [
        f"{BOSS_NAME} collapses into formless Hollow and is gone.",
        f"{RIFT} stands unguarded. Step to it and seal the wound.",
    ]


def gate_blocked_line() -> str:
    return f"The Gate will not close while {BOSS_NAME} still stands."


def victory_lines(hero_name: str) -> list[str]:
    return [
        f"You press your will into {RIFT}, and the wound draws shut.",
        f"The Hollowing recedes from {REGION}. The long dark eases.",
        f"{hero_name}, you have sealed the Sundered Gate. "
        f"The Hollowreach is saved.",
        "*** YOU WIN ***",
    ]
