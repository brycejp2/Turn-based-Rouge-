"""Race definitions (design plan §5.2).

A representative subset of the 12 races, enough to exercise the
character-model machinery: XP multiplier, attribute modifiers &
potentials, lifespan, regen rates, starting alignment and signature
abilities.  The full roster is ported the same way from the wiki
**Races** pages (§18); each entry is pure data so adding the rest is a
table edit, not a code change.

``attr_mods`` are applied to the point-buy/rolled base values; ``attr_pot``
are added to potentials.  ``hp_regen``/``pp_regen`` are turns-per-point
(lower = faster).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RaceDef:
    id: str
    name: str
    attr_mods: dict          # {attr_key: delta}
    attr_pot: dict           # {attr_key: potential delta}
    xp_mult: float           # higher = slower leveling (§5.2)
    age_range: tuple         # (min, max) starting age
    hp_regen: int            # turns per HP recovered
    pp_regen: int            # turns per PP recovered
    start_alignment: str     # "lawful" | "neutral" | "chaotic"
    abilities: tuple = ()    # signature traits
    start_skills: tuple = ()


RACES = {
    "human": RaceDef(
        id="human", name="Human",
        attr_mods={}, attr_pot={},
        xp_mult=0.86, age_range=(16, 30), hp_regen=30, pp_regen=30,
        start_alignment="neutral",
        abilities=("jack_of_all_trades", "good_shop_relations"),
    ),
    "troll": RaceDef(
        id="troll", name="Troll",
        attr_mods={"St": 12, "To": 10, "Le": -8, "Ma": -8, "Wi": -6, "Dx": -4},
        attr_pot={"St": 15, "To": 12, "Le": -10, "Ma": -10},
        xp_mult=2.5, age_range=(14, 20), hp_regen=12, pp_regen=90,
        start_alignment="chaotic",
        abilities=("fastest_hp_regen", "illiterate", "two_handed_start"),
    ),
    "high_elf": RaceDef(
        id="high_elf", name="High Elf",
        attr_mods={"Le": 6, "Ma": 6, "Dx": 4, "To": -4, "St": -2},
        attr_pot={"Le": 8, "Ma": 8, "Dx": 6, "To": -6},
        xp_mult=1.0, age_range=(60, 130), hp_regen=45, pp_regen=18,
        start_alignment="lawful",
        abilities=("fast_pp_regen", "elven_gear"),
    ),
    "dwarf": RaceDef(
        id="dwarf", name="Dwarf",
        attr_mods={"To": 6, "St": 4, "Dx": -4, "Le": -2},
        attr_pot={"To": 8, "St": 6, "Dx": -6},
        xp_mult=1.0, age_range=(40, 70), hp_regen=30, pp_regen=30,
        start_alignment="lawful",
        abilities=("mithril_skin_eligible", "find_secret_doors", "gold_piety"),
    ),
    "gnome": RaceDef(
        id="gnome", name="Gnome",
        attr_mods={"Dx": 4, "Le": 3, "To": 2, "St": -2},
        attr_pot={"Dx": 6, "Le": 4},
        xp_mult=0.75, age_range=(40, 80), hp_regen=30, pp_regen=28,
        start_alignment="neutral",
        abilities=("fast_crossbow_marks",),
    ),
    "dark_elf": RaceDef(
        id="dark_elf", name="Dark Elf",
        attr_mods={"Dx": 6, "Ma": 4, "To": -4, "Ap": -4},
        attr_pot={"Dx": 8, "Ma": 6, "To": -6},
        xp_mult=1.0, age_range=(50, 110), hp_regen=45, pp_regen=18,
        start_alignment="chaotic",
        abilities=("fast_pp_regen", "spider_affinity", "hated_by_dwarves"),
        start_skills=("Alertness",),
    ),
    "drakeling": RaceDef(
        id="drakeling", name="Drakeling",
        attr_mods={"To": 5, "St": 2, "Ap": -3},
        attr_pot={"To": 6},
        xp_mult=1.0, age_range=(12, 25), hp_regen=28, pp_regen=30,
        start_alignment="neutral",
        abilities=("acid_spit", "heat_vulnerable"),
    ),
}

DEFAULT_RACE = "human"
