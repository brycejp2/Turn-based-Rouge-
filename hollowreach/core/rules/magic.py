"""Spell resolution (design ref §8).

Casting is driven from ``game.cast_spell`` (which handles PP cost, spell
knowledge and power); this module turns a chosen spell + direction into
effects on the level: bolts that streak down a line, balls that burst in
an area, self-heals, light, and blinks.  Elemental damage is scaled
against monster types by :func:`resist_mult`.
"""

from __future__ import annotations

from ..world.fov import compute_fov
from ...content.monsters import MONSTERS

# element x monster-type multipliers (missing pairs default to 1.0).
_RESIST = {
    ("fire", "hollowed"): 1.5, ("fire", "plant"): 2.0, ("fire", "demon"): 0.5,
    ("cold", "hollowed"): 0.5, ("cold", "undead"): 0.5,
    ("shock", "construct"): 0.5,
    ("light", "hollowed"): 1.75, ("light", "undead"): 1.75,
    ("light", "demon"): 1.5,
}


def _types_of(actor) -> tuple:
    mdef = MONSTERS.get(actor.monster_id)
    return mdef.types if mdef else ()


def resist_mult(element: str, types) -> float:
    if element in ("force", "none"):
        return 1.0
    mult = 1.0
    for t in types:
        mult *= _RESIST.get((element, t), 1.0)
    return mult


def resolve(game, spell, direction, power: int) -> None:
    """Apply ``spell``'s effect, logging messages and handling kills."""
    kind = spell.kind
    if kind == "bolt":
        _bolt(game, spell, direction, power)
    elif kind == "ball":
        _ball(game, spell, direction, power)
    elif kind == "heal":
        _heal(game, spell, power)
    elif kind == "light":
        _light(game)
    elif kind == "teleport":
        _teleport(game)


def _damage_monster(game, mon, spell, power) -> int:
    dmg = game.rng.roll(spell.dice) + power
    dmg = int(dmg * resist_mult(spell.element, _types_of(mon)))
    dmg = max(1, dmg)
    mon.take_damage(dmg)
    return dmg


def _bolt(game, spell, direction, power) -> None:
    dx, dy = direction
    level = game.levels[game.depth]
    pc = game.pc.actor
    x, y = pc.x, pc.y
    struck = []
    for _ in range(spell.reach):
        x += dx
        y += dy
        if not level.in_bounds(x, y) or not level.tile(x, y).walkable:
            break
        mon = level.actor_at(x, y)
        if mon is not None and mon.is_alive and not mon.is_player:
            dmg = _damage_monster(game, mon, spell, power)
            struck.append((mon, dmg))
    if not struck:
        game.log.add(f"The {spell.name} streaks off and fizzles.")
        return
    for mon, dmg in struck:
        game.log.add(f"The {spell.name} hits {mon.name} ({dmg}).")
    for mon, _dmg in struck:
        if not mon.is_alive:
            game._reward_kill(mon)


def _ball(game, spell, direction, power) -> None:
    dx, dy = direction
    level = game.levels[game.depth]
    pc = game.pc.actor
    x, y = pc.x, pc.y
    # Fly until we hit a wall, a monster, or the range limit.
    for _ in range(spell.reach):
        nx, ny = x + dx, y + dy
        if not level.in_bounds(nx, ny) or not level.tile(nx, ny).walkable:
            break
        x, y = nx, ny
        if level.actor_at(x, y) is not None and not level.actor_at(x, y).is_player:
            break
    radius = spell.radius_base + pc.attributes.Wi // 8
    game.log.add(f"The {spell.name} bursts!")
    victims = []
    for mon in list(level.monsters()):
        if max(abs(mon.x - x), abs(mon.y - y)) <= radius:
            dmg = _damage_monster(game, mon, spell, power)
            victims.append((mon, dmg))
    for mon, dmg in victims:
        game.log.add(f"  {mon.name} is caught in the blast ({dmg}).")
    for mon, _dmg in victims:
        if not mon.is_alive:
            game._reward_kill(mon)


def _heal(game, spell, power) -> None:
    a = game.pc.actor
    amount = game.rng.roll(spell.dice) + power
    a.heal(amount)
    game.log.add(f"You cast {spell.name}. Wounds close. (+{amount} HP)")


def _light(game) -> None:
    level = game.levels[game.depth]
    pc = game.pc.actor
    for (x, y) in compute_fov(level, pc.x, pc.y, 7):
        level.explored[y][x] = True
        game.visible.add((x, y))
    game.log.add("Light blooms around you.")


def _teleport(game) -> None:
    level = game.levels[game.depth]
    pc = game.pc.actor
    for _ in range(200):
        x = game.rng.randint(1, level.width - 2)
        y = game.rng.randint(1, level.height - 2)
        if level.is_walkable(x, y) and level.actor_at(x, y) is None:
            pc.x, pc.y = x, y
            game._update_fov()
            game.log.add("You blink across the level.")
            return
    game.log.add("The blink fizzles.")
