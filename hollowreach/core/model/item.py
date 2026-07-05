"""Items: definitions, instances, and BUC status.

Split into two layers:

* :class:`ItemBase` — the immutable *definition* of an item type (a long
  sword, a potion of healing).  These live in ``content/items.py``.
* :class:`Item` — a concrete *instance* carried in the world, with its
  own hidden **BUC** (Blessed / Uncursed / Cursed), enchantment level,
  quantity and identification state.

Every instance rolls BUC at generation (10% blessed, 10% cursed).  Cursed
gear welds on when equipped and can't be removed; blessed gear is
stronger.  Weapon/armour *types* are visible on sight, but their
enchantment and BUC stay hidden until identified; potions and scrolls are
fully disguised behind a random per-game appearance (see
``core/rules/identification.py``).
"""

from __future__ import annotations

from dataclasses import dataclass

# -- BUC ---------------------------------------------------------------------
BLESSED = "blessed"
UNCURSED = "uncursed"
CURSED = "cursed"
BUC_BONUS = {BLESSED: 1, UNCURSED: 0, CURSED: -1}

# -- equip slots -------------------------------------------------------------
SLOT_WEAPON = "weapon"
SLOT_BODY = "body"
SLOT_SHIELD = "shield"
SLOT_HEAD = "head"
SLOT_CLOAK = "cloak"
SLOT_HANDS = "hands"
SLOT_GIRDLE = "girdle"
SLOT_BOOTS = "boots"
SLOT_NECK = "neck"
SLOT_RING = "ring"

# Categories whose appearance is disguised until identified.
APPEARANCE_CATEGORIES = {"potion", "scroll", "ring"}
# Categories consumed on use.
CONSUMABLE_CATEGORIES = {"potion", "scroll", "food"}


@dataclass(frozen=True)
class ItemBase:
    id: str
    name: str                 # real name, e.g. "long sword"
    category: str             # weapon | body_armor | shield | potion | scroll | ...
    glyph: str
    weight: int = 10
    slot: "str | None" = None
    dv: int = 0               # defensive value contribution
    pv: int = 0               # protection value contribution
    dmg_dice: str = "1d3"     # melee damage (weapons)
    to_hit: int = 0           # weapon accuracy bonus
    two_handed: bool = False
    stackable: bool = False
    price: int = 0
    effect: "str | None" = None   # consumable effect id
    plural: "str | None" = None

    def pluralized(self) -> str:
        if self.plural:
            return self.plural
        return self.name + "s"


@dataclass
class Item:
    base: ItemBase
    buc: str = UNCURSED
    enchant: int = 0
    quantity: int = 1
    identified: bool = False
    buc_known: bool = False

    # -- passthrough accessors -------------------------------------------
    @property
    def category(self) -> str:
        return self.base.category

    @property
    def slot(self) -> "str | None":
        return self.base.slot

    @property
    def glyph(self) -> str:
        return self.base.glyph

    @property
    def weight(self) -> int:
        return self.base.weight * self.quantity

    @property
    def name(self) -> str:
        return self.base.name

    # -- effective combat contribution (folds in enchant + BUC) ----------
    @property
    def buc_mod(self) -> int:
        return BUC_BONUS[self.buc]

    @property
    def dv_bonus(self) -> int:
        """DV contribution when worn (shields/parry weapons carry DV)."""
        if self.base.dv >= self.base.pv and (self.base.dv or self.base.pv):
            return self.base.dv + self.enchant + self.buc_mod
        return self.base.dv

    @property
    def pv_bonus(self) -> int:
        """PV contribution when worn (armour carries PV)."""
        if self.base.pv > self.base.dv:
            return self.base.pv + self.enchant + self.buc_mod
        return self.base.pv

    @property
    def weapon_bonus(self) -> int:
        """Flat to-hit / damage bonus a wielded weapon grants."""
        return self.enchant + self.buc_mod

    # -- stacking --------------------------------------------------------
    def can_stack_with(self, other: "Item") -> bool:
        return (
            self.base.stackable
            and other.base.id == self.base.id
            and self.buc == other.buc
            and self.enchant == other.enchant
            and self.identified == other.identified
            and self.buc_known == other.buc_known
        )

    def split(self, count: int) -> "Item":
        """Peel ``count`` off a stack into a new Item."""
        count = max(1, min(count, self.quantity))
        self.quantity -= count
        clone = Item(self.base, self.buc, self.enchant, count,
                     self.identified, self.buc_known)
        return clone

    def reveal(self) -> None:
        self.identified = True
        self.buc_known = True

    def enchant_bracket(self) -> str:
        """``[+dv, +pv]`` / ``(+hit, +dmg)`` shown once identified."""
        cat = self.base.category
        if cat in ("weapon",):
            b = self.weapon_bonus
            return f"({b:+d}, {b:+d})"
        if cat in ("body_armor", "shield", "helmet", "boots", "cloak",
                   "gauntlets", "girdle"):
            return f"[{self.dv_bonus:+d}, {self.pv_bonus:+d}]"
        return ""
