#!/usr/bin/env python3
"""Hollowreach — entry point.

Character creation order:
    Ancestry → Class → Gender → Omen → Attributes → Name.

Run modes:
    python main.py                 interactive (curses) game
    python main.py --demo [N]      headless AI demo, N turns (for CI/testing)
    python main.py --seed 12345    fix the RNG seed for a reproducible run
"""

from __future__ import annotations

import argparse
import sys

from hollowreach.core.engine.rng import Rng
from hollowreach.core.model.character import build_player
from hollowreach.content.races import RACES, DEFAULT_RACE
from hollowreach.content.classes import CLASSES, DEFAULT_CLASS
from hollowreach.content.starsigns import STAR_SIGNS, DEFAULT_STAR_SIGN
from hollowreach.game import Game, DIRECTIONS


DEFAULT_ATTRS = {"St": 12, "Le": 11, "Wi": 11, "Dx": 13, "To": 13,
                 "Ch": 9, "Ap": 10, "Ma": 10, "Pe": 11}


def make_game(seed: int, name: str, race: str, cls: str, sign: str,
              gender: str, permadeath: bool = True) -> Game:
    rng = Rng(seed)
    pc = build_player(name, race, cls, sign, gender, dict(DEFAULT_ATTRS), rng)
    return Game.new(pc, rng, seed, permadeath=permadeath)


# ---------------------------------------------------------------------------
# Headless demo — a simple greedy AI so the whole stack can be exercised
# without a terminal (used by CI and `verify`).
# ---------------------------------------------------------------------------
def run_demo(seed: int, turns: int) -> int:
    from hollowreach.ui.render import render_screen
    game = make_game(seed, "Demo", "dwarf", "fighter", "beacon", "male",
                     permadeath=False)

    print("=== Hollowreach demo run ===")
    print(f"seed={seed}  {game.pc.race.name} {game.pc.cls.name}  "
          f"sign={game.pc.sign.name}")
    print(render_screen(game.levels[game.depth], game.pc, game.visible, game.log))
    print()

    step = 0
    while game.running and step < turns and game.pc.actor.is_alive:
        game.run_turn(lambda: _demo_command(game))
        step += 1

    print(render_screen(game.levels[game.depth], game.pc, game.visible, game.log))
    print()
    print(f"Demo ended after {step} player turns. "
          f"HP {game.pc.actor.hp}/{game.pc.actor.max_hp}, "
          f"char level {game.pc.actor.char_level}, "
          f"XP {game.pc.xp}, DL {game.depth}, "
          f"time {game.calendar.describe()}.")
    return 0


def _demo_command(game):
    """BFS-driven AI that also uses the item systems: heal when desperate,
    grab loot, equip upgrades, fight, descend, explore."""
    pc = game.pc.actor
    level = game.levels[game.depth]

    # 0. Desperation: quaff a potion when critically hurt (use-ID it).
    if pc.hp * 100 < pc.max_hp * 35:
        potion = _demo_pick_potion(game)
        if potion is not None:
            return ("quaff", potion)

    # 1. Grab anything underfoot, then equip any upgrade in the pack.
    if level.items_at(pc.x, pc.y):
        return ("pickup", None)
    upgrade = _demo_find_upgrade(game)
    if upgrade is not None:
        return ("equip", upgrade)

    # 2. Fight the nearest reachable monster we've seen.
    monsters = [m for m in level.monsters() if level.explored[m.y][m.x]]
    if monsters:
        step = _bfs_step(level, pc, {(m.x, m.y) for m in monsters},
                         attack_targets=True)
        if step is not None:
            return step

    # 3. Collect known loot piles on the way down.
    piles = {xy for xy in level.items
             if level.explored[xy[1]][xy[0]] and level.items_at(*xy)}
    if piles:
        step = _bfs_step(level, pc, piles)
        if step is not None:
            return step

    # 4. Descend if we're on / can reach the down-stairs.
    if level.tile(pc.x, pc.y).key == "stairs_down":
        return ">"
    if level.stairs_down is not None and level.explored[level.stairs_down[1]][level.stairs_down[0]]:
        step = _bfs_step(level, pc, {level.stairs_down})
        if step is not None:
            return step

    # 5. Explore toward the nearest unexplored, reachable tile.
    frontier = _explore_frontier(level, game.visible)
    if frontier:
        step = _bfs_step(level, pc, frontier)
        if step is not None:
            return step
    return "."


def _demo_pick_potion(game):
    """Prefer a known healing potion; else any potion (a desperation gamble)."""
    known, any_potion = None, None
    for _letter, item in game.pc.inventory.of_category({"potion"}):
        if any_potion is None:
            any_potion = item
        if item.identified and item.base.effect in ("heal", "extra_heal"):
            known = item
    return known or any_potion


