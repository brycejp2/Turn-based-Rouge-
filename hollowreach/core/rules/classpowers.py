"""Class powers — the level-6/12/18/25/32/40/50 gifts (design ref §5.3).

Each class grants a fixed set of powers at level breakpoints.  This
resolver applies them as a character levels up:

* **passive / one_time** — applied exactly once when the breakpoint is
  reached (attribute mods, flat DV/PV/to-hit/damage, speed, +extra
  attack, +crit, regen multiplier, auto-BUC).
* **per_level** — recurs, adding its payload every level from the
  breakpoint onward (e.g. Fighter's Melee mastery: +1 damage per level).

Powers are what give each class its late-game identity and are a major
axis of build variety.
"""

from __future__ import annotations

# Payload keys that map directly onto attribute modifiers.
_ATTR_KEYS = {"St", "Le", "Wi", "Dx", "To", "Ch", "Ap", "Ma", "Pe"}


def apply_level_powers(pc) -> list[str]:
    """Apply any powers unlocked at the character's *current* level.

    Returns human-readable messages for powers gained this level.
    """
    level = pc.actor.char_level
    messages: list[str] = []
    for power in pc.cls.class_powers:
        if power.kind == "per_level" and power.level <= level:
            _apply_per_level(pc, power)
        elif power.level == level and power.kind in ("passive", "one_time"):
            if power.name in pc.granted_powers:
                continue
            pc.granted_powers.add(power.name)
            _apply_once(pc, power)
            messages.append(f"Class power: {power.name}!")
    return messages


def _apply_per_level(pc, power) -> None:
    actor = pc.actor
    actor.per_level_dmg += power.payload.get("melee_dmg", 0)


def _apply_once(pc, power) -> None:
    actor = pc.actor
    payload = power.payload
    for key, value in payload.items():
        if key in _ATTR_KEYS:
            actor.attributes.apply_modifier(key, value)
        elif key == "to_hit":
            actor.class_to_hit += value
        elif key == "class_dmg":
            actor.class_dmg += value
        elif key == "dv":
            actor.class_dv += value
        elif key == "pv":
            actor.class_pv += value
        elif key == "speed":
            actor.base_speed += value
        elif key == "extra_attack":
            actor.class_extra_attacks += value  # folded in by refresh_combat
        elif key == "crit_bonus":
            actor.class_crit += value           # folded in by refresh_combat
        elif key == "hp_regen_mult":
            pc.regen_mult = value
        elif key == "auto_buc":
            pc.auto_buc = True
        elif key == "spell_cost_mult":
            pc.spell_cost_mult = value
        # else: unknown payload key — reserved for future systems.
