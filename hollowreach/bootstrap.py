"""Game construction shared by every front-end (ASCII, tiles, demo).

Keeps the wiring in one place so ``main.py`` and ``ui/pygame_app.py`` build
a run the same way without importing each other.
"""

from __future__ import annotations

from .core.engine.rng import Rng
from .core.model.character import build_player
from .game import Game

DEFAULT_ATTRS = {"St": 12, "Le": 11, "Wi": 11, "Dx": 13, "To": 13,
                 "Ch": 9, "Ap": 10, "Ma": 10, "Pe": 11}


def new_game(seed: int, name: str, race: str, cls: str, sign: str,
             gender: str, permadeath: bool = True,
             blight_enabled: bool = True) -> Game:
    rng = Rng(seed)
    pc = build_player(name, race, cls, sign, gender, dict(DEFAULT_ATTRS), rng)
    return Game.new(pc, rng, seed, permadeath=permadeath,
                    blight_enabled=blight_enabled)
