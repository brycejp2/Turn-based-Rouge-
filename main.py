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


def _demo_command(game) -> str:
    """BFS-driven AI: attack the nearest known monster, else head for the
    down-stairs, else explore toward the nearest unexplored tile."""
    pc = game.pc.actor
    level = game.levels[game.depth]

    # 1. Fight the nearest reachable monster we've seen.
    monsters = [m for m in level.monsters() if level.explored[m.y][m.x]]
    if monsters:
        step = _bfs_step(level, pc, {(m.x, m.y) for m in monsters},
                         attack_targets=True)
        if step is not None:
            return step

    # 2. Descend if we're on / can reach the down-stairs.
    if level.tile(pc.x, pc.y).key == "stairs_down":
        return ">"
    if level.stairs_down is not None and level.explored[level.stairs_down[1]][level.stairs_down[0]]:
        step = _bfs_step(level, pc, {level.stairs_down})
        if step is not None:
            return step

    # 3. Explore toward the nearest unexplored, reachable tile.
    frontier = _explore_frontier(level, game.visible)
    if frontier:
        step = _bfs_step(level, pc, frontier)
        if step is not None:
            return step
    return "."


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
    from hollowreach.ui.render import render_level, status_line
    curses.curs_set(0)
    stdscr.nodelay(False)

    pending = {"cmd": None}

    def get_command():
        return pending["cmd"] or "."

    while game.running and game.pc.actor.is_alive:
        stdscr.erase()
        level = game.levels[game.depth]
        grid = render_level(level, game.pc.actor, game.visible)
        for y, row in enumerate(grid.split("\n")):
            _safe_add(stdscr, y, 0, row)
        h = level.height
        _safe_add(stdscr, h + 1, 0, status_line(game.pc))
        _safe_add(stdscr, h + 2, 0, game.calendar.describe())
        for i, msg in enumerate(game.log.recent(4)):
            _safe_add(stdscr, h + 4 + i, 0, msg)
        _safe_add(stdscr, h + 9, 0,
                  "move: hjkl/yubn  > down  < up  .wait  Q quit")
        stdscr.refresh()

        key = stdscr.getch()
        pending["cmd"] = _translate_key(key)
        if pending["cmd"] == "Q":
            game.running = False
            break
        game.run_turn(get_command)

    stdscr.nodelay(False)
    _safe_add(stdscr, 0, 0, "  --- press any key to exit ---  ")
    stdscr.refresh()
    stdscr.getch()


def _translate_key(key):
    try:
        ch = chr(key)
    except ValueError:
        return "."
    if ch in DIRECTIONS or ch in (">", "<", "Q"):
        return ch
    return "."


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
