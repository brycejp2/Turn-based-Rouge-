"""Identification service and item naming (design ref §11.2, §11.4).

At the start of a run each potion and scroll type is assigned a random
**appearance** (a "fizzy potion", a scroll labelled "VROOMBA").  The
player sees only that until the type is identified — by using one
(use-ID), reading a scroll of identify, or other means.  Identifying one
item reveals *every* item of that type for the rest of the run.

Weapons and armour show their *type* immediately but hide enchantment and
BUC until identified.  This service owns both the disguise map and the
canonical display-name logic so the UI and message log stay consistent.
"""

from __future__ import annotations

from ..model.item import (
    Item, ItemBase, APPEARANCE_CATEGORIES, BLESSED, CURSED, UNCURSED,
)
from ...content.items import (
    ITEMS, POTION_APPEARANCES, SCROLL_LABELS,
)


class IdentificationService:
    def __init__(self, rng):
        self._appearance: dict[str, str] = {}
        self._identified: set[str] = set()
        self._assign_potions(rng)
        self._assign_scrolls(rng)

    def _assign_potions(self, rng) -> None:
        pots = [b.id for b in ITEMS.values() if b.category == "potion"]
        looks = list(POTION_APPEARANCES)
        rng.shuffle(looks)
        for base_id, look in zip(pots, looks):
            self._appearance[base_id] = f"{look} potion"

    def _assign_scrolls(self, rng) -> None:
        scrolls = [b.id for b in ITEMS.values() if b.category == "scroll"]
        labels = list(SCROLL_LABELS)
        rng.shuffle(labels)
        for base_id, label in zip(scrolls, labels):
            self._appearance[base_id] = f'scroll labelled "{label}"'

    # -- state -----------------------------------------------------------
    def is_type_identified(self, base: ItemBase) -> bool:
        if base.category not in APPEARANCE_CATEGORIES:
            return True
        return base.id in self._identified

    def identify_type(self, base: ItemBase) -> bool:
        """Mark a whole item type known. Returns True if newly learned."""
        if base.id in self._identified:
            return False
        self._identified.add(base.id)
        return True

    def appearance(self, base: ItemBase) -> str:
        return self._appearance.get(base.id, base.name)

    # -- naming ----------------------------------------------------------
    def display_name(self, item: Item, quantity: bool = True) -> str:
        base = item.base
        type_known = self.is_type_identified(base)

        if base.category in APPEARANCE_CATEGORIES and not type_known:
            core = self.appearance(base)
        else:
            core = base.name

        prefix = ""
        if item.buc_known:
            prefix = {BLESSED: "blessed ", CURSED: "cursed ",
                      UNCURSED: "uncursed "}[item.buc]

        suffix = ""
        if item.identified:
            bracket = item.enchant_bracket()
            if bracket:
                suffix = " " + bracket

        name = f"{prefix}{core}{suffix}"

        if quantity and item.quantity > 1:
            plural = base.pluralized() if type_known else core + "s"
            head = f"{item.quantity} "
            if base.category in APPEARANCE_CATEGORIES and not type_known:
                return f"{head}{prefix}{core}s{suffix}"
            return f"{head}{prefix}{plural}{suffix}"
        article = "an" if name[:1].lower() in "aeiou" else "a"
        return f"{article} {name}"
