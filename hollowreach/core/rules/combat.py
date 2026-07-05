"""Melee combat resolution (design plan §7.1).

Resolution order per attack:

1. **To-hit** roll: attacker melee bonus + ``1d20`` vs defender **DV**.
2. On a hit, roll weapon damage dice + strength bonus, then **PV** soaks
   a share of it (PV never reduces a hit below a small minimum, matching
   the "a blow always stings a little" rule).
3. Apply on-hit specials (poison, corruption, drain) — hooked here for
   later milestones.

Returns a :class:`CombatResult` the UI turns into a message-log line.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..engine.rng import Rng
from ..model.actor import Actor


@dataclass
class CombatResult:
    attacker: str
    defender: str
    hit: bool
    damage: int
    killed: bool
    critical: bool = False
    message: str = ""


def melee_attack(attacker: Actor, defender: Actor, rng: Rng) -> CombatResult:
    """Resolve one melee *action*, which may land several strikes when the
    attacker's weapon proficiency / Dexterity grant extra attacks (§6.3)."""
    strikes = 1 + max(0, getattr(attacker, "extra_attacks", 0))
    total = 0
    hits = 0
    any_crit = False
    killed = False

    for _ in range(strikes):
        if not defender.is_alive:
            break
        struck, dealt, crit = _single_strike(attacker, defender, rng)
        if struck:
            hits += 1
            total += dealt
            any_crit = any_crit or crit
        if not defender.is_alive:
            killed = True
            break

    if hits == 0:
        return CombatResult(
            attacker.name, defender.name, hit=False, damage=0, killed=False,
            message=f"{_cap(attacker.name)} misses {defender.name}.",
        )

    if strikes > 1 and hits > 1:
        body = f"{_cap(attacker.name)} hits {defender.name} {hits}× ({total})."
    else:
        verb = "critically hits" if any_crit else "hits"
        body = f"{_cap(attacker.name)} {verb} {defender.name} ({total})."
    if killed:
        body += f" {_cap(defender.name)} dies!"
    return CombatResult(
        attacker.name, defender.name, hit=True, damage=total,
        killed=killed, critical=any_crit, message=body,
    )


def _single_strike(attacker: Actor, defender: Actor, rng: Rng):
    """One strike. Returns (hit, damage_dealt, was_critical)."""
    to_hit = attacker.melee_to_hit + rng.rnd(20)
    dv = defender.dv
    if to_hit <= dv:
        return False, 0, False

    # Criticals: a wide to-hit margin, or the attacker's flat crit bonus
    # (Find Weakness skill, Monk precision) (§6.2).
    crit_bonus = getattr(attacker, "crit_bonus", 0)
    critical = (to_hit >= dv + 20 and rng.one_in(4)) or rng.chance(crit_bonus)
    raw = rng.roll(attacker.weapon_dice) + attacker.melee_damage_bonus
    if critical:
        raw *= 2
    raw = max(1, raw)

    soaked = max(1, raw - defender.pv)   # a blow always stings a little
    dealt = defender.take_damage(soaked)
    return True, dealt, critical


def _cap(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name
