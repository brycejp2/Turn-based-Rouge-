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

from hollowreach.content.races import RACES, DEFAULT_RACE
from hollowreach.content.classes import CLASSES, DEFAULT_CLASS
from hollowreach.content.starsigns import STAR_SIGNS, DEFAULT_STAR_SIGN
from hollowreach.game import Game, DIRECTIONS
from hollowreach.bootstrap import new_game, DEFAULT_ATTRS

# Backwards-compatible alias used throughout the demo/tests.
make_game = new_game


# ---------------------------------------------------------------------------
# Headless demo — a simple greedy AI so the whole stack can be exercised
# without a terminal (used by CI and `verify`).
# ---------------------------------------------------------------------------
def run_demo(seed: int, turns: int, blight_enabled: bool = True) -> int:
    from hollowreach.ui.render import render_screen
    game = make_game(seed, "Demo", "dwarf", "fighter", "beacon", "male",
                     permadeath=False, blight_enabled=blight_enabled)

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
    outcome = "WON" if game.won else ("DIED" if not game.pc.actor.is_alive else "stopped")
    print(f"Demo {outcome} after {step} player turns. "
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

    # 0. Desperation: heal-cast, else quaff a potion when critically hurt.
    if pc.hp * 100 < pc.max_hp * 40:
        heal = _demo_heal_spell(game)
        if heal is not None:
            return ("cast", (heal, None))
        potion = _demo_pick_potion(game)
        if potion is not None:
            return ("quaff", potion)

    # 0b. Casters: blast an aligned, visible monster with a bolt.
    cast = _demo_offensive_spell(game)
    if cast is not None:
        return cast

    # 1. Grab anything underfoot, then equip any upgrade in the pack.
    if level.items_at(pc.x, pc.y):
        return ("pickup", None)
    upgrade = _demo_find_upgrade(game)
    if upgrade is not None:
        return ("equip", upgrade)

    # 2. Fight monsters that are visible and *engaged* (within 3 tiles).
    # Chasing distant or merely-remembered monsters is a trap: wanderers
    # never get caught, detours pile up damage, and the Blight clock eats
    # the wasted turns (found via run tracing). Chasers come to you.
    monsters = [m for m in level.monsters()
                if (m.x, m.y) in game.visible
                and max(abs(m.x - pc.x), abs(m.y - pc.y)) <= 3]
    if monsters:
        step = _bfs_step(level, pc, {(m.x, m.y) for m in monsters},
                         attack_targets=True)
        if step is not None:
            return step

    # 2b. Final level: once the guardian is dead, make for the Gate to win.
    if level.is_final and level.gate is not None:
        boss = level.boss
        if (boss is None or not boss.is_alive) and \
                level.explored[level.gate[1]][level.gate[0]]:
            step = _bfs_step(level, pc, {level.gate})
            if step is not None:
                return step

    # 3. Descend if we're on / can reach the down-stairs.
    if level.tile(pc.x, pc.y).key == "stairs_down":
        return ">"
    if level.stairs_down is not None and level.explored[level.stairs_down[1]][level.stairs_down[0]]:
        step = _bfs_step(level, pc, {level.stairs_down})
        if step is not None:
            return step

    # 4. Explore toward the frontier. The chosen target is *sticky* —
    # re-picking the nearest tile every step makes the AI dither (left,
    # right, left...) whenever the frontier shifts, wasting turns that the
    # Blight clock punishes.
    frontier = _explore_frontier(level, game.visible)
    if frontier:
        # Keep walking to the committed goal until we stand on it (it may
        # leave the frontier as we approach — that's fine, it's still the
        # anchor that stops left/right dithering).
        goal = getattr(game, "_demo_goal", None)
        if goal is not None and goal != (pc.x, pc.y) and level.is_walkable(*goal):
            step = _bfs_step(level, pc, {goal})
            if step is not None and step != ".":
                return step
        game._demo_goal = _bfs_goal(level, pc, frontier)
        step = _bfs_step(level, pc, frontier)
        if step is not None:
            return step

    # 5. Everything reachable is blocked by monsters (a clogged corridor):
    # fight through toward the objective rather than waiting forever.
    objective = None
    if level.is_final and level.gate is not None:
        objective = level.gate
    elif level.stairs_down is not None:
        objective = level.stairs_down
    if objective is not None:
        step = _bfs_step(level, pc, {objective}, through_monsters=True)
        if step is not None:
            return step
    if frontier:
        step = _bfs_step(level, pc, frontier, through_monsters=True)
        if step is not None:
            return step
    return "."


def _demo_heal_spell(game):
    from hollowreach.content.spells import SPELLS
    for sid, state in game.pc.spells.items():
        if SPELLS[sid].kind == "heal" and state["castings"] > 0:
            if game.pc.actor.pp >= game._spell_cost(SPELLS[sid], state):
                return sid
    return None


def _demo_offensive_spell(game):
    """Cast a bolt at the nearest visible monster on a straight line."""
    from hollowreach.content.spells import SPELLS
    pc = game.pc.actor
    level = game.levels[game.depth]
    bolts = [(sid, s) for sid, s in game.pc.spells.items()
             if SPELLS[sid].kind == "bolt" and s["castings"] > 0]
    if not bolts:
        return None
    for mon in level.monsters():
        if (mon.x, mon.y) not in game.visible:
            continue
        dx, dy = mon.x - pc.x, mon.y - pc.y
        if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)):
            continue
        sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
        for sid, state in bolts:
            spell = SPELLS[sid]
            if max(abs(dx), abs(dy)) <= spell.reach and \
                    pc.pp >= game._spell_cost(spell, state):
                return ("cast", (sid, (sx, sy)))
    return None


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
    wielded = equip.weapon()

    def _welded(worn_item):
        # A known-cursed worn item can't come off; don't retry forever.
        return (worn_item is not None and worn_item.buc == "cursed"
                and worn_item.buc_known)

    for _letter, item in game.pc.inventory.listing():
        slot = item.slot
        if slot is None:
            continue
        if item.category == "weapon":
            # Respect the hands rule: no two-handers while a shield is worn.
            if item.base.two_handed and equip.worn.get("shield"):
                continue
            if _welded(wielded):
                continue
            cur_avg = (Dice.parse(wielded.base.dmg_dice).average
                       if wielded else Dice.parse("1d3").average)
            if Dice.parse(item.base.dmg_dice).average > cur_avg:
                return item
        else:
            if slot == "shield" and wielded is not None and wielded.base.two_handed:
                continue
            target = slot if slot != "ring" else "ring1"
            worn = equip.worn.get(target)
            if worn is None:
                return item
            if _welded(worn):
                continue
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


