"""Constellations / birth-omens (original content).

Twelve constellations, one per month of the Hollowreach calendar; a hero
is born under one and gains its omen.  The *mechanic* (a birth sign that
grants small permanent bonuses) is a genre staple; the constellations,
names and framing here are original to this game.

Effects are a flat dict the character builder folds in at creation —
attribute mods, speed, a blight-rate modifier, free talents, fire
immunity, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StarSignDef:
    id: str
    month: int
    name: str
    effects: dict = field(default_factory=dict)
    note: str = ""


STAR_SIGNS = {
    "hawk": StarSignDef("hawk", 1, "The Hawk",
                        {"speed": 10, "Pe": 2},
                        "swift; keen-eyed; hard to ambush"),
    "tome": StarSignDef("tome", 2, "The Tome",
                        {"Le": 3, "alignment": 500, "free_skill_per_level": 1},
                        "learned; an extra skill each level"),
    "sigil": StarSignDef("sigil", 3, "The Sigil",
                         {"neutral_spell_cost_mult": 0.9},
                         "attuned to balanced magic"),
    "warden": StarSignDef("warden", 4, "The Warden",
                          {"blight_mult": 0.81},
                          "resists the Hollowing"),
    "ember": StarSignDef("ember", 5, "The Ember",
                         {"fire_immunity": True, "cold_dmg_mult": 1.5,
                          "fire_spell_cost_mult": 0.8},
                         "immune to fire; frail to cold"),
    "wyrm": StarSignDef("wyrm", 6, "The Wyrm",
                        {"combat_spell_cost_mult": 0.9},
                        "cheaper combat magic; a warlike streak"),
    "blade": StarSignDef("blade", 7, "The Blade",
                         {"melee_mark_cost_mult": 0.8},
                         "masters weapons faster"),
    "gale": StarSignDef("gale", 8, "The Gale",
                        {"free_talent": 1, "grant_skill": "Survival"},
                        "grants Survival and a free talent"),
    "chalice": StarSignDef("chalice", 9, "The Chalice",
                           {"skill_boost": True},
                           "broadly gifted across skills"),
    "beacon": StarSignDef("beacon", 10, "The Beacon",
                          {"hp_regen_mult": 0.75, "free_talent": 1},
                          "strong regeneration; a good first omen"),
    "fang": StarSignDef("fang", 11, "The Fang",
                        {"Wi": 2}, "iron will"),
    "bastion": StarSignDef("bastion", 12, "The Bastion",
                           {"pv": 1, "To": 2, "Wi": 4},
                           "tough and resolute — a survivor's omen"),
}

DEFAULT_STAR_SIGN = "beacon"

# Calendar months are named for the constellations.
MONTH_NAMES = [STAR_SIGNS[k].name.replace("The ", "") for k in
               ["hawk", "tome", "sigil", "warden", "ember", "wyrm",
                "blade", "gale", "chalice", "beacon", "fang", "bastion"]]

# A new run begins in the month of the Warden (when the Gate was opened).
STARTING_MONTH = 4
