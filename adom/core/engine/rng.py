"""Seedable RNG and dice engine.

Implements the primitives called for in the design plan §3.2:

* A seedable random source so a run is reproducible from a seed.
* Standard dice notation ``XdY(+Z)`` via :func:`roll`.
* ``Rnd(n)`` == uniform ``1..n`` as used by the skill formulas (§6.2).
* ``M{a, b}`` == ``max(a, b)`` exposed as :func:`m` so damage/effect
  formulas can be transcribed from the wiki almost verbatim.

The class is deliberately tiny; every other subsystem takes an ``Rng``
instance rather than touching the global ``random`` module, which keeps
the whole game deterministic under a fixed seed.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

_DICE_RE = re.compile(
    r"^\s*(?P<count>\d+)\s*d\s*(?P<sides>\d+)\s*(?P<mod>[+-]\s*\d+)?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Dice:
    """A parsed ``XdY+Z`` expression."""

    count: int
    sides: int
    modifier: int = 0

    @classmethod
    def parse(cls, spec: "str | Dice") -> "Dice":
        if isinstance(spec, Dice):
            return spec
        match = _DICE_RE.match(spec)
        if not match:
            raise ValueError(f"Bad dice expression: {spec!r}")
        mod = match.group("mod")
        modifier = int(mod.replace(" ", "")) if mod else 0
        return cls(int(match.group("count")), int(match.group("sides")), modifier)

    @property
    def minimum(self) -> int:
        return self.count + self.modifier

    @property
    def maximum(self) -> int:
        return self.count * self.sides + self.modifier

    @property
    def average(self) -> float:
        return self.count * (self.sides + 1) / 2 + self.modifier

    def __str__(self) -> str:
        base = f"{self.count}d{self.sides}"
        if self.modifier > 0:
            return f"{base}+{self.modifier}"
        if self.modifier < 0:
            return f"{base}{self.modifier}"
        return base


class Rng:
    """Deterministic random source shared by every subsystem."""

    def __init__(self, seed: "int | None" = None):
        if seed is None:
            seed = random.SystemRandom().randint(0, 2**63 - 1)
        self.seed = seed
        self._random = random.Random(seed)

    # -- primitives -------------------------------------------------------
    def rnd(self, n: int) -> int:
        """Uniform integer in ``1..n`` (the wiki's ``Rnd(n)``)."""
        if n <= 0:
            return 0
        return self._random.randint(1, n)

    def randint(self, low: int, high: int) -> int:
        """Uniform integer in ``low..high`` inclusive."""
        return self._random.randint(low, high)

    def chance(self, percent: float) -> bool:
        """True with probability ``percent`` out of 100."""
        return self._random.random() * 100.0 < percent

    def one_in(self, n: int) -> bool:
        """True with probability ``1/n`` (n>=1)."""
        return n >= 1 and self._random.randint(1, n) == 1

    def choice(self, seq):
        return self._random.choice(seq)

    def shuffle(self, seq) -> None:
        self._random.shuffle(seq)

    def weighted_choice(self, items):
        """Pick from ``[(value, weight), ...]`` proportional to weight."""
        total = sum(weight for _, weight in items)
        if total <= 0:
            raise ValueError("weighted_choice needs positive total weight")
        pick = self._random.random() * total
        upto = 0.0
        for value, weight in items:
            upto += weight
            if pick < upto:
                return value
        return items[-1][0]

    # -- dice -------------------------------------------------------------
    def roll(self, spec: "str | Dice") -> int:
        """Roll ``XdY(+Z)`` and return the total."""
        dice = Dice.parse(spec)
        total = dice.modifier
        for _ in range(dice.count):
            total += self._random.randint(1, dice.sides)
        return total


def m(a: int, b: int) -> int:
    """``M{a, b}`` from the wiki formulas: the larger of two values."""
    return a if a > b else b