def _bfs_step(level, pc, goals, attack_targets=False, through_monsters=False):
    """First step (direction key) of the shortest path to any goal, or None."""
    return _bfs(level, pc, goals, attack_targets, through_monsters)[0]


def _bfs_goal(level, pc, goals, attack_targets=False, through_monsters=False):
    """The goal cell the shortest path reaches, or None."""
    return _bfs(level, pc, goals, attack_targets, through_monsters)[1]


def _bfs(level, pc, goals, attack_targets=False, through_monsters=False):
    """Shortest path to any goal cell: returns ``(first_step_key, goal)``.

    ``attack_targets``: goal cells may hold a monster (the final bump is an
    attack).  ``through_monsters``: monsters don't block the path at all —
    if the first step lands on one, the bump attacks it, which still makes
    progress (used to fight through clogged corridors)."""
    from collections import deque
    start = (pc.x, pc.y)
    if start in goals:
        return ".", start
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
            if (blocker is not None and blocker is not pc
                    and not through_monsters
                    and not (is_goal and attack_targets)):
                continue
            prev[(nx, ny)] = (cx, cy)
            if is_goal:
                found = (nx, ny)
                queue.clear()
                break
            queue.append((nx, ny))
    if found is None:
        return None, None
    # Walk back to the first step from start.
    node = found
    while prev[node] != start:
        node = prev[node]
    dx, dy = node[0] - pc.x, node[1] - pc.y
    for key, delta in DIRECTIONS.items():
        if delta == (dx, dy):
            return key, found
    return ".", found


