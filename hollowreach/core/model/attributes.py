"""The nine attributes and their book-keeping (design plan §5.1).

Attributes: Strength, Learning, Willpower, Dexterity, Toughness,
Charisma, Appearance, Mana, Perception.

Each attribute tracks three numbers:

* **base** — the trained value (raised/lowered by herbs, training, abuse).
* **potential** — a hidden hard cap for *training* (boosts may exceed it).
* **modifiers** — a running sum of semi-permanent effects (equipment,
  corruptions, the orc daylight penalty, temporary boosts).

The **modified / total** value the rest of the game reads is
``base + modifiers`` clamped to the ``1..99`` range.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Canonical order used everywhere (char sheet, save files, point-buy).
ATTRIBUTE_KEYS = ["St", "Le", "Wi", "Dx", "To", "Ch", "Ap", "Ma", "Pe"]

ATTRIBUTE_NAMES = {
    "St": "Strength",
    "Le": "Learning",
    "Wi": "Willpower",
    "Dx": "Dexterity",
    "To": "Toughness",
    "Ch": "Charisma",
    "Ap": "Appearance",
    "Ma": "Mana",
    "Pe": "Perception",
}

MIN_VALUE = 1
MAX_VALUE = 99


@dataclass
class Attribute:
    key: str
    base: int
    potential: int
    modifier: int = 0

    @property
    def value(self) -> int:
        """Modified/total value, clamped to 1..99 (§5.1)."""
        return max(MIN_VALUE, min(MAX_VALUE, self.base + self.modifier))

    def train(self, amount: int = 1) -> bool:
        """Raise the base toward potential. Returns True if it moved."""
        target = min(self.base + amount, self.potential)
        if target > self.base:
            self.base = target
            return True
        return False

    def drain(self, amount: int = 1) -> None:
        """Lower the base value (stat-drain attacks, abuse)."""
        self.base = max(MIN_VALUE, self.base - amount)


class Attributes:
    """The full set of nine, keyed by two-letter code."""

    def __init__(self, values: "dict[str, int]", potentials: "dict[str, int] | None" = None):
        potentials = potentials or {}
        self._attrs: dict[str, Attribute] = {}
        for key in ATTRIBUTE_KEYS:
            base = values.get(key, 10)
            pot = potentials.get(key, base)
            self._attrs[key] = Attribute(key, base, max(pot, base))

    def __getitem__(self, key: str) -> Attribute:
        return self._attrs[key]

    def value(self, key: str) -> int:
        return self._attrs[key].value

    def apply_modifier(self, key: str, delta: int) -> None:
        self._attrs[key].modifier += delta

    def clear_modifiers(self) -> None:
        for attr in self._attrs.values():
            attr.modifier = 0

    # Convenience accessors used throughout the rules code.
    @property
    def St(self) -> int: return self.value("St")
    @property
    def Le(self) -> int: return self.value("Le")
    @property
    def Wi(self) -> int: return self.value("Wi")
    @property
    def Dx(self) -> int: return self.value("Dx")
    @property
    def To(self) -> int: return self.value("To")
    @property
    def Ch(self) -> int: return self.value("Ch")
    @property
    def Ap(self) -> int: return self.value("Ap")
    @property
    def Ma(self) -> int: return self.value("Ma")
    @property
    def Pe(self) -> int: return self.value("Pe")

    def as_dict(self) -> "dict[str, int]":
        return {key: attr.value for key, attr in self._attrs.items()}

    def to_save(self) -> dict:
        return {
            key: {"base": a.base, "potential": a.potential}
            for key, a in self._attrs.items()
        }

    @classmethod
    def from_save(cls, data: dict) -> "Attributes":
        values = {k: v["base"] for k, v in data.items()}
        pots = {k: v["potential"] for k, v in data.items()}
        return cls(values, pots)
