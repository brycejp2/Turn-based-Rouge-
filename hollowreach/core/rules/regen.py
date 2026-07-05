"""Natural HP/PP regeneration (design ref §5.2 regen rates, §6.2 Healing).

Each turn the hero recovers a fraction of a hit point / power point.  The
interval (turns per point) comes from the ancestry's regen rate, shortened
by the Healing skill, the Beacon omen and Healer class powers via
``pc.regen_mult`` / ``pc.pp_regen_mult``.  This gives Toughness-light but
regen-heavy builds a real identity and makes the Healing skill matter.
"""

from __future__ import annotations


def _interval(base: int, mult: float, skill: int) -> float:
    """Turns per point recovered (lower = faster)."""
    interval = base * mult
    interval *= max(0.4, 1.0 - skill / 150.0)   # Healing/Concentration help
    return max(1.0, interval)


def advance_regen(pc) -> None:
    actor = pc.actor
    healing = pc.skills.get("Healing", 0)

    if actor.hp < actor.max_hp:
        interval = _interval(pc.race.hp_regen, pc.regen_mult, healing)
        pc.hp_regen_counter += 1.0
        while pc.hp_regen_counter >= interval and actor.hp < actor.max_hp:
            actor.hp += 1
            pc.hp_regen_counter -= interval
    else:
        pc.hp_regen_counter = 0.0

    if actor.pp < actor.max_pp:
        concentration = pc.skills.get("Concentration", 0)
        interval = _interval(pc.race.pp_regen, pc.pp_regen_mult, concentration)
        pc.pp_regen_counter += 1.0
        while pc.pp_regen_counter >= interval and actor.pp < actor.max_pp:
            actor.pp += 1
            pc.pp_regen_counter -= interval
    else:
        pc.pp_regen_counter = 0.0
