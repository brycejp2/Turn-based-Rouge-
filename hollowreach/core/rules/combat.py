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
    to_hit = attacker.melee_to_hit + rng.rnd(20)
    dv = defender.dv

    if to_hit <= dv:
        return CombatResult(
            attacker.name, defender.name, hit=False, damage=0, killed=False,
            message=f"{_cap(attacker.name)} misses {defender.name}.",
        )

    # Damage: weapon dice + strength bonus, criticals on a wide margin.
    critical = to_hit >= dv + 20 and rng.one_in(4)
    raw = rng.roll(attacker.weapon_dice) + attacker.melee_damage_bonus
    if critical:
        raw *= 2
    raw = max(1, raw)

    # PV soak — a hit always deals at least 1.
    soaked = max(1, raw - defender.pv)
    dealt = defender.take_damage(soaked)
    killed = not defender.is_alive

    verb = "critically hits" if critical else "hits"
    msg = f"{_cap(attacker.name)} {verb} {defender.name} ({dealt})."
    if killed:
        msg += f" {_cap(defender.name)} dies!"
    return CombatResult(
        attacker.name, defender.name, hit=True, damage=dealt,
        killed=killed, critical=critical, message=msg,
    )


def _cap(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name
