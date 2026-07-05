# Hollowreach

> Descend into the Hollow. Seal the rift — or be unmade by it.

**Hollowreach** is an original single-character, turn-based roguelike with
permadeath and procedural generation. You descend into *the Sundered
Depths* beneath the corruption-haunted valley of **the Hollowreach**,
racing a spreading blight — *the Hollowing* — to reach and seal *the
Sundered Gate* before it claims you.

It's built on a classic-roguelike engine (energy/speed turns, DV/PV
combat, persistent procedural levels, an approaching corruption clock and
a divine economy). The **mechanics** come from the roguelike tradition;
the **world, names, story and content are all original** to this project
and live in [`hollowreach/content/`](hollowreach/content/) — see
[`world.py`](hollowreach/content/world.py). The systems reference in
[`docs/DESIGN_MECHANICS.md`](docs/DESIGN_MECHANICS.md) is an internal
design document, not shipped content.

> Status: **early foundation** (engine + core systems). This is the base
> a commercial release is built on; the roadmap below tracks the path to a
> shippable product. Implemented in dependency-free **Python 3**.

## Quick start

```bash
# Play (interactive; needs a terminal — on Windows: pip install windows-curses):
python3 main.py

# Headless AI demo — exercises the whole stack, good for CI:
python3 main.py --demo 400 --seed 7

# Run the test suite (stdlib unittest, no pytest required):
python3 -m unittest discover -s tests -v
```

In-game keys: `hjkl` + `yubn` move/attack, `>`/`<` stairs, `.` wait, `Q` quit.

### Windows 11

The demo and tests run on a stock Python install. The interactive game
uses `curses`, which isn't bundled on Windows — install the drop-in:

```powershell
pip install windows-curses
python main.py
```

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
  The Hawk +10 speed, The Bastion +PV/To/Wi); starting skills; XP scaled
  by relative speed; per-character monster memory.
- **World** — persistent procedural levels keyed to depth, fog-of-war,
  recursive-shadowcasting field of view; a 360-day / 12-month calendar
  with day/night sight range.
- **Permadeath** — one canonical save, deleted on load, erased on death,
  all behind a single toggle.

## Architecture

```
hollowreach/
  core/engine/      energy scheduler, seedable RNG + dice
  core/model/       Actor, Attributes, character assembly, monster memory
  core/world/       Level (persistent grid + fog), tiles, FOV
  core/generation/  random dungeon generators (DL-keyed spawns/features)
  core/rules/       combat, calendar/lighting, monster AI
  content/          world.py + data tables: ancestries, classes, omens, monsters
  ui/               ASCII renderer + message log
  persistence/      single-save permadeath service
main.py             entry point (interactive + headless demo)
tests/              37 unittest tests
docs/               DESIGN_MECHANICS.md (internal systems reference)
```

New content is data in `content/`; new systems are resolvers in
`core/rules/` that subscribe to the same turn scheduler.

## Roadmap to a shippable product

**Game depth**
1. Inventory, equip slots, BUC status, identification, items/potions/scrolls
2. Skills + weapon proficiencies + the full class-power system
3. Magic (PP, spell knowledge/power, spell list) + mind powers
4. Overworld, towns/NPCs, shops, quests
5. Altars / piety / alignment / prayer / crowning (the divine economy)
6. The corruption clock + mutation table + cures
7. The Sundered Depths spine, the boss, and the standard ending
8. Remaining ancestries/classes/monsters/artifacts + alternate endings

**Productization** (chosen direction: original IP, 2D tile graphics)
- Title screen, save-slot menu, options/settings, audio
- A 2D tile render layer over the existing ASCII model
- One-click Windows build (packaged `.exe`)
- Steam release: Steamworks (achievements, cloud saves), store page,
  the $100 Steam Direct fee

## Testing

`python3 -m unittest discover -s tests` runs 37 tests covering the dice
engine, the energy-scheduler invariant, attribute clamping/potentials,
DV/PV/combat formulas, character assembly, calendar/lighting, FOV, level
connectivity & determinism, and permadeath save consumption.

## Licensing / IP

All code and the Hollowreach setting are original to this project. The
document under `docs/` analyses another game's *mechanics* for design
reference only; none of that game's named content ships here. Game
mechanics are not copyrightable; the roguelike genre is built on shared
systems.
