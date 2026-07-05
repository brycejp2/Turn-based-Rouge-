"""General skills — advancement and effects (design ref §6.2).

Skills are 0–100.  They rise on level-up (a few picks, more with high
Learning or the Tome omen) and, for combat skills, occasionally through
use.  A subset is wired into the combat math here; the rest are recorded
for systems that arrive in later milestones.

Wired effects:
* **Athletics** — up to +8 speed near mastery.
* **Dodge** — +DV that scales with skill.
* **Alertness** — +1/+2/+4 DV at 75/90/100.
* **Find Weakness** — +critical chance.
* **Healing** — shortens natural regeneration intervals (see regen.py).
"""

from __future__ import annotations

# Combat skills that can rise through use.
_USE_TRAINED = ("Find Weakness", "Dodge", "Athletics", "Tactics")


def apply_skill_bonuses(pc) -> None:
    """Recompute skill-derived actor fields (called by refresh_combat)."""
    actor = pc.actor
    skills = pc.skills

    dodge = skills.get("Dodge", 0)
    actor.dodge_dv = dodge // 20                      # +0..+5

    alert = skills.get("Alertness", 0)
    actor.alertness_dv = 4 if alert >= 100 else 2 if alert >= 90 else \
        1 if alert >= 75 else 0

    athletics = skills.get("Athletics", 0)
    actor.athletics_speed = min(8, athletics // 12)   # +8 near 100

    find_weakness = skills.get("Find Weakness", 0)
    skill_crit = find_weakness // 10                  # +0..+10 %
    actor.crit_bonus = actor.class_crit + skill_crit


def gain_level_skills(pc, rng) -> None:
    """Raise a handful of known skills on level-up (§6.1)."""
    if not pc.skills:
        return
    le = pc.actor.attributes.Le
    picks = 3 + (1 if le >= 15 else 0) + (1 if le >= 20 else 0)
    picks += pc.sign.effects.get("free_skill_per_level", 0)
    names = list(pc.skills)
    for _ in range(picks):
        name = rng.choice(names)
        pc.skills[name] = min(100, pc.skills[name] + rng.rnd(3) + 1)


def train_on_use(pc, rng) -> "str | None":
    """Small chance to bump a known combat skill after a melee blow."""
    trainable = [s for s in _USE_TRAINED if s in pc.skills and pc.skills[s] < 100]
    if not trainable or not rng.one_in(12):
        return None
    name = rng.choice(trainable)
    pc.skills[name] = min(100, pc.skills[name] + 1)
    return name  # caller refreshes combat if a wired skill changed
