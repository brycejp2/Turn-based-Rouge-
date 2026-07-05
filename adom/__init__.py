"""ADOM reimplementation — foundational engine slice.

Package layout mirrors the design plan's recommended module map (§17.1):

* ``adom.core.engine``     — energy scheduler, RNG/dice
* ``adom.core.model``      — Actor, Attributes, character assembly
* ``adom.core.world``      — Level, tiles, field of view
* ``adom.core.generation`` — random dungeon generators
* ``adom.core.rules``      — combat (spell/piety/corruption resolvers land here)
* ``adom.content``         — data tables (races, classes, star signs, monsters)
* ``adom.ui``              — ASCII renderer + message log
* ``adom.persistence``     — single-save permadeath service

See ``README.md`` for the mapping from plan sections to modules.
"""

__version__ = "0.1.0"
