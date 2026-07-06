# Hollowreach

> Descend into the Hollow. Seal the rift — or be unmade by it.

**Hollowreach** is an original single-character, turn-based roguelike with
permadeath and procedural generation. You descend into *the Sundered
Depths* beneath the corruption-haunted valley of **the Hollowreach**,
racing a spreading blight — *the Hollowing* — to reach and seal *the
Sundered Gate* before it claims you.

It's built on a classic-roguelike engine (energy/speed turns, DV/PV
combat, persistent procedural levels, the Hollowing's creeping Blight
clock and a divine economy). The **mechanics** come from the roguelike tradition;
the **world, names, story and content are all original** to this project
and live in [`hollowreach/content/`](hollowreach/content/) — see
[`world.py`](hollowreach/content/world.py). The systems reference in
[`docs/DESIGN_MECHANICS.md`](docs/DESIGN_MECHANICS.md) is an internal
design document, not shipped content.

> Status: **playable vertical slice** — a complete, winnable game loop
> with a 2D tile client that packages to a Windows `.exe`. The roadmap
> below tracks the path to a shippable product. The engine, ASCII client
> and tests are pure-stdlib **Python 3**; only the tile client needs
> `pygame`.

## Quick start

```bash
pip install -r requirements.txt   # pygame, for the 2D tile client

# Play — 2D tile client (title screen, character creation, mouse-free):
python3 main.py

# Play in the terminal instead (ASCII/curses):
python3 main.py --ascii

# Headless AI demo — exercises the whole stack, good for CI:
python3 main.py --demo 400 --seed 7

# Run the test suite (stdlib unittest, no pytest required):
python3 -m unittest discover -s tests -v
```

In-game keys: arrows or `hjkl`/`yubn` move/attack, `>`/`<` stairs, `g` get,
`i` inventory, `C` character, `w` wield/wear, `T` take off, `q` quaff,
`r` read, `d` drop, `.` wait, `Q` quit.

### Play on Windows without Python — download the `.exe`

Hollowreach builds to a single self-contained **`Hollowreach.exe`** (no
Python install needed to play). See [`packaging/`](packaging/README.md) —
on Windows just run `packaging\build_windows.bat` and you get
`dist\Hollowreach.exe`. The terminal client (`--ascii`) needs
`pip install windows-curses`; the tile client does not.