def _demo_find_upgrade(game):
    """Return an unequipped item that beats what's worn (or fills an empty slot)."""
    from hollowreach.core.engine.rng import Dice
    equip = game.pc.equipment
    for _letter, item in game.pc.inventory.listing():
        slot = item.slot
        if slot is None:
            continue
        if item.category == "weapon":
            cur = equip.weapon()
            cur_avg = Dice.parse(cur.base.dmg_dice).average if cur else Dice.parse("1d3").average
            if Dice.parse(item.base.dmg_dice).average > cur_avg:
                return item
        else:
            target = slot if slot != "ring" else "ring1"
            worn = equip.worn.get(target)
            if worn is None:
                return item
            if item.pv_bonus + item.dv_bonus > worn.pv_bonus + worn.dv_bonus:
                return item
    return None


def _explore_frontier(level, visible):
    """Explored floor tiles that border an unexplored neighbour."""
    frontier = set()
    for y in range(level.height):
        for x in range(level.width):
            if not level.explored[y][x] or not level.is_walkable(x, y):
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if level.in_bounds(nx, ny) and not level.explored[ny][nx]:
                    frontier.add((x, y))
                    break
    return frontier


def _bfs_step(level, pc, goals, attack_targets=False):
    """Return the direction key of the first step on the shortest path to
    any goal cell, or ``None`` if unreachable.  With ``attack_targets`` the
    goal cells may hold a monster (the final bump becomes an attack)."""
    from collections import deque
    start = (pc.x, pc.y)
    if start in goals:
        return "."
    prev = {start: None}
    queue = deque([start])
    found = None
    while queue:
        cx, cy = queue.popleft()
        if (cx, cy) in goals and (cx, cy) != start:
            found = (cx, cy)
            break
        for dx, dy in DIRECTIONS.values():
            if dx == 0 and dy == 0:
                continue
            nx, ny = cx + dx, cy + dy
            if (nx, ny) in prev or not level.in_bounds(nx, ny):
                continue
            is_goal = (nx, ny) in goals
            if not level.is_walkable(nx, ny):
                continue
            blocker = level.actor_at(nx, ny)
            if blocker is not None and blocker is not pc and not (is_goal and attack_targets):
                continue
            prev[(nx, ny)] = (cx, cy)
            if is_goal:
                found = (nx, ny)
                queue.clear()
                break
            queue.append((nx, ny))
    if found is None:
        return None
    # Walk back to the first step from start.
    node = found
    while prev[node] != start:
        node = prev[node]
    dx, dy = node[0] - pc.x, node[1] - pc.y
    for key, delta in DIRECTIONS.items():
        if delta == (dx, dy):
            return key
    return "."


# ---------------------------------------------------------------------------
# Interactive curses front-end.
# ---------------------------------------------------------------------------
def run_interactive(seed: int) -> int:
    try:
        import curses
    except ImportError:
        print("curses unavailable; use --demo instead.")
        return 1

    name, race, cls, sign, gender = _prompt_character()
    game = make_game(seed, name, race, cls, sign, gender)
    curses.wrapper(_curses_loop, game)
    return 0


def _prompt_character():
    print("=== Create your hero (Enter accepts the default) ===")
    name = input("Name [Grimm]: ").strip() or "Grimm"
    race = _pick("Ancestry", RACES, DEFAULT_RACE)
    cls = _pick("Class", CLASSES, DEFAULT_CLASS)
    gender = (input("Gender (male/female) [male]: ").strip().lower() or "male")
    if gender not in ("male", "female"):
        gender = "male"
    sign = _pick("Omen", STAR_SIGNS, DEFAULT_STAR_SIGN)
    return name, race, cls, sign, gender


def _pick(label, table, default):
    keys = list(table)
    print(f"\n{label}:")
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {table[key].name}")
    choice = input(f"{label} [{table[default].name}]: ").strip()
    if not choice:
        return default
    if choice.isdigit() and 1 <= int(choice) <= len(keys):
        return keys[int(choice) - 1]
    for key in keys:
        if key.startswith(choice.lower()) or table[key].name.lower().startswith(choice.lower()):
            return key
    return default


def _curses_loop(stdscr, game):
    import curses
    curses.curs_set(0)
    stdscr.nodelay(False)
    pending = {"cmd": "."}

    def get_command():
        return pending["cmd"]

    while game.running and game.pc.actor.is_alive:
        _draw_main(stdscr, game)
        action = _handle_key(stdscr, game, stdscr.getch())
        if action == "QUIT":
            game.running = False
            break
        if action is None:
            continue  # non-turn UI action (viewed inventory / cancelled)
        pending["cmd"] = action
        game.run_turn(get_command)

    _draw_main(stdscr, game)
    _safe_add(stdscr, 0, 0, "  --- press any key to exit ---  ")
    stdscr.refresh()
    stdscr.getch()


