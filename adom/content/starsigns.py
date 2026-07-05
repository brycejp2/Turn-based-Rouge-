"""Star signs (design plan §5.4).

One sign per Ancardian month; the game begins in the month of the
Unicorn (§4.2).  Effects are modelled as a flat ``effects`` dict the
character builder folds in at creation — attribute mods, speed, a
corruption-rate modifier, free talents, fire immunity, etc.
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
    "raven": StarSignDef("raven", 1, "Raven",
                         {"speed": 10, "Pe": 2},
                         "faster; stronger companions; hard to trick"),
    "book": StarSignDef("book", 2, "Book",
                        {"Le": 3, "alignment": 500, "free_skill_per_level": 1},
                        "better spell learning; lawful lean"),
    "wand": StarSignDef("wand", 3, "Wand",
                        {"neutral_spell_cost_mult": 0.9},
                        "neutral-magic lean"),
    "unicorn": StarSignDef("unicorn", 4, "Unicorn",
                           {"corruption_mult": 0.81},
                           "grace/purity; corruption modifier"),
    "salamander": StarSignDef("salamander", 5, "Salamander",
                              {"fire_immunity": True, "cold_dmg_mult": 1.5,
                               "fire_spell_cost_mult": 0.8},
                              "fire immunity, extra cold damage"),
    "dragon": StarSignDef("dragon", 6, "Dragon",
                          {"combat_spell_cost_mult": 0.9},
                          "combat-magic lean"),
    "sword": StarSignDef("sword", 7, "Sword",
                         {"melee_mark_cost_mult": 0.8},
                         "cheaper melee weapon marks"),
    "falcon": StarSignDef("falcon", 8, "Falcon",
                          {"free_talent": 1, "grant_skill": "Survival"},
                          "grants Survival + a free talent"),
    "cup": StarSignDef("cup", 9, "Cup", {"skill_boost": True},
                       "general skill boosts"),
    "candle": StarSignDef("candle", 10, "Candle",
                          {"hp_regen_mult": 0.75, "free_talent": 1},
                          "strong HP regen; beginner-recommended"),
    "wolf": StarSignDef("wolf", 11, "Wolf", {"Wi": 2}, "+Willpower lean"),
    "tree": StarSignDef("tree", 12, "Tree",
                        {"pv": 1, "To": 2, "Wi": 4},
                        "+PV, +To, +Wi — early-survival powerhouse"),
}

DEFAULT_STAR_SIGN = "candle"
MONTH_NAMES = [STAR_SIGNS[k].name for k in
               ["raven", "book", "wand", "unicorn", "salamander", "dragon",
                "sword", "falcon", "cup", "candle", "wolf", "tree"]]
