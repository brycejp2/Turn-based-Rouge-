"""Character assembly and monster instantiation (design plan §5, §6, §12).

``build_player`` folds a race + class + star sign + rolled attributes into
a ready-to-play :class:`Actor`, applying:

* race attribute modifiers and potentials (§5.2),
* star-sign effects incl. the Hawk speed bonus,
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
from .inventory import (
    Inventory, Equipment, carrying_capacity, encumbrance_penalty,
)
from ..generation.loot import make_item
from ..rules.proficiency import Proficiencies
from ..rules.classpowers import apply_level_powers
from ..rules.skills import apply_skill_bonuses, gain_level_skills
from ...content.spells import STARTING_SPELLS
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
        self.inventory = Inventory()
        self.equipment = Equipment()
        # The Hollowing (see core/rules/blight.py).
        self.blight_points: float = 0.0
        self.warps: list[str] = []
        # Build systems (skills, proficiencies, class powers, regen).
        self.proficiencies = Proficiencies()
        self.granted_powers: set = set()
        self.regen_mult: float = 1.0
        self.pp_regen_mult: float = 1.0
        self.hp_regen_counter: float = 0.0
        self.pp_regen_counter: float = 0.0
        self.auto_buc: bool = False
        self.spell_cost_mult: float = 1.0
        # Known spells: id -> {"castings", "power", "casts"} (see §8).
        self.spells: dict[str, dict] = {}

    def learn_spell(self, spell_id: str, castings: int) -> bool:
        """Learn or refresh a spell from a book. Returns True if newly learned."""
        state = self.spells.get(spell_id)
        if state is None:
            base_power = max(1, 1 + self.actor.attributes.Le // 10)
            self.spells[spell_id] = {"castings": castings, "power": base_power,
                                     "casts": 0}
            return True
        state["castings"] += castings
        return False

    def refresh_combat(self) -> None:
        """Re-fold equipment, proficiency and skills into the actor's stats."""
        self.equipment.recompute(self.actor)
        self.proficiencies.apply_to_actor(self)
        apply_skill_bonuses(self)

    def update_encumbrance(self) -> None:
        """Recompute the carry-weight speed penalty (§5.1)."""
        capacity = carrying_capacity(self.actor.attributes.St)
        self.actor.encumbrance_penalty = encumbrance_penalty(
            self.inventory.total_weight(), capacity)

    # -- experience & leveling (§6.1) ------------------------------------
    def xp_to_next_level(self) -> int:
        # Tuned against full-run simulations: a hero who fights on the way
        # down should hit ~L6 by mid-depths and ~L10+ near the bottom.
        lvl = self.actor.char_level
        base = lvl * lvl * 25 + lvl * 25
        return int(base * self.race.xp_mult * self.cls_xp_bias())

    def cls_xp_bias(self) -> float:
        return 1.0

    def award_xp(self, amount: int) -> list:
        """Add XP (with the Learning bonus) and level up if earned.

        Returns a list of level-up / class-power messages (empty if no
        level gained)."""
        le = self.actor.attributes.Le
        amount = int(amount * (1 + le / 1000.0))
        self.xp += amount
        messages: list = []
        while self.xp >= self.xp_to_next_level():
            messages.extend(self._level_up())
        return messages

    def _level_up(self) -> list:
        a = self.actor
        a.char_level += 1
        # HP/PP gains driven by class dice plus To/Ma (§6.1).
        hp_gain = _rng.roll(self.cls.hp_per_level) + max(0, (a.attributes.To - 10) // 4)
        pp_gain = _rng.roll(self.cls.pp_per_level) + max(0, (a.attributes.Ma - 10) // 4)
        a.max_hp += hp_gain
        a.hp += hp_gain
        a.max_pp += pp_gain
        a.pp += pp_gain
        messages = [f"Welcome to level {a.char_level}!"]
        messages.extend(apply_level_powers(self))   # class powers (§5.3)
        gain_level_skills(self, _rng)               # skill increases (§6.2)
        self.refresh_combat()
        return messages

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

    # Casters need a real Mana/Willpower base so PP is usable from level 1.
    if cls.caster_type == "arcane":
        values["Ma"] += 6; values["Wi"] += 2
    elif cls.caster_type == "clerical":
        values["Ma"] += 4; values["Wi"] += 3
    for k in ("Ma", "Wi"):
        potentials[k] = max(potentials[k], values[k])

    attrs = Attributes(values, potentials)

    actor = Actor(name=name, glyph="@", attributes=attrs, is_player=True)
    actor.base_speed = 100 + sign.effects.get("speed", 0)

    # Starting HP/PP: Toughness drives HP, Mana + Willpower drive PP (§5.1).
    to = attrs.To
    ma = attrs.Ma
    actor.max_hp = actor.hp = max(1, to + rng.rnd(6) + 4)
    actor.max_pp = actor.pp = max(0, (ma - 6) + attrs.Wi // 4 + rng.rnd(4))

    # Star-sign PV / Dwarf innate stoneskin eligibility.
    actor.armor_pv += sign.effects.get("pv", 0)
    if "stoneskin_eligible" in race.abilities:
        actor.stoneskin = 3

    pc = PlayerCharacter(actor, race, cls, sign, gender)
    # Omen regeneration bonus (e.g. the Beacon).
    pc.regen_mult = sign.effects.get("hp_regen_mult", 1.0)
    # Casters channel power back faster — without this a wizard casts two
    # spells and then waits out a hundred-turn drought.
    if cls.caster_type == "arcane":
        pc.pp_regen_mult = 0.45
    elif cls.caster_type == "clerical":
        pc.pp_regen_mult = 0.6

    # Assemble starting skills: universal + race + class + sign grants (§5.2).
    skill_names = ["Climbing", "First Aid", "Haggling", "Listening"]
    if "illiterate" not in race.abilities and attrs.Le >= 10:
        skill_names.append("Literacy")
    skill_names += list(race.start_skills) + list(cls.start_skills)
    if "grant_skill" in sign.effects:
        skill_names.append(sign.effects["grant_skill"])
    for skill in skill_names:
        pc.skills.setdefault(skill, _starting_skill_value(skill, attrs, rng))

    # Level-1 unarmed classes scale DV with level (Monk, §7.2).
    if cls.archetype == "unarmed":
        actor.unarmed_dv_per_level = 2 / 3

    _grant_starting_gear(pc, rng)
    pc.refresh_combat()   # fold skills/proficiency/equipment into the actor
    return pc


# Per-class starting kit (weapon + body armour). Unarmed classes skip the
# weapon so their fists stay in play.
_STARTING_KITS = {
    "fighter": ("long_sword", "ring_mail"),
    "barbarian": ("battle_axe", "leather_armor"),
    "wizard": ("dagger", "cloak"),
    "priest": ("mace", "leather_armor"),
    "healer": ("short_sword", "leather_armor"),
    "monk": (None, "cloak"),
}


def _grant_starting_gear(pc: "PlayerCharacter", rng: Rng) -> None:
    weapon_id, armor_id = _STARTING_KITS.get(pc.cls.id, ("short_sword", "leather_armor"))
    for base_id in (weapon_id, armor_id):
        if base_id is None:
            continue
        item = make_item(base_id, rng, buc="uncursed", enchant=0)
        pc.inventory.add(item)
        ok, displaced, _msg = pc.equipment.equip(item)
        if ok:
            pc.inventory.remove(item)
    # A little consumable relief and food.
    pc.inventory.add(make_item("potion_healing", rng, buc="uncursed",
                               enchant=0, quantity=2))
    pc.inventory.add(make_item("ration", rng, buc="uncursed", enchant=0))

    # Casters start knowing their tradition's spells, with the books.
    for spell_id in STARTING_SPELLS.get(pc.cls.id, ()):
        pc.learn_spell(spell_id, castings=25)
        pc.inventory.add(make_item(f"book_{spell_id}", rng,
                                   buc="uncursed", enchant=0))

    pc.equipment.recompute(pc.actor)
    pc.update_encumbrance()


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
    # DV grows gently with depth (steeper slopes made mid-game monsters
    # unhittable for an on-curve hero — verified by run simulations).
    actor.armor_dv = int(mdef.dv + 0.45 * (depth + level_bonus)) - \
        ((attrs.Dx - 12) // 2 + (attrs.Dx - 9) // 2)
    actor.armor_pv = mdef.pv
    actor.weapon_dice = mdef.attack
    actor.hostile = True
    return actor