# ---------------------------------------------------------------------------
# Interactive curses front-end.
# ---------------------------------------------------------------------------
def run_interactive(seed: int, blight_enabled: bool = True) -> int:
    try:
        import curses
    except ImportError:
        print("curses unavailable; use --demo instead.")
        return 1

    name, race, cls, sign, gender = _prompt_character()
    game = make_game(seed, name, race, cls, sign, gender,
                     blight_enabled=blight_enabled)
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

    while game.running and game.pc.actor.is_alive and not game.won:
        _draw_main(stdscr, game)
        action = _handle_key(stdscr, game, stdscr.getch())
        if action == "QUIT":
            game.running = False
            break
        if action is None:
            continue  # non-turn UI action (viewed inventory / cancelled)
        pending["cmd"] = action
        game.run_turn(get_command)
        if getattr(game, "pending_shop", False):
            game.pending_shop = False
            _shop_screen_curses(stdscr, game)

    _draw_main(stdscr, game)
    banner = ("  *** YOU SEALED THE GATE — YOU WIN! ***  " if game.won
              else "  --- press any key to exit ---  ")
    _safe_add(stdscr, 0, 0, banner)
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
              "hjkl/yubn move  >< stairs  g get  i inv  C char  J quests  z cast  "
              "w wield  T off  q quaff  r read  d drop  bump folk  Q quit")
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
    if ch in ("p", "O"):        # pray / offer at an altar
        return ch
    if ch in ("g", ","):
        return ("pickup", None)
    if ch == "i":
        _show_inventory(stdscr, game)
        return None
    if ch == "J":
        _show_quests_curses(stdscr, game)
        return None
    if ch == "C":
        _show_character(stdscr, game)
        return None
    if ch == "q":
        it = _select_item(stdscr, game, {"potion"}, "Quaff which potion?")
        return ("quaff", it) if it else None
    if ch == "r":
        it = _select_item(stdscr, game, {"scroll", "spellbook"},
                          "Read what?")
        return ("read", it) if it else None
    if ch == "z":
        return _cast_flow(stdscr, game)
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


def _cast_flow(stdscr, game):
    """Select a known spell, aim it if needed, return a cast command."""
    from hollowreach.content.spells import SPELLS
    if not game.pc.spells:
        return None
    letters = "abcdefghijklmnopqrstuvwxyz"
    entries = []
    for i, (sid, state) in enumerate(sorted(game.pc.spells.items())):
        spell = SPELLS[sid]
        cost = game._spell_cost(spell, state)
        entries.append((letters[i],
                        f"{spell.name}  {cost} PP  x{state['castings']}", sid))
    spell_id = _menu(stdscr, "Cast which spell?", entries)
    if spell_id is None:
        return None
    spell = SPELLS[spell_id]
    if spell.kind in ("bolt", "ball"):
        direction = _pick_direction(stdscr)
        if direction is None:
            return None
        return ("cast", (spell_id, direction))
    return ("cast", (spell_id, None))


def _pick_direction(stdscr):
    stdscr.erase()
    _safe_add(stdscr, 0, 0, "Aim: direction key (hjkl/yubn), Esc to cancel")
    stdscr.refresh()
    key = stdscr.getch()
    try:
        ch = chr(key)
    except ValueError:
        return None
    if ch in DIRECTIONS and DIRECTIONS[ch] != (0, 0):
        return DIRECTIONS[ch]
    return None


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


def _show_character(stdscr, game):
    from hollowreach.core.model.attributes import ATTRIBUTE_KEYS, ATTRIBUTE_NAMES
    from hollowreach.core.rules.proficiency import tier_name
    from hollowreach.content.warps import WARPS
    pc, a = game.pc, game.pc.actor
    stdscr.erase()
    row = 0
    def line(text, indent=0):
        nonlocal row
        _safe_add(stdscr, row, indent, text)
        row += 1

    line(f"{a.name} — level {a.char_level} {pc.race.name} {pc.cls.name} "
         f"(born under {pc.sign.name})")
    line(f"XP: {pc.xp}  (next level at {pc.xp_to_next_level()})")
    crown = "  — Champion" if pc.crowned else ""
    line(f"Faith: {pc.alignment} ({pc.alignment_score:+d})   "
         f"piety {pc.piety}{crown}")
    row += 1
    line("Attributes:")
    attr_str = "   ".join(f"{k} {a.attributes.value(k):>2}" for k in ATTRIBUTE_KEYS)
    line(attr_str, 2)
    row += 1
    line(f"Combat:  DV {a.dv}   PV {a.pv}   to-hit {a.melee_to_hit}   "
         f"weapon {a.weapon_dice}{'+'+str(a.melee_damage_bonus) if a.melee_damage_bonus else ''}   "
         f"attacks {1 + a.extra_attacks}   crit +{a.crit_bonus}%")
    line(f"Speed {a.speed}   HP {a.hp}/{a.max_hp}   PP {a.pp}/{a.max_pp}")
    row += 1
    line("Weapon proficiencies:")
    profs = [(c, t) for c, t in pc.proficiencies.tier.items() if t > 0]
    if profs:
        for cat, tier in profs:
            line(f"{cat:<8} {tier_name(tier)}", 2)
    else:
        line("(none trained yet)", 2)
    row += 1
    line("Skills:")
    listing = sorted(pc.skills.items())
    for i in range(0, len(listing), 3):
        chunk = listing[i:i + 3]
        line("   ".join(f"{n} {v:>3}" for n, v in chunk), 2)
    if pc.spells:
        from hollowreach.content.spells import SPELLS
        row += 1
        line("Spells known:")
        for sid, state in sorted(pc.spells.items()):
            sp = SPELLS[sid]
            line(f"{sp.name}  ({sp.pp} PP, x{state['castings']}, "
                 f"power {state['power']})", 2)
    if pc.warps:
        row += 1
        line("The Hollowing has warped you:")
        for wid in pc.warps:
            line(f"- {WARPS[wid].name} ({WARPS[wid].note})", 2)
    row += 1
    line("(press any key to return)")
    stdscr.refresh()
    stdscr.getch()


