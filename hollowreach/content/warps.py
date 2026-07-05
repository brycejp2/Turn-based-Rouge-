"""Warps — the mutations inflicted by the Hollowing (original content).

As a hero soaks up **Blight** in the deep places, the Hollowing *warps*
them: body and mind twist, granting jagged gifts alongside real costs.
Each Warp is pure data — attribute shifts, flat DV/PV, an unarmed-damage
bump, and optional special tags the Blight clock wires into the engine.

Warps are drawn in a per-run shuffled order.  Accumulate enough and the
hero stops being a hero at all (see ``core/rules/blight.py``).  This is
original content; the *concept* of a creeping mutation clock is a genre
mechanic, the Warps and framing here are ours.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WarpDef:
    id: str
    name: str
    attr_mods: dict = field(default_factory=dict)
    dv: int = 0
    pv: int = 0
    unarmed_dmg: int = 0
    specials: tuple = ()
    note: str = ""


WARPS = {
    "ashen_skin": WarpDef(
        "ashen_skin", "ashen skin", {"Dx": -2, "Ap": -3}, pv=4,
        note="grey, bark-hard hide"),
    "hollow_eyes": WarpDef(
        "hollow_eyes", "hollow eyes", {"Pe": 6, "Ap": -4},
        note="lidless, all-seeing sockets"),
    "gaunt_frame": WarpDef(
        "gaunt_frame", "gaunt frame", {"To": -3}, dv=4,
        note="wretchedly thin and hard to hit"),
    "cinderblood": WarpDef(
        "cinderblood", "cinderblood", {"St": 3, "Wi": -1, "Ap": -2},
        note="veins that run hot as coals"),
    "knotted_hide": WarpDef(
        "knotted_hide", "knotted hide", {"Dx": -2}, pv=3,
        note="rope-like ridges of scar"),
    "barbed_flesh": WarpDef(
        "barbed_flesh", "barbed flesh", {"Dx": -2, "Ap": -3}, unarmed_dmg=4,
        note="skin bristling with bone spurs"),
    "cloven_gait": WarpDef(
        "cloven_gait", "cloven gait", {"St": 2, "Dx": -4},
        note="splayed, hoof-like feet"),
    "leaden_bones": WarpDef(
        "leaden_bones", "leaden bones", {"St": 4, "To": 2, "Dx": -4},
        note="dense, ponderous skeleton"),
    "wispform": WarpDef(
        "wispform", "wispform", {"Dx": 4, "St": -4, "To": -4}, dv=2,
        note="half-real, drifting flesh"),
    "fevered_mind": WarpDef(
        "fevered_mind", "fevered mind", {"Ma": 4, "Wi": -2},
        note="a mind alight with borrowed power"),
    "voidsight": WarpDef(
        "voidsight", "voidsight", {"Ap": -2}, specials=("night_vision",),
        note="eyes that drink the dark"),
    "chittering_voice": WarpDef(
        "chittering_voice", "chittering voice", {"Ch": -4, "Wi": 2},
        note="a dozen whispering throats"),
}

# The order Warps arrive is shuffled per run by the Blight clock.
WARP_IDS = list(WARPS.keys())

# Blight points per Warp, and the count at which the hero is consumed.
BLIGHT_PER_WARP = 100
MAX_WARPS = len(WARPS)   # the threshold past the last Warp = game over
