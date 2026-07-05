"""Character assembly and monster instantiation (design plan §5, §6, §12).

``build_player`` folds a race + class + star sign + rolled attributes into
a ready-to-play :class:`Actor`, applying:

* race attribute modifiers and potentials (§5.2),
* star-sign effects incl. the Raven speed bonus (§5.4),
* Toughness-driven starting HP and Mana-driven starting PP (§5.1),
* class starting skills and level-1 combat contributions (§5.3),
* the monster-memory record store (§3.4).

``make_monster`` instantiates a monster from a :class:`MonsterDef`,
scaling DV with dungeon level per §12.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .actor import Actor
from .attributes import Attributes, ATTRIBUTE_KEYS
from ..engine.rng import Rng
from ...content.races import RACES, RaceDef
from ...content.classes import CLASSES, ClassDef
from ...content.starsigns import STAR_SIGNS, StarSignDef
from ...content.monsters import MonsterDef


@dataclass
class MemoryRecord:
    """Per-character knowledge accumulated about a monster type (§3.4)."""
    monster_id: str
    kills: int = 0
    seen: int = 0
    max_hp_observed: int = 0
    abilities_seen: set = field(default_factory=set)


class PlayerCharacter:
    """Wraps an :class:`Actor` with the run-level progression state."""

    def __init__(self, actor: Actor, race: RaceDef, cls: ClassDef,
                 sign: StarSignDef, gender: str):
        self.actor = actor
        self.race = race
        self.cls = cls
        self.sign = sign
        self.gender = gender
        self.xp = 0
        self.skills: dict[str, int] = {}
        self.piety = cls.start_piety
        self.alignment = race.start_alignment
        self.monster_memory: dict[str, MemoryRecord] = {}
        self.turns = 0

    # -- experience & leveling (§6.1) ------------------------------------
    def xp_to_next_level(self) -> int:
        base = self.actor.char_level * self.actor.char_level * 50
        return int(base * self.race.xp_mult * self.cls_xp_bias())

    def cls_xp_bias(self) -> float:
        return 1.0

    def award_xp(self, amount: int) -> bool:
        """Add XP (with the Learning bonus) and level up if earned."""
        le = self.actor.attributes.Le
        amount = int(amount * (1 + le / 1000.0))
        self.xp += amount
        leveled = False
        while self.xp >= self.xp_to_next_level():
            self._level_up()
            leveled = True
        return leveled

    def _level_up(self) -> None:
        a = self.actor
        a.char_level += 1
        # HP/PP gains driven by class dice plus To/Ma (§6.1).
        hp_gain = _rng.roll(self.cls.hp_per_level) + max(0, (a.attributes.To - 10) // 4)
        pp_gain = _rng.roll(self.cls.pp_per_level) + max(0, (a.attributes.Ma - 10) // 4)
        a.max_hp += hp_gain
        a.hp += hp_gain
        a.max_pp += pp_gain
        a.pp += pp_gain

    def note_kill(self, monster_id: str) -> None:
        rec = self.monster_memory.setdefault(monster_id, MemoryRecord(monster_id))
        rec.kills += 1


# A module-level RNG only for level-up dice; the game passes a seeded one
# into building.  Reassigned by build_player so runs stay deterministic.
_rng = Rng(0)


def build_player(name: str, race_id: str, class_id: str, sign_id: str,
                 gender: str, base_attrs: dict, rng: Rng) -> PlayerCharacter:
    global _rng
    _rng = rng
    race = RACES[race_id]
    cls = CLASSES[class_id]
    sign = STAR_SIGNS[sign_id]

    # Start from rolled/point-buy bases, apply race + star-sign attr mods.
    values = dict(base_attrs)
    potentials = {}
    for key in ATTRIBUTE_KEYS:
        base = values.get(key, 10)
        base += race.attr_mods.get(key, 0)
        base += sign.effects.get(key, 0)
        if gender == "male" and key == "St":
            base += 1
        if gender == "female" and key == "Dx":
            base += 1
        values[key] = max(1, base)
        potentials[key] = max(values[key], values[key] + race.attr_pot.get(key, 0))

    attrs = Attributes(values, potentials)

    actor = Actor(name=name, glyph="@", attributes=attrs, is_player=True)
    actor.base_speed = 100 + sign.effects.get("speed", 0)

    # Starting HP/PP: Toughness drives HP, Mana drives PP (§5.1).
    to = attrs.To
    ma = attrs.Ma
    actor.max_hp = actor.hp = max(1, to + rng.rnd(6) + 4)
    actor.max_pp = actor.pp = max(0, (ma - 6) + rng.rnd(4))

    # Star-sign PV / Dwarf mithril-skin eligibility.
    actor.armor_pv += sign.effects.get("pv", 0)
    if "mithril_skin_eligible" in race.abilities:
        actor.mithril_skin = 3

    pc = PlayerCharacter(actor, race, cls, sign, gender)

    # Assemble starting skills: universal + race + class + sign grants (§5.2).
    skill_names = ["Climbing", "First Aid", "Haggling", "Listening"]
    if "illiterate" not in race.abilities and attrs.Le >= 10:
        skill_names.append("Literacy")
    skill_names += list(race.start_skills) + list(cls.start_skills)
    if "grant_skill" in sign.effects:
        skill_names.append(sign.effects["grant_skill"])
    for skill in skill_names:
        pc.skills.setdefault(skill, _starting_skill_value(skill, attrs, rng))

    # Level-1 class combat contributions.
    if cls.archetype == "unarmed":
        actor.unarmed_dv_per_level = 2 / 3   # Monk (§7.2)
    if "Dodge" in pc.skills:
        actor.dodge_dv += 1
    if "Alertness" in pc.skills:
        actor.alertness_dv += 1

    return pc


def _starting_skill_value(skill: str, attrs: Attributes, rng: Rng) -> int:
    """Representative starting-skill formulas (§6.2)."""
    formulas = {
        "Climbing": lambda: rng.rnd(attrs.Dx) + rng.rnd(10) + 20,
        "First Aid": lambda: rng.rnd(attrs.Le) + rng.rnd(10) + 15,
        "Haggling": lambda: rng.rnd(attrs.Ch) + rng.rnd(10) + 15,
        "Listening": lambda: rng.rnd(attrs.Pe) + rng.rnd(10) + 20,
        "Literacy": lambda: min(100, attrs.Le * 4),
        "Healing": lambda: rng.rnd(30) + 50,
        "Herbalism": lambda: rng.rnd(40) + 40,
    }
    return min(100, formulas.get(skill, lambda: rng.rnd(20) + 20)())


def make_monster(mdef: MonsterDef, rng: Rng, depth: int = 1,
                 level_bonus: int = 0) -> Actor:
    """Instantiate a monster; DV scales with dungeon level (§12.1)."""
    # Monsters use a compact attribute stand-in derived from their stats.
    attrs = Attributes({"Dx": 10, "To": 10, "St": 12})
    hp = max(1, rng.roll(mdef.hp_dice) + level_bonus * 2)
    actor = Actor(
        name=mdef.name, glyph=mdef.glyph, attributes=attrs,
        is_player=False, monster_id=mdef.id,
    )
    actor.base_speed = mdef.speed
    actor.max_hp = actor.hp = hp
    actor.char_level = 1 + level_bonus
    # DV ~= table value + 0.7*level (§12.1); PV straight from the def.
    actor.armor_dv = int(mdef.dv + 0.7 * (depth + level_bonus)) - \
        ((attrs.Dx - 12) // 2 + (attrs.Dx - 9) // 2)
    actor.armor_pv = mdef.pv
    actor.weapon_dice = mdef.attack
    actor.hostile = True
    return actor