def _show_quests_curses(stdscr, game):
    from hollowreach.content.quests import QUESTS
    from hollowreach.core.rules import quests as qrules
    stdscr.erase()
    _safe_add(stdscr, 0, 0, "Quest Journal   (any key to return)")
    row = 2
    active = [(q, s) for q, s in game.pc.quests.items() if s["state"] == "active"]
    done = [q for q, s in game.pc.quests.items() if s["state"] == "done"]
    if not active and not done:
        _safe_add(stdscr, row, 2, "No quests — talk to the folk of Hearthvale.")
    for qid, _s in active:
        q = QUESTS[qid]
        cur, need = qrules.progress(game.pc, q)
        _safe_add(stdscr, row, 2, f"{q.title}  ({min(cur, need)}/{need})"); row += 1
        _safe_add(stdscr, row, 4, q.description); row += 1
    for qid in done:
        _safe_add(stdscr, row, 2, f"[done] {QUESTS[qid].title}"); row += 1
    stdscr.refresh()
    stdscr.getch()


def _shop_screen_curses(stdscr, game):
    from hollowreach.core.rules import shop
    mode = "buy"
    while True:
        stdscr.erase()
        if mode == "buy":
            rows = [(it, shop.buy_price(game.pc, it.base.price))
                    for it in game.shop_stock]
            _safe_add(stdscr, 0, 0, f"Bram's Wares — BUY   Gold: {game.pc.gold}"
                      "   (Tab: sell, Esc: leave)")
        else:
            rows = [(it, shop.sell_price(game.pc, it.base.price))
                    for _l, it in game.pc.inventory.listing()]
            _safe_add(stdscr, 0, 0, f"SELL your pack   Gold: {game.pc.gold}"
                      "   (Tab: buy, Esc: leave)")
        letters = "abcdefghijklmnopqrstuvwxyz"
        mapping = {}
        for i, (it, price) in enumerate(rows[:24]):
            mapping[letters[i]] = it
            _safe_add(stdscr, i + 2, 2,
                      f"{letters[i]}) {game.id_service.display_name(it)}  — {price} gold")
        if not rows:
            _safe_add(stdscr, 2, 2, "(nothing here)")
        stdscr.refresh()
        key = stdscr.getch()
        if key == 27:            # Esc
            return
        if key == 9:             # Tab
            mode = "sell" if mode == "buy" else "buy"
            continue
        try:
            ch = chr(key)
        except ValueError:
            continue
        it = mapping.get(ch)
        if it is not None:
            if mode == "buy":
                game.buy_item(it)
            else:
                game.sell_item(it)


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


def run_tiles(seed, blight_enabled: bool = True) -> int:
    """Launch the 2D pygame front-end (the default, windowed client)."""
    try:
        from hollowreach.ui.pygame_app import run_pygame
    except Exception as exc:  # pragma: no cover - env without pygame
        print(f"Tile UI unavailable ({exc}). Try --ascii or "
              f"'pip install pygame'.")
        return 1
    # A fixed --seed forces a reproducible run; otherwise each run rerolls.
    return run_pygame(seed if seed is not None else None,
                      blight_enabled=blight_enabled)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Hollowreach roguelike")
    parser.add_argument("--demo", nargs="?", const=200, type=int,
                        help="run a headless AI demo for N turns (default 200)")
    parser.add_argument("--ascii", action="store_true",
                        help="use the terminal (curses) client instead of tiles")
    parser.add_argument("--seed", type=int, default=None,
                        help="RNG seed for a reproducible run")
    parser.add_argument("--no-blight", action="store_true",
                        help="disable the Hollowing (Blight) pressure clock")
    args = parser.parse_args(argv)

    blight_enabled = not args.no_blight
    if args.demo is not None:
        return run_demo(args.seed if args.seed is not None else 1, args.demo,
                        blight_enabled=blight_enabled)
    if args.ascii:
        return run_interactive(args.seed if args.seed is not None else 1,
                               blight_enabled=blight_enabled)
    return run_tiles(args.seed, blight_enabled=blight_enabled)


if __name__ == "__main__":
    sys.exit(main())
