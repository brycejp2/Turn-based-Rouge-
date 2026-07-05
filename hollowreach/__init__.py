"""Hollowreach — an original turn-based roguelike.

A single-character, permadeath dungeon crawl in the corruption-haunted
valley of the Hollowreach.  The engine draws on the classic roguelike
tradition (energy/speed turns, DV/PV combat, procedural persistent
levels, a corruption clock and a divine economy); all world, names, lore
and content are original to this project.  See ``content/world.py`` for
the setting and ``docs/DESIGN_MECHANICS.md`` for the systems reference.

Package layout:

* ``hollowreach.core.engine``     — energy scheduler, RNG/dice
* ``hollowreach.core.model``      — Actor, Attributes, character assembly
* ``hollowreach.core.world``      — Level, tiles, field of view
* ``hollowreach.core.generation`` — random dungeon generators
* ``hollowreach.core.rules``      — combat, calendar, AI (more resolvers to come)
* ``hollowreach.content``         — data tables: world, ancestries, classes, omens, monsters
* ``hollowreach.ui``              — ASCII renderer + message log
* ``hollowreach.persistence``     — single-save permadeath service
"""

__version__ = "0.1.0"
GAME_TITLE = "Hollowreach"
