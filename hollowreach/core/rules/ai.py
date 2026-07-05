"""Minimal monster AI (foundational slice).

Hostile monsters that can see the player step toward it and attack when
adjacent; otherwise they wander.  This is deliberately simple — later
milestones layer on the special-ability components from §12.2 (breeders,
summoners, breath weapons) behind the same ``take_turn`` entry point.
"""

from __future__ import annotations

from ..engine.rng import Rng
from .combat import melee_attack, CombatResult


def monster_turn(monster, player, level, rng: Rng) -> "CombatResult | None":
    dx = player.x - monster.x
    dy = player.y - monster.y
    dist2 = dx * dx + dy * dy

    # Adjacent (including diagonals): attack.
    if max(abs(dx), abs(dy)) == 1:
        return melee_attack(monster, player, rng)

    # Chase if reasonably close; else wander.
    if dist2 <= 100:
        step_x = _sign(dx)
        step_y = _sign(dy)
        if _try_step(monster, level, step_x, step_y):
            return None
        # Blocked diagonally — try the cardinal components.
        if step_x and _try_step(monster, level, step_x, 0):
            return None
        if step_y and _try_step(monster, level, 0, step_y):
            return None
        return None

    # Wander.
    wx, wy = rng.randint(-1, 1), rng.randint(-1, 1)
    if wx or wy:
        _try_step(monster, level, wx, wy)
    return None


def _try_step(actor, level, dx, dy) -> bool:
    nx, ny = actor.x + dx, actor.y + dy
    if not level.is_walkable(nx, ny):
        return False
    if level.actor_at(nx, ny) is not None:
        return False
    actor.x, actor.y = nx, ny
    return True


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)
