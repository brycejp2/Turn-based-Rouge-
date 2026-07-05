"""Item instantiation and loot rolls (design ref §11.2, §11.3).

``make_item`` turns a base id into a concrete :class:`Item`, rolling BUC
(10% blessed / 10% cursed) and an occasional enchantment.  ``roll_loot``
draws from the depth-keyed spawn table so deeper levels yield heavier
gear.
"""

from __future__ import annotations

from ..model.item import Item, ItemBase, BLESSED, UNCURSED, CURSED
from ...content.items import ITEMS, item_spawn_table


def make_item(base_id: str, rng, buc: "str | None" = None,
              enchant: "int | None" = None, quantity: "int | None" = None) -> Item:
    base = ITEMS[base_id]
    if buc is None:
        roll = rng.rnd(100)
        buc = BLESSED if roll <= 10 else CURSED if roll <= 20 else UNCURSED
    if enchant is None:
        # Most gear is +0; a minority carries a small +/- enchant.
        if base.slot is not None:
            e = rng.rnd(100)
            enchant = 1 if e <= 12 else 2 if e <= 16 else -1 if e <= 22 else 0
        else:
            enchant = 0
    if quantity is None:
        # Only auto-roll a stack size when the caller didn't specify one.
        if base.stackable and base.category in ("scroll", "potion"):
            quantity = 1 if rng.rnd(100) > 20 else rng.rnd(2) + 1
        else:
            quantity = 1
    return Item(base=base, buc=buc, enchant=enchant, quantity=quantity)


def roll_loot(rng, depth: int) -> Item:
    table = item_spawn_table(depth)
    base_id = rng.weighted_choice(table)
    return make_item(base_id, rng)
