"""Weapon proficiencies — the "marks" system (design ref §6.3).

Separate from general skills.  Each weapon **category** (sword, axe,
blunt, spear, dagger, unarmed) has its own proficiency that grows as you
fight with weapons of that category.  Landing melee blows earns *marks*;
crossing a threshold raises the proficiency **level**, which grants
cumulative to-hit, damage and DV — and, at the higher tiers, **extra
attacks per action**.  This is what rewards committing to a weapon style
and gives each build its combat feel.

Mark gain scales with class aptitude (``weapon_mark_rate``) and the Blade
omen, so a Fighter masters a blade far faster than a Wizard.
"""

from __future__ import annotations

# Proficiency tiers: (name, to_hit, damage, dv, extra_attacks) — cumulative.
PROFICIENCY_TIERS = [
    ("unskilled", 0, 0, 0, 0),
    ("basic",     1, 0, 0, 0),
    ("skilled",   2, 1, 1, 0),
    ("adept",     3, 1, 1, 0),
    ("expert",    4, 2, 2, 0),
    ("master",    5, 3, 2, 1),   # first extra attack
    ("grand master", 6, 3, 3, 1),
    ("legendary", 7, 4, 3, 2),
    ("mythic",    8, 5, 4, 2),
]

# Marks required to *reach* tier k (index 1..8); tier 0 needs none.
TIER_THRESHOLDS = [0, 8, 20, 45, 85, 150, 250, 400, 650]

CATEGORIES = ("sword", "axe", "blunt", "spear", "dagger", "unarmed")


def tier_for_marks(marks: float) -> int:
    tier = 0
    for i, threshold in enumerate(TIER_THRESHOLDS):
        if marks >= threshold:
            tier = i
    return tier


def tier_name(tier: int) -> str:
    return PROFICIENCY_TIERS[tier][0]


def tier_bonuses(tier: int):
    """Return (to_hit, damage, dv, extra_attacks) for a proficiency tier."""
    _name, th, dmg, dv, extra = PROFICIENCY_TIERS[tier]
    return th, dmg, dv, extra


def mark_gain(pc) -> float:
    """Marks earned for one landed blow, scaled by class + omen (§6.3)."""
    rate = pc.cls.weapon_mark_rate or 1.0
    gain = 1.0 / max(0.1, rate)
    omen_mult = pc.sign.effects.get("melee_mark_cost_mult", 1.0)
    gain /= max(0.1, omen_mult)   # cheaper marks => more per blow
    return gain


class Proficiencies:
    """Per-character marks and levels for each weapon category."""

    def __init__(self):
        self.marks: dict[str, float] = {c: 0.0 for c in CATEGORIES}
        self.tier: dict[str, int] = {c: 0 for c in CATEGORIES}

    def category_of(self, pc) -> str:
        weapon = pc.equipment.weapon()
        if weapon is None:
            return "unarmed"
        return weapon.base.weapon_skill or "unarmed"

    def award(self, pc, category: str) -> "str | None":
        """Add marks for a landed blow; return a tier-up message or None."""
        self.marks[category] = self.marks.get(category, 0.0) + mark_gain(pc)
        new_tier = tier_for_marks(self.marks[category])
        if new_tier > self.tier.get(category, 0):
            self.tier[category] = new_tier
            return (f"You feel more skilled with {category} weapons "
                    f"({tier_name(new_tier)}).")
        return None

    def apply_to_actor(self, pc) -> None:
        """Fold the wielded category's proficiency into the actor (§6.3)."""
        category = self.category_of(pc)
        tier = self.tier.get(category, 0)
        th, dmg, dv, extra = tier_bonuses(tier)
        actor = pc.actor
        actor.prof_to_hit = th
        actor.prof_dmg = dmg
        actor.prof_dv = dv
        # Extra attacks: proficiency tier + Dexterity + class-power extras.
        dex_bonus = max(0, (actor.attributes.Dx - 15) // 8)
        actor.extra_attacks = extra + dex_bonus + actor.class_extra_attacks
