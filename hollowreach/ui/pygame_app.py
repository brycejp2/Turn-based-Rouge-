"""2D tile front-end (pygame).

A graphical client over the same :class:`~hollowreach.game.Game` the ASCII
client drives — identical turn loop and command protocol, different
presentation and input.  Screens: a title, character creation, the tiled
play view (map viewport + stats panel + message log), overlays
(inventory, character sheet, item pickers), and win/death screens.

All ``draw_*`` helpers render onto a passed-in surface so frames can be
produced head-lessly (SDL dummy driver) for testing.
"""

from __future__ import annotations

import random

import pygame

from . import tiles
from .tiles import TileAtlas
from ..content.races import RACES, DEFAULT_RACE
from ..content.classes import CLASSES, DEFAULT_CLASS
from ..content.starsigns import STAR_SIGNS, DEFAULT_STAR_SIGN
from ..content.monsters import MONSTERS
from ..content import world

# -- layout ----------------------------------------------------------------
TILE = 24
VIEW_W, VIEW_H = 40, 21
PANEL_W = 300
LOG_H = 150
MAP_X, MAP_Y = 0, 0
MAP_PX = VIEW_W * TILE
WIN_W = MAP_PX + PANEL_W
WIN_H = VIEW_H * TILE + LOG_H


def _fonts():
    return {
        "big": pygame.font.Font(None, 56),
        "mid": pygame.font.Font(None, 32),
        "ui": pygame.font.Font(None, 22),
        "small": pygame.font.Font(None, 18),
    }


def text(surf, font, s, x, y, color=tiles.TEXT):
    surf.blit(font.render(s, True, color), (x, y))


def text_center(surf, font, s, cx, y, color=tiles.TEXT):
    img = font.render(s, True, color)
    surf.blit(img, img.get_rect(midtop=(cx, y)))


# ==========================================================================
# Play view
# ==========================================================================
def _monster_category(actor) -> str:
    mdef = MONSTERS.get(actor.monster_id)
    if mdef and mdef.types:
        return mdef.types[0]
    return "humanoid"