Save files live in `%USERPROFILE%\.hollowreach_saves\` (override with the
`HOLLOWREACH_SAVE_DIR` environment variable).

## What's implemented today

- **Energy/speed turn system** — a min-heap scheduler keyed on each
  actor's next-action time (not a fixed round loop); a speed-200 actor
  acts twice as often as speed-100, verified by a unit test.
- **Combat** — `DV = trunc((Dx-12)/2) + trunc((Dx-9)/2)` plus
  Dodge/Alertness/tactics/armour; `PV = trunc((To-18)/2)` capped +20 plus
  armour, Dwarven stoneskin and a Blessed bonus; to-hit vs DV, PV soak
  with a ≥1 floor, and criticals.
- **Characters** — nine attributes (base/potential/modified, 1–99);
  Toughness drives max HP, Mana drives max PP; playable ancestries with
  attribute mods, XP multipliers and traits; twelve birth **omens** (e.g.
  The Hawk +10 speed, The Bastion +PV/To/Wi); XP scaled
  by relative speed; per-character monster memory.
- **Build variety** — the systems that make two heroes play differently:
  - **Weapon proficiencies** (marks): each weapon category (sword, axe,
    blunt, spear, dagger, unarmed) trains as you fight with it, climbing
    tiers (basic → master → mythic) for cumulative to-hit/damage/DV and
    **extra attacks per turn**. Mark gain scales with class and the Blade
    omen, so a Fighter masters a blade far faster than a Wizard.
  - **Class powers** at levels 6/12/18/25+: passive, per-level and
    one-time gifts that define each class (Fighter's Flurry extra attack,
    Barbarian's speed & savage blows, Monk's precise strikes, Healer's
    recovery, Priest's discerning eye…).
  - **Skills** that advance on level-up and through use, wired into the
    math: Athletics → speed, Dodge/Alertness → DV, Find Weakness → crit.
  - **Natural regeneration** driven by ancestry, the Healing skill, the
    Beacon omen and Healer powers.
  - A **character screen** (`C`) shows attributes, proficiencies, skills,
    combat stats and active Warps.
- **The Hollowing (Blight clock)** — the signature pressure mechanic.
  In the deep places hidden **Blight** accrues every turn at a rate that
  climbs with depth; cross a threshold and the Hollowing inflicts a
  **Warp** — an original mutation with jagged upsides and real costs
  (ashen skin, hollow eyes, voidsight, leaden bones…). Hold too many and
  you're *claimed by the Hollowing* — a nonstandard game over. Because
  Blight only builds while you linger, grinding is self-defeating: the
  clock always pushes you forward. The Warden omen and high Appearance
  slow it; the rare potion of cleansing sheds it; a difficulty flag
  (`--no-blight`) turns it off.
- **Items & equipment** — weapons, armour, potions and scrolls with
  hidden **BUC** (blessed/uncursed/cursed, cursed gear welds on),
  enchantment levels, a letter-indexed inventory with stacking and
  Strength-based carry weight, and eleven equip slots that fold into the
  combat math. **Identification**: potions/scrolls are disguised behind
  per-run appearances until use-identified or read via a scroll of
  identify. Working consumables — healing, gain attributes, enchant
  weapon/armour, remove curse, magic mapping, teleport, and more.
- **A complete, winnable loop** — descend the Sundered Depths to the
  bottom (depth 15), where the **Sundered Gate** is guarded by the unique
  boss **Vurgast the Unmade**. Defeat him and step to the Gate to **seal
  it and win**; the Gate rejects you while the guardian lives. The
  descent is balanced so a strong, focused run reaches the bottom with a
  handful of Warps to spare — but dawdling lets the Hollowing claim you
  first. Verified end-to-end: a built hero descends all 15 levels, slays
  Vurgast and wins. Deeper corrupting foes (wraiths, hollowed husks, and
  Vurgast) feed the Hollowing when they land a blow.
- **World** — persistent procedural levels keyed to depth, fog-of-war,
  recursive-shadowcasting field of view; loot scattered by depth; a
  360-day / 12-month calendar with day/night sight range.
- **Permadeath** — one canonical save, deleted on load, erased on death
  (and on victory — the run is complete), all behind a single toggle.
- **2D tile client + packaging** — a pygame front-end with a title
  screen, character creation, a tiled play view (map viewport + stats
  panel with HP/PP/Hollowing bars + message log), inventory/character
  overlays, item pickers, and win/death screens. All tile art is drawn
  procedurally in code — no external assets. Builds to a single
  self-contained **`Hollowreach.exe`** via PyInstaller
  ([`packaging/`](packaging/README.md)).

## Architecture

```
hollowreach/
  core/engine/      energy scheduler, seedable RNG + dice
  core/model/       Actor, Attributes, character assembly, monster memory,
                    Item, Inventory, Equipment
  core/world/       Level (persistent grid + fog), tiles, FOV
  core/generation/  random dungeon generators, loot rolls
  core/rules/       combat, AI, calendar, identification, consumables, blight,
                    proficiency, class powers, skills, regen
  content/          world.py + data tables: ancestries, classes, omens, monsters, items, warps
  ui/               ASCII renderer, 2D tile client (pygame_app + procedural tiles)
  persistence/      single-save permadeath service
  bootstrap.py      shared game construction
main.py             entry point (tiles / --ascii / --demo)
packaging/          PyInstaller spec + build scripts (-> Hollowreach.exe)
tests/              93 unittest tests
docs/               DESIGN_MECHANICS.md (internal systems reference)
```

New content is data in `content/`; new systems are resolvers in
`core/rules/` that subscribe to the same turn scheduler.

## Roadmap to a shippable product

**Game depth**
1. ~~Inventory, equip slots, BUC status, identification, items/potions/scrolls~~ ✅ **done**
2. ~~Skills + weapon proficiencies + the full class-power system~~ ✅ **done**
3. Magic (PP, spell knowledge/power, spell list) + mind powers
4. Overworld, towns/NPCs, shops, quests
5. Altars / piety / alignment / prayer / crowning (the divine economy)
6. ~~The corruption clock + mutation table + cures~~ ✅ **done** (the Hollowing / Blight)
7. ~~The Sundered Depths spine, the boss, and the standard ending~~ ✅ **done** (winnable!)
8. Remaining ancestries/classes/monsters/artifacts + alternate endings

**Productization** (chosen direction: original IP, 2D tile graphics)
- Title screen & character creation ✅ done; save-slot menu, options, audio still to do
- ~~A 2D tile render layer over the existing ASCII model~~ ✅ **done** (pygame)
- ~~One-click Windows build (packaged `.exe`)~~ ✅ **done** (PyInstaller)
- Steam release: Steamworks (achievements, cloud saves), store page,
  the $100 Steam Direct fee

## Testing

`python3 -m unittest discover -s tests` runs 93 tests covering the dice
engine, the energy-scheduler invariant, attribute clamping/potentials,
DV/PV/combat formulas, character assembly, calendar/lighting, FOV, level
connectivity & determinism, permadeath save consumption, the item system
(BUC, inventory/equipment, identification, consumables), and the Blight
clock (accrual, Warp application/reversal, cures, the consumed end-state).

## Licensing / IP

All code and the Hollowreach setting are original to this project. The
document under `docs/` analyses another game's *mechanics* for design
reference only; none of that game's named content ships here. Game
mechanics are not copyrightable; the roguelike genre is built on shared
systems.
