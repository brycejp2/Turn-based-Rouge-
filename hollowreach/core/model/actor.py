"""Actors: the player character and monsters (design plan §5, §7, §12).

This is where the plan's core numeric formulas live, transcribed as
directly as possible from the mechanics reference so they can be verified:

* **DV** (§7.2):  ``(Dx-12)/2 + (Dx-9)/2`` plus Dodge/Alertness/tactics
  and equipment, with the class unarmed bonuses (Monk ``+lvl*2/3``,
  Beastfighter ``+lvl/3``).
* **PV** (§7.2):  ``(To-18)/2`` capped at +20, plus armour and the
  Dwarven stoneskin +3.
* **Max HP** driven mainly by Toughness (§5.1), **max PP** by Mana.

Monsters and the PC share this class; ``is_player`` and the optional
``mdef``/character payload distinguish them.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .attributes import Attributes
from ..engine.scheduler import STANDARD_ACTION_COST


@dataclass
class Actor:
    name: str
    glyph: str
    attributes: Attributes
    x: int = 0
    y: int = 0
    level: object = None
    is_player: bool = False

    base_speed: int = 100
    char_level: int = 1

    max_hp: int = 0
    hp: int = 0
    max_pp: int = 0
    pp: int = 0

    # Equipment-derived combat values (set by the equipment layer later).
    armor_dv: int = 0
    armor_pv: int = 0
    weapon_dice: str = "1d3"       # unarmed default
    weapon_to_hit: int = 0
    weapon_dmg_bonus: int = 0

    # Class/skill contributions folded in by the character builder.
    dodge_dv: int = 0
    alertness_dv: int = 0
    unarmed_dv_per_level: float = 0.0   # Monk 2/3, Beastfighter 1/3
    stoneskin: int = 0                  # Dwarf innate +3 PV
    blessed: bool = False

    tactics_dv: int = 0                 # from the tactics slider (§7.3)
    tactics_to_hit: int = 0

    # Warp (Hollowing) contributions — see core/rules/blight.py.
    warp_dv: int = 0
    warp_pv: int = 0
    warp_unarmed_dmg: int = 0
    night_vision: bool = False
    unarmed: bool = True                # True while wielding no weapon

    # Class-power contributions (applied once at level breakpoints; never
    # reset — they accumulate permanently).
    class_dv: int = 0
    class_pv: int = 0
    class_to_hit: int = 0
    class_dmg: int = 0
    per_level_dmg: int = 0              # accrues from per-level class powers
    class_extra_attacks: int = 0
    class_crit: int = 0

    # Weapon-proficiency contributions for the wielded category (recomputed
    # by refresh_combat whenever the weapon or proficiency changes).
    prof_to_hit: int = 0
    prof_dmg: int = 0
    prof_dv: int = 0

    # Skill-derived contributions (recomputed by refresh_combat).
    athletics_speed: int = 0

    # Final computed combat values (set by refresh_combat).
    extra_attacks: int = 0             # extra melee strikes per action
    crit_bonus: int = 0                # +% critical chance

    alive: bool = True
    hostile: bool = True
    corruptions: int = 0
    monster_id: "str | None" = None
    encumbrance_penalty: int = 0        # speed lost to carry weight (§5.1)

    # Townsfolk (non-hostile NPCs): a role drives what bumping them does.
    npc_id: "str | None" = None
    role: "str | None" = None          # "shopkeeper" | "quest_giver" | "folk"

    # -- scheduler contract ----------------------------------------------
    @property
    def speed(self) -> int:
        spd = self.base_speed - self.encumbrance_penalty + self.athletics_speed
        return max(1, spd)

    @property
    def is_alive(self) -> bool:
        return self.alive and self.hp > 0

    # -- derived combat values -------------------------------------------
    @property
    def dv(self) -> int:
        """Defensive Value — chance to avoid a blow (§7.2)."""
        dx = self.attributes.Dx
        # Truncate toward zero to match the reference integer arithmetic.
        dv = int((dx - 12) / 2) + int((dx - 9) / 2)
        dv += self.armor_dv + self.dodge_dv + self.alertness_dv
        dv += self.tactics_dv + self.warp_dv + self.class_dv + self.prof_dv
        if self.unarmed_dv_per_level and not self._has_body_armor():
            dv += int(self.char_level * self.unarmed_dv_per_level)
        return max(0, dv)

    @property
    def pv(self) -> int:
        """Protection Value — damage soak (§7.2)."""
        to = self.attributes.To
        pv = min(20, (to - 18) // 2) if to > 18 else 0
        pv += self.armor_pv + self.stoneskin + self.warp_pv + self.class_pv
        if self.blessed:
            pv += 1 + (self.char_level // 25)  # +2 at L25, +3 at L50
        return max(0, pv)

    @property
    def melee_to_hit(self) -> int:
        """Attacker's to-hit bonus (level + weapon + Dx/St + tactics)."""
        dx = self.attributes.Dx
        st = self.attributes.St
        bonus = self.char_level
        bonus += (dx - 10) // 3 + (st - 10) // 4
        bonus += self.weapon_to_hit + self.tactics_to_hit
        bonus += self.class_to_hit + self.prof_to_hit
        return bonus

    @property
    def melee_damage_bonus(self) -> int:
        """Strength-driven flat damage added to weapon dice (§7.3)."""
        st = self.attributes.St
        bonus = 0
        if st > 15:
            bonus += st - 15
        if st < 6:
            bonus -= 6 - st
        if self.unarmed:
            bonus += self.warp_unarmed_dmg
        bonus += self.class_dmg + self.per_level_dmg + self.prof_dmg
        return bonus + self.weapon_dmg_bonus

    def _has_body_armor(self) -> bool:
        return self.armor_pv > 2  # rough proxy until equipment layer lands

    # -- health ----------------------------------------------------------
    def take_damage(self, amount: int) -> int:
        amount = max(0, amount)
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False
        return amount

    def heal(self, amount: int) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def restore_pp(self, amount: int) -> None:
        self.pp = min(self.max_pp, self.pp + amount)