def draw_play(surf, fonts, atlas, game):
    surf.fill(tiles.BG)
    level = game.levels[game.depth]
    pc = game.pc.actor

    cam_x = max(0, min(pc.x - VIEW_W // 2, max(0, level.width - VIEW_W)))
    cam_y = max(0, min(pc.y - VIEW_H // 2, max(0, level.height - VIEW_H)))

    fog = pygame.Surface((TILE, TILE), pygame.SRCALPHA)
    fog.fill((6, 6, 10, 150))

    for sy in range(VIEW_H):
        for sx in range(VIEW_W):
            gx, gy = cam_x + sx, cam_y + sy
            if not level.in_bounds(gx, gy):
                continue
            visible = (gx, gy) in game.visible
            explored = level.explored[gy][gx]
            if not visible and not explored:
                continue
            px, py = MAP_X + sx * TILE, MAP_Y + sy * TILE
            surf.blit(atlas.terrain(level.tile(gx, gy)), (px, py))
            if visible:
                pile = level.items_at(gx, gy)
                if pile:
                    it = pile[-1]
                    surf.blit(atlas.item(it.glyph, it.category), (px, py))
            else:
                surf.blit(fog, (px, py))

    # Actors (only the currently visible ones).
    for actor in level.actors:
        if not actor.is_alive or actor.is_player:
            continue
        if (actor.x, actor.y) not in game.visible:
            continue
        if not (cam_x <= actor.x < cam_x + VIEW_W and cam_y <= actor.y < cam_y + VIEW_H):
            continue
        px = MAP_X + (actor.x - cam_x) * TILE
        py = MAP_Y + (actor.y - cam_y) * TILE
        if actor is level.boss:
            surf.blit(atlas.boss(actor.glyph), (px, py))
        else:
            surf.blit(atlas.creature(actor.glyph, _monster_category(actor)), (px, py))

    hx = MAP_X + (pc.x - cam_x) * TILE
    hy = MAP_Y + (pc.y - cam_y) * TILE
    surf.blit(atlas.hero(), (hx, hy))

    _draw_panel(surf, fonts, game)
    _draw_log(surf, fonts, game)


def _bar(surf, x, y, w, h, frac, color):
    frac = max(0.0, min(1.0, frac))
    pygame.draw.rect(surf, (30, 30, 38), (x, y, w, h), border_radius=3)
    if frac > 0:
        pygame.draw.rect(surf, color, (x, y, int(w * frac), h), border_radius=3)
    pygame.draw.rect(surf, tiles.PANEL_BORDER, (x, y, w, h), 1, border_radius=3)


def _draw_panel(surf, fonts, game):
    px = MAP_PX
    pygame.draw.rect(surf, tiles.PANEL, (px, 0, PANEL_W, WIN_H))
    pygame.draw.line(surf, tiles.PANEL_BORDER, (px, 0), (px, WIN_H), 1)
    pc, a = game.pc, game.pc.actor
    x = px + 14
    y = 12
    ui, small = fonts["ui"], fonts["small"]
    text(surf, fonts["mid"], a.name, x, y); y += 34
    text(surf, ui, f"Lv {a.char_level} {pc.race.name} {pc.cls.name}", x, y,
         tiles.TEXT_DIM); y += 26
    text(surf, ui, f"born under {pc.sign.name}", x, y, tiles.TEXT_DIM); y += 30

    text(surf, small, f"HP {a.hp}/{a.max_hp}", x, y, tiles.TEXT_WARN); y += 18
    _bar(surf, x, y, PANEL_W - 40, 10, a.hp / max(1, a.max_hp), (200, 60, 60)); y += 20
    text(surf, small, f"PP {a.pp}/{a.max_pp}", x, y, (120, 160, 220)); y += 18
    _bar(surf, x, y, PANEL_W - 40, 10, a.pp / max(1, a.max_pp), (70, 120, 210)); y += 26

    warps = len(pc.warps)
    from ..content.warps import MAX_WARPS
    text(surf, small, f"Hollowing: {warps}/{MAX_WARPS} warps", x, y,
         tiles.ACCENT); y += 18
    _bar(surf, x, y, PANEL_W - 40, 10, warps / MAX_WARPS, tiles.ACCENT); y += 28

    for label in (
        f"DV {a.dv}    PV {a.pv}",
        f"to-hit {a.melee_to_hit}   x{1 + a.extra_attacks} atk",
        f"speed {a.speed}   crit +{a.crit_bonus}%",
        f"weapon {a.weapon_dice}",
    ):
        text(surf, small, label, x, y); y += 20
    y += 6
    depth_note = "  (the Gate)" if game.levels[game.depth].is_final else ""
    text(surf, ui, f"Depth {game.depth}{depth_note}", x, y, tiles.TEXT); y += 26
    text(surf, small, game.calendar.describe(), x, y, tiles.TEXT_DIM); y += 26

    y = WIN_H - 60
    text(surf, small, "g get  i inv  C sheet  w wield", x, y, tiles.TEXT_DIM); y += 18
    text(surf, small, "q quaff  r read  T off  d drop", x, y, tiles.TEXT_DIM); y += 18
    text(surf, small, "> < stairs   . wait   Q quit", x, y, tiles.TEXT_DIM)


def _draw_log(surf, fonts, game):
    ly = VIEW_H * TILE
    pygame.draw.rect(surf, (16, 16, 21), (0, ly, MAP_PX, LOG_H))
    pygame.draw.line(surf, tiles.PANEL_BORDER, (0, ly), (MAP_PX, ly), 1)
    small = fonts["small"]
    lines = game.log.recent(6)
    yy = ly + 8
    for i, line in enumerate(lines):
        shade = tiles.TEXT if i >= len(lines) - 2 else tiles.TEXT_DIM
        text(surf, small, line[:88], 10, yy, shade)
        yy += 22


# ==========================================================================
# Overlays
# ==========================================================================
def _overlay_box(surf, fonts, title):
    box = pygame.Surface((WIN_W - 200, WIN_H - 120), pygame.SRCALPHA)
    box.fill((18, 18, 24, 245))
    pygame.draw.rect(box, tiles.PANEL_BORDER, box.get_rect(), 2)
    text(box, fonts["mid"], title, 20, 14)
    return box


def draw_inventory(surf, fonts, game):
    box = _overlay_box(surf, fonts, "Inventory")
    ui, small = fonts["ui"], fonts["small"]
    y = 60
    text(box, ui, "Worn:", 20, y); y += 26
    worn = game.pc.equipment.worn_items()
    if not worn:
        text(box, small, "(nothing)", 40, y, tiles.TEXT_DIM); y += 22
    for slot, it in worn:
        text(box, small, f"{slot:<7} {game.id_service.display_name(it)}", 40, y); y += 22
    y += 12
    text(box, ui, "Pack:", 20, y); y += 26
    if game.pc.inventory.is_empty():
        text(box, small, "(empty)", 40, y, tiles.TEXT_DIM); y += 22
    for letter, it in game.pc.inventory.listing():
        text(box, small, f"{letter})  {game.id_service.display_name(it)}", 40, y); y += 22
    text(box, small, "press any key to return", 20, box.get_height() - 28, tiles.TEXT_DIM)
    surf.blit(box, (100, 60))


def draw_character(surf, fonts, game):
    from ..core.model.attributes import ATTRIBUTE_KEYS
    from ..core.rules.proficiency import tier_name
    from ..content.warps import WARPS
    box = _overlay_box(surf, fonts, "Character")
    pc, a = game.pc, game.pc.actor
    ui, small = fonts["ui"], fonts["small"]
    y = 60
    text(box, ui, f"Level {a.char_level} {pc.race.name} {pc.cls.name} "
         f"— {pc.sign.name}", 20, y); y += 28
    attr = "   ".join(f"{k} {a.attributes.value(k)}" for k in ATTRIBUTE_KEYS)
    text(box, small, attr, 20, y); y += 26
    text(box, small, f"DV {a.dv}   PV {a.pv}   to-hit {a.melee_to_hit}   "
         f"attacks {1 + a.extra_attacks}   crit +{a.crit_bonus}%", 20, y); y += 28
    text(box, ui, "Proficiencies:", 20, y); y += 24
    profs = [(c, t) for c, t in pc.proficiencies.tier.items() if t > 0]
    text(box, small, ", ".join(f"{c} ({tier_name(t)})" for c, t in profs)
         or "(none trained)", 40, y); y += 26
    text(box, ui, "Skills:", 20, y); y += 24
    listing = sorted(pc.skills.items())
    for i in range(0, len(listing), 4):
        chunk = listing[i:i + 4]
        text(box, small, "   ".join(f"{n} {v}" for n, v in chunk), 40, y); y += 20
    if pc.warps:
        y += 8
        text(box, ui, "Warps:", 20, y); y += 24
        text(box, small, ", ".join(WARPS[w].name for w in pc.warps), 40, y)
    text(box, small, "press any key to return", 20, box.get_height() - 28, tiles.TEXT_DIM)
    surf.blit(box, (100, 60))


def draw_select(surf, fonts, entries, prompt):
    box = _overlay_box(surf, fonts, prompt)
    small = fonts["small"]
    y = 60
    if not entries:
        text(box, small, "(nothing suitable)", 20, y, tiles.TEXT_DIM)
    for letter, label in entries:
        text(box, small, f"{letter})  {label}", 30, y); y += 24
    text(box, small, "letter to choose, Esc to cancel", 20, box.get_height() - 28,
         tiles.TEXT_DIM)
    surf.blit(box, (100, 60))


def draw_title(surf, fonts, seed_note=""):
    surf.fill(tiles.BG)
    cx = WIN_W // 2
    pygame.draw.circle(surf, tiles.GATE_GLOW, (cx, 150), 46)
    pygame.draw.circle(surf, tiles.BG, (cx, 150), 30)
    text_center(surf, fonts["big"], world.GAME_TITLE, cx, 230, tiles.HERO)
    text_center(surf, fonts["ui"], world.TAGLINE, cx, 296, tiles.TEXT_DIM)
    text_center(surf, fonts["ui"], "Press ENTER to descend", cx, 400, tiles.TEXT)
    text_center(surf, fonts["small"], "Esc or Q to quit", cx, 436, tiles.TEXT_DIM)
    if seed_note:
        text_center(surf, fonts["small"], seed_note, cx, WIN_H - 30, tiles.TEXT_DIM)


def draw_create(surf, fonts, fields, sel, name):
    surf.fill(tiles.BG)
    cx = WIN_W // 2
    text_center(surf, fonts["mid"], "Create your hero", cx, 40)
    ui, small = fonts["ui"], fonts["small"]
    y = 130
    rows = [
        ("Name", name + ("_" if sel == 0 else "")),
        ("Ancestry", RACES[fields["race"]].name),
        ("Class", CLASSES[fields["cls"]].name),
        ("Omen", STAR_SIGNS[fields["sign"]].name),
        ("Gender", fields["gender"].title()),
    ]
    notes = [
        "type a name",
        ", ".join(RACES[fields["race"]].abilities[:2]) or "balanced",
        CLASSES[fields["cls"]].archetype,
        STAR_SIGNS[fields["sign"]].note,
        "",
    ]
    for i, (label, value) in enumerate(rows):
        color = tiles.HERO if i == sel else tiles.TEXT
        text(surf, ui, f"{label:>10}:", 340, y, tiles.TEXT_DIM)
        text(surf, ui, value, 500, y, color)
        if notes[i]:
            text(surf, small, notes[i], 760, y + 2, tiles.TEXT_DIM)
        y += 44
    text_center(surf, small,
                "Up/Down select field   Left/Right change   Enter begin   Esc back",
                cx, WIN_H - 60, tiles.TEXT_DIM)


def draw_gameover(surf, fonts, game):
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surf.blit(overlay, (0, 0))
    cx = WIN_W // 2
    if game.won:
        text_center(surf, fonts["big"], "YOU WIN", cx, 200, tiles.TEXT_GOOD)
        text_center(surf, fonts["ui"], "You sealed the Sundered Gate.", cx, 270)
    else:
        text_center(surf, fonts["big"], "YOU DIED", cx, 200, tiles.TEXT_WARN)
        text_center(surf, fonts["ui"],
                    f"Lost to the Depths at depth {game.depth}.", cx, 270,
                    tiles.TEXT_DIM)
    for i, line in enumerate(game.log.recent(3)):
        text_center(surf, fonts["small"], line[:70], cx, 320 + i * 22, tiles.TEXT_DIM)
    text_center(surf, fonts["ui"], "ENTER: new run     Q: quit", cx, 430, tiles.TEXT)


# ==========================================================================
# Input
# ==========================================================================
_MOVE = {
    pygame.K_h: "h", pygame.K_LEFT: "h", pygame.K_KP4: "h",
    pygame.K_l: "l", pygame.K_RIGHT: "l", pygame.K_KP6: "l",
    pygame.K_k: "k", pygame.K_UP: "k", pygame.K_KP8: "k",
    pygame.K_j: "j", pygame.K_DOWN: "j", pygame.K_KP2: "j",
    pygame.K_y: "y", pygame.K_KP7: "y",
    pygame.K_u: "u", pygame.K_KP9: "u",
    pygame.K_b: "b", pygame.K_KP1: "b",
    pygame.K_n: "n", pygame.K_KP3: "n",
    pygame.K_PERIOD: ".", pygame.K_KP5: ".",
}


def _translate(event):
    """Return (kind, value): 'cmd'/'overlay'/'select'/'quit'/None."""
    key = event.key
    uni = event.unicode
    # Stairs first: '>'/'<' share the period/comma keys.
    if uni == ">":
        return ("cmd", ">")
    if uni == "<":
        return ("cmd", "<")
    if key in _MOVE:
        return ("cmd", _MOVE[key])
    if key == pygame.K_g or uni == ",":
        return ("select", "get")
    if key == pygame.K_i:
        return ("overlay", "inventory")
    if key == pygame.K_c and (event.mod & pygame.KMOD_SHIFT):
        return ("overlay", "character")
    if key == pygame.K_c:
        return ("overlay", "character")
    if key == pygame.K_w:
        return ("select", "wield")
    if key == pygame.K_t:
        return ("select", "takeoff")
    if key == pygame.K_q and not (event.mod & pygame.KMOD_SHIFT):
        return ("select", "quaff")
    if key == pygame.K_r:
        return ("select", "read")
    if key == pygame.K_d:
        return ("select", "drop")
    if key == pygame.K_q and (event.mod & pygame.KMOD_SHIFT):
        return ("quit", None)
    return (None, None)


def _select_entries(game, verb):
    ids = game.id_service
    if verb == "quaff":
        items = game.pc.inventory.of_category({"potion"})
        return [(l, ids.display_name(it)) for l, it in items], items
    if verb == "read":
        items = game.pc.inventory.of_category({"scroll"})
        return [(l, ids.display_name(it)) for l, it in items], items
    if verb == "wield":
        items = [(l, it) for l, it in game.pc.inventory.listing() if it.slot]
        return [(l, ids.display_name(it)) for l, it in items], items
    if verb == "drop":
        items = game.pc.inventory.listing()
        return [(l, ids.display_name(it)) for l, it in items], items
    if verb == "takeoff":
        worn = game.pc.equipment.worn_items()
        letters = "abcdefghijklmnopqrstuvwxyz"
        entries = [(letters[i], f"{s}: {ids.display_name(it)}")
                   for i, (s, it) in enumerate(worn)]
        return entries, [(letters[i], s) for i, (s, _it) in enumerate(worn)]
    return [], []


def _run_command(game, command):
    def provide():
        return command
    game.run_turn(provide)


# ==========================================================================
# Top-level loop
# ==========================================================================
def run_pygame(seed: "int | None" = None, blight_enabled: bool = True) -> int:
    # Init only display + fonts (no audio yet) to stay quiet and lean.
    pygame.display.init()
    pygame.font.init()
    pygame.key.set_repeat(220, 60)
    pygame.display.set_caption(world.GAME_TITLE)
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    fonts = _fonts()
    atlas = TileAtlas(TILE)
    clock = pygame.time.Clock()

    from ..bootstrap import new_game

    while True:
        if not _title_loop(screen, fonts, clock):
            break
        params = _create_loop(screen, fonts, clock)
        if params is None:
            continue
        run_seed = seed if seed is not None else random.randint(1, 2**31)
        game = new_game(run_seed, params["name"], params["race"], params["cls"],
                        params["sign"], params["gender"],
                        blight_enabled=blight_enabled)
        if not _play_loop(screen, fonts, atlas, clock, game):
            break
    pygame.quit()
    return 0


def _title_loop(screen, fonts, clock) -> bool:
    while True:
        draw_title(screen, fonts)
        pygame.display.flip()
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True


def _create_loop(screen, fonts, clock):
    fields = {"race": DEFAULT_RACE, "cls": DEFAULT_CLASS,
              "sign": DEFAULT_STAR_SIGN, "gender": "male"}
    order = {"race": list(RACES), "cls": list(CLASSES),
             "sign": list(STAR_SIGNS), "gender": ["male", "female"]}
    keymap = {1: "race", 2: "cls", 3: "sign", 4: "gender"}
    sel = 0
    name = "Kael"
    while True:
        draw_create(screen, fonts, fields, sel, name)
        pygame.display.flip()
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return None
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return {"name": name or "Kael", "race": fields["race"],
                        "cls": fields["cls"], "sign": fields["sign"],
                        "gender": fields["gender"]}
            if event.key == pygame.K_UP:
                sel = (sel - 1) % 5
            elif event.key == pygame.K_DOWN:
                sel = (sel + 1) % 5
            elif event.key in (pygame.K_LEFT, pygame.K_RIGHT) and sel in keymap:
                field = keymap[sel]
                opts = order[field]
                i = opts.index(fields[field])
                i = (i + (1 if event.key == pygame.K_RIGHT else -1)) % len(opts)
                fields[field] = opts[i]
            elif sel == 0:
                if event.key == pygame.K_BACKSPACE:
                    name = name[:-1]
                elif event.unicode and event.unicode.isprintable() and len(name) < 16:
                    name += event.unicode


def _play_loop(screen, fonts, atlas, clock, game) -> bool:
    """Returns True to return to the title, False to quit the program."""
    while True:
        ended = game.won or not game.pc.actor.is_alive or not game.running
        if ended:
            draw_play(screen, fonts, atlas, game)
            draw_gameover(screen, fonts, game)
            pygame.display.flip()
            clock.tick(30)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        return False
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        return True
            continue

        draw_play(screen, fonts, atlas, game)
        pygame.display.flip()
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type != pygame.KEYDOWN:
                continue
            kind, value = _translate(event)
            if kind == "quit":
                return False
            if kind == "cmd":
                _run_command(game, value)
            elif kind == "overlay":
                _show_overlay(screen, fonts, atlas, clock, game, value)
            elif kind == "select":
                _handle_select(screen, fonts, atlas, clock, game, value)


def _show_overlay(screen, fonts, atlas, clock, game, which):
    draw_play(screen, fonts, atlas, game)
    if which == "inventory":
        draw_inventory(screen, fonts, game)
    else:
        draw_character(screen, fonts, game)
    pygame.display.flip()
    _wait_key(clock)


def _handle_select(screen, fonts, atlas, clock, game, verb):
    if verb == "get":
        _run_command(game, ("pickup", None))
        return
    entries, items = _select_entries(game, verb)
    prompts = {"quaff": "Quaff which potion?", "read": "Read which scroll?",
               "wield": "Wield/wear what?", "drop": "Drop what?",
               "takeoff": "Take off what?"}
    draw_play(screen, fonts, atlas, game)
    draw_select(screen, fonts, entries, prompts[verb])
    pygame.display.flip()
    chosen = _wait_letter(clock, [l for l, _ in entries])
    if chosen is None:
        return
    payload = dict(items).get(chosen)
    verb_cmd = {"quaff": "quaff", "read": "read", "wield": "equip",
                "drop": "drop", "takeoff": "unequip"}[verb]
    _run_command(game, (verb_cmd, payload))


def _wait_key(clock):
    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                return


def _wait_letter(clock, letters):
    while True:
        clock.tick(30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.unicode in letters:
                    return event.unicode
