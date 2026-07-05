# ADOM — Turn-Based Roguelike

A ground-up reconstruction of *Ancient Domains of Mystery*, following the
[full design plan](ADOM_Full_Design_Plan.md).  This repository currently
implements the plan's **foundational engine slice** (§17.4 milestones 1–2,
plus scaffolding for 3+): the signature energy/speed turn model, the
character model with ADOM's actual formulas, procedural levels, combat,
field of view, an Ancardian calendar, and single-save permadeath.

The plan is huge (12 races × 22 classes, ~600 monsters, ~50 artifacts,
the Caverns of Chaos, the corruption clock, the divine economy…).  This
codebase is built as an **engine + data tables** so the remaining content
is poured in as data, not new code — exactly the approach §18 prescribes.

> The design plan is `.NET`-oriented; this implementation is in **Python
> 3** (no third-party dependencies) for portability and so it runs and
> tests anywhere.  The module layout and every formula follow the plan.

## Quick start

```bash
# Play (interactive, needs a terminal with curses):
python3 main.py

# Headless AI demo — exercises the whole stack, good for CI:
python3 main.py --demo 400 --seed 7

# Run the test suite (stdlib unittest, no pytest required):
python3 -m unittest discover -s tests -v
```

In-game keys: `hjkl` + `yubn` to move/attack, `>`/`<` for stairs,
`.` to wait, `Q` to quit.

## Architecture → design-plan mapping

The package layout mirrors the plan's recommended module map (§17.1):

| Module | Plan § | Responsibility |
|---|---|---|
| `adom/core/engine/rng.py` | §3.2 | Seedable RNG, `XdY+Z` dice, `Rnd(n)`, `M{a,b}` |
| `adom/core/engine/scheduler.py` | §3.1 | **Energy/speed scheduler** — min-heap keyed on next-action time (not round-based) |
| `adom/core/model/attributes.py` | §5.1 | The 9 attributes: base / potential / modified, clamp 1–99 |
| `adom/core/model/actor.py` | §5, §7.2 | Actor (PC & monsters); **DV**, **PV**, to-hit, HP/PP formulas |
| `adom/core/model/character.py` | §5–6, §3.4 | Race/class/star-sign assembly, XP & leveling, monster memory |
| `adom/core/world/tile.py` | §4.3 | Tile types incl. altars / forges / herb bushes |
| `adom/core/world/level.py` | §4.3 | Persistent level: grid, fog-of-war, occupants, item piles |
| `adom/core/world/fov.py` | §4.1 | Recursive-shadowcasting field of view |
| `adom/core/generation/dungeon.py` | §4.3 | Random rooms-and-corridors levels, DL-keyed spawns |
| `adom/core/rules/combat.py` | §7.1 | Melee resolution: to-hit vs DV, PV soak, criticals |
| `adom/core/rules/calendar.py` | §4.1–4.2 | Ancardian calendar + time-of-day sight radius |
| `adom/core/rules/ai.py` | §12 | Monster turn logic (chase / attack / wander) |
| `adom/content/*.py` | §5.2–5.4, §12, §18 | Data tables: races, classes, star signs, monsters |
| `adom/ui/render.py` | §17.1 | ASCII renderer + message log |
| `adom/persistence/save.py` | §3.3, §5.7 | **Single-save permadeath** service behind a flag |
| `adom/game.py` | §3.1, §17.3 | Turn loop wiring subsystems onto the scheduler |

## What faithfully models ADOM today

- **Energy/speed system (§3.1).** Actors accrue energy by `speed`; a
  standard action costs 1000 EP.  A speed-200 actor acts twice as often
  as speed-100 — verified by a unit test.  No fixed round loop.
- **Combat formulas (§7.2).** `DV = trunc((Dx-12)/2) + trunc((Dx-9)/2)`
  plus Dodge/Alertness/tactics/armour and the Monk unarmed bonus;
  `PV = trunc((To-18)/2)` capped +20, plus armour, Dwarven Mithril-Skin
  +3, and the Blessed bonus.  A hit always deals ≥1 after PV soak.
- **Character model (§5).** 9 attributes with base/potential/modified;
  Toughness drives max HP, Mana drives max PP; race attribute mods &
  potentials, XP multipliers (Troll ×2.5…), star-sign effects (Raven
  +10 speed, Tree +PV/To/Wi, Candle regen…), universal + race + class
  starting skills.
- **World (§4).** Persistent procedural levels keyed to dungeon level;
  fog-of-war; recursive-shadowcasting FOV; the 360-day / 12-month
  Ancardian calendar starting in the Unicorn, with day/night sight.
- **Progression (§6).** XP scaled by relative speed and the Learning
  bonus; level-ups raise HP/PP; per-character monster memory (§3.4).
- **Permadeath (§3.3).** One canonical save, deleted on load, erased on
  death — all gated behind a single `permadeath` flag (§5.7).

## Roadmap (remaining plan milestones, §17.4)

3. Inventory, BUC, equip slots, identification, items/potions/scrolls (§11)
4. Skills + weapon marks + full class-power system (§6.2–6.3)
5. Magic: PP, spell knowledge/power, spell list + mindcraft (§8)
6. Overworld graph, towns/NPCs, shops, quests (§4.4, §13, §14)
7. Altars / piety / alignment / prayer / crowning (§10)
8. Corruption clock + corruption table + removal (§9)
9. Caverns of Chaos spine + the five Orbs + Gate + standard ending (§13.4, §14–15)
10. Remaining races/classes/monsters/artifacts/zones + ultra endings

Each is additive: new data in `adom/content/` and new resolvers in
`adom/core/rules/`, subscribing to the same turn scheduler (§17.3).

## Testing

`python3 -m unittest discover -s tests` runs 37 tests covering the dice
engine, the energy scheduler invariant, attribute clamping/potentials,
DV/PV/combat formulas, character assembly, calendar/lighting, FOV,
level connectivity & determinism, and permadeath save consumption.
