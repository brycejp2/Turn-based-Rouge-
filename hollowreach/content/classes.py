"""Class definitions (design plan §5.3).

A representative subset of the 22 classes.  Each carries the fields the
plan calls out: starting skills, starting piety (Druid/Priest 1500,
Paladin 1200, others 200), caster type, to-hit progression, weapon-mark
rate, and the seven **class powers** unlocked at levels 6/12/18/25/32/40/50.

Class powers are modelled as data (``ClassPower``) — ``kind`` selects how
the rules engine applies the ``payload`` (one-time bonus, per-level
recurring, permanent passive, or an activatable ability).  Only a couple
of powers per class are filled in here to exercise the system; the rest
are ported from the mechanics reference (docs/DESIGN_MECHANICS.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field

CLASS_POWER_LEVELS = (6, 12, 18, 25, 32, 40, 50)


@dataclass(frozen=True)
class ClassPower:
    level: int
    kind: str      # "one_time" | "per_level" | "passive" | "activated"
    name: str
    payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ClassDef:
    id: str
    name: str
    start_piety: int
    caster_type: str          # "arcane" | "clerical" | "mind" | "none"
    melee_to_hit_per_level: float   # to-hit progression slope
    weapon_mark_rate: float         # 1.0 = normal; <1 = faster marks
    hp_per_level: str               # dice added on level-up (To also drives it)
    pp_per_level: str
    start_skills: tuple = ()
    class_powers: tuple = ()
    archetype: str = "melee"


CLASSES = {
    "fighter": ClassDef(
        id="fighter", name="Fighter", start_piety=200, caster_type="none",
        melee_to_hit_per_level=1.0, weapon_mark_rate=0.9,
        hp_per_level="1d6", pp_per_level="1d2",
        start_skills=("Athletics", "Dodge", "Find Weakness", "Tactics"),
        archetype="melee",
        class_powers=(
            ClassPower(6, "passive", "Tension", {"to_hit": 3}),
            ClassPower(12, "per_level", "Melee bonus", {"melee_dmg": 1}),
        ),
    ),
    "barbarian": ClassDef(
        id="barbarian", name="Barbarian", start_piety=200, caster_type="none",
        melee_to_hit_per_level=1.1, weapon_mark_rate=0.8,
        hp_per_level="1d8", pp_per_level="1d1",
        start_skills=("Athletics", "Climbing", "Survival", "Two-Weapon Combat"),
        archetype="melee",
        class_powers=(
            ClassPower(6, "passive", "Speed of the wild", {"speed": 10}),
            ClassPower(12, "passive", "Damage bonus vs many foes", {}),
        ),
    ),
    "wizard": ClassDef(
        id="wizard", name="Wizard", start_piety=200, caster_type="arcane",
        melee_to_hit_per_level=0.4, weapon_mark_rate=1.3,
        hp_per_level="1d3", pp_per_level="1d6",
        start_skills=("Concentration", "Literacy", "Alchemy", "Find Weakness"),
        archetype="arcane",
        class_powers=(
            ClassPower(6, "passive", "Cheaper arcane spells", {"spell_cost_mult": 0.9}),
        ),
    ),
    "priest": ClassDef(
        id="priest", name="Priest", start_piety=1500, caster_type="clerical",
        melee_to_hit_per_level=0.6, weapon_mark_rate=1.1,
        hp_per_level="1d4", pp_per_level="1d5",
        start_skills=("Concentration", "Literacy", "First Aid", "Healing"),
        archetype="clerical",
        class_powers=(
            ClassPower(6, "passive", "Detect Item Status", {"auto_buc": True}),
        ),
    ),
    "healer": ClassDef(
        id="healer", name="Healer", start_piety=200, caster_type="none",
        melee_to_hit_per_level=0.7, weapon_mark_rate=1.1,
        hp_per_level="1d5", pp_per_level="1d4",
        start_skills=("Healing", "Herbalism", "First Aid", "Literacy", "Concentration"),
        archetype="melee",
        class_powers=(
            ClassPower(6, "passive", "Regeneration x2", {"hp_regen_mult": 0.5}),
            ClassPower(12, "passive", "Regeneration x3", {"hp_regen_mult": 0.33}),
        ),
    ),
    "monk": ClassDef(
        id="monk", name="Monk", start_piety=200, caster_type="none",
        melee_to_hit_per_level=0.9, weapon_mark_rate=1.0,
        hp_per_level="1d5", pp_per_level="1d3",
        start_skills=("Athletics", "Dodge", "Stealth", "Tactics", "Climbing"),
        archetype="unarmed",
        class_powers=(
            ClassPower(6, "activated", "Circular kick", {"ep_cost": 2500}),
        ),
    ),
}

DEFAULT_CLASS = "fighter"