def _draw_main(stdscr, game):
    from hollowreach.ui.render import render_level, status_line
    stdscr.erase()
    level = game.levels[game.depth]
    for y, row in enumerate(render_level(level, game.pc.actor, game.visible).split("\n")):
        _safe_add(stdscr, y, 0, row)
    h = level.height
    _safe_add(stdscr, h + 1, 0, status_line(game.pc))
    _safe_add(stdscr, h + 2, 0, game.calendar.describe())
    for i, msg in enumerate(game.log.recent(4)):
        _safe_add(stdscr, h + 4 + i, 0, msg)
    _safe_add(stdscr, h + 9, 0,
              "hjkl/yubn move  >< stairs  g get  i inv  w wield  T takeoff  "
              "q quaff  r read  d drop  . wait  Q quit")
    stdscr.refresh()


def _handle_key(stdscr, game, key):
    """Translate a keypress into a turn action (string/tuple), a non-turn UI
    action (returns None), or the QUIT sentinel."""
    try:
        ch = chr(key)
    except ValueError:
        return None
    if ch in DIRECTIONS or ch in (">", "<"):
        return ch
    if ch == "Q":
        return "QUIT"
    if ch in ("g", ","):
        return ("pickup", None)
    if ch == "i":
        _show_inventory(stdscr, game)
        return None
    if ch == "q":
        it = _select_item(stdscr, game, {"potion"}, "Quaff which potion?")
        return ("quaff", it) if it else None
    if ch == "r":
        it = _select_item(stdscr, game, {"scroll"}, "Read which scroll?")
        return ("read", it) if it else None
    if ch == "w":
        it = _select_item(stdscr, game, None, "Wield/wear what?", equippable=True)
        return ("equip", it) if it else None
    if ch == "T":
        slot = _select_worn(stdscr, game)
        return ("unequip", slot) if slot else None
    if ch == "d":
        it = _select_item(stdscr, game, None, "Drop what?")
        return ("drop", it) if it else None
    return None


def _select_item(stdscr, game, categories, prompt, equippable=False):
    items = game.pc.inventory.listing()
    if equippable:
        items = [(l, it) for l, it in items if it.slot is not None]
    elif categories is not None:
        items = [(l, it) for l, it in items if it.category in categories]
    if not items:
        _flash(stdscr, "You have nothing suitable.")
        return None
    labelled = [(l, game.id_service.display_name(it), it) for l, it in items]
    return _menu(stdscr, prompt, labelled)


def _select_worn(stdscr, game):
    worn = game.pc.equipment.worn_items()
    if not worn:
        _flash(stdscr, "You are wearing nothing.")
        return None
    labelled = [(chr(ord("a") + i), f"{slot}: {game.id_service.display_name(it)}", slot)
                for i, (slot, it) in enumerate(worn)]
    return _menu(stdscr, "Take off what?", labelled)


def _menu(stdscr, prompt, entries):
    """entries: list of (key_letter, label, value). Returns chosen value or None."""
    while True:
        stdscr.erase()
        _safe_add(stdscr, 0, 0, prompt + "   (letter to choose, ESC/space to cancel)")
        for i, (letter, label, _value) in enumerate(entries):
            _safe_add(stdscr, i + 2, 2, f"{letter}) {label}")
        stdscr.refresh()
        key = stdscr.getch()
        if key in (27, ord(" ")):
            return None
        try:
            ch = chr(key)
        except ValueError:
            continue
        for letter, _label, value in entries:
            if ch == letter:
                return value


def _show_inventory(stdscr, game):
    stdscr.erase()
    _safe_add(stdscr, 0, 0, "Inventory   (any key to return)")
    row = 2
    _safe_add(stdscr, row, 0, "Worn:")
    row += 1
    worn = game.pc.equipment.worn_items()
    if not worn:
        _safe_add(stdscr, row, 2, "(nothing)")
        row += 1
    for slot, it in worn:
        _safe_add(stdscr, row, 2, f"{slot:<7} {game.id_service.display_name(it)}")
        row += 1
    row += 1
    _safe_add(stdscr, row, 0, "Pack:")
    row += 1
    if game.pc.inventory.is_empty():
        _safe_add(stdscr, row, 2, "(empty)")
        row += 1
    for letter, it in game.pc.inventory.listing():
        _safe_add(stdscr, row, 2, f"{letter}) {game.id_service.display_name(it)}")
        row += 1
    cap = 800 + game.pc.actor.attributes.St * 120
    _safe_add(stdscr, row + 1, 0,
              f"Weight: {game.pc.inventory.total_weight()} / {cap}")
    stdscr.refresh()
    stdscr.getch()


def _flash(stdscr, message):
    _safe_add(stdscr, 0, 0, message + "  (press any key)")
    stdscr.refresh()
    stdscr.getch()


def _safe_add(stdscr, y, x, text):
    import curses
    try:
        stdscr.addstr(y, x, text)
    except curses.error:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Hollowreach roguelike")
    parser.add_argument("--demo", nargs="?", const=200, type=int,
                        help="run a headless AI demo for N turns (default 200)")
    parser.add_argument("--seed", type=int, default=1,
                        help="RNG seed for a reproducible run")
    args = parser.parse_args(argv)

    if args.demo is not None:
        return run_demo(args.seed, args.demo)
    return run_interactive(args.seed)


if __name__ == "__main__":
    sys.exit(main())
