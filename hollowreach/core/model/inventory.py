"""Inventory and worn equipment (design ref §11.1).

* :class:`Inventory` — a letter-indexed pack (a–z) with stacking and a
  weight total; Strength sets carrying capacity, and going over it slows
  the hero.
* :class:`Equipment` — the worn slots.  Equipping folds the item's
  enchant + BUC into the actor's cached combat values; cursed items weld
  on and refuse to come off.
"""

from __future__ import annotations

from .item import Item, CURSED, SLOT_RING, SLOT_WEAPON


class Inventory:
    LETTERS = "abcdefghijklmnopqrstuvwxyz"

    def __init__(self):
        self.slots: dict[str, Item] = {}

    def add(self, item: Item) -> "str | None":
        # Try to stack onto an existing pile first.
        for letter, existing in self.slots.items():
            if existing.can_stack_with(item):
                existing.quantity += item.quantity
                return letter
        for letter in self.LETTERS:
            if letter not in self.slots:
                self.slots[letter] = item
                return letter
        return None  # pack full (26 distinct stacks)

    def remove(self, item: Item, quantity: "int | None" = None) -> "Item | None":
        for letter, existing in list(self.slots.items()):
            if existing is item:
                if quantity is not None and quantity < existing.quantity:
                    return existing.split(quantity)
                del self.slots[letter]
                return existing
        return None

    def by_letter(self, letter: str) -> "Item | None":
        return self.slots.get(letter)

    def letter_of(self, item: Item) -> "str | None":
        for letter, existing in self.slots.items():
            if existing is item:
                return letter
        return None

    def listing(self) -> list:
        return [(letter, self.slots[letter]) for letter in sorted(self.slots)]

    def of_category(self, categories) -> list:
        return [(l, it) for l, it in self.listing() if it.category in categories]

    def total_weight(self) -> int:
        return sum(it.weight for it in self.slots.values())

    def is_empty(self) -> bool:
        return not self.slots


class Equipment:
    # Order matters for display; two ring slots share the SLOT_RING type.
    SLOTS = ["weapon", "body", "shield", "head", "cloak", "hands",
             "girdle", "boots", "neck", "ring1", "ring2"]

    def __init__(self):
        self.worn: dict[str, "Item | None"] = {s: None for s in self.SLOTS}

    def _target_slot(self, item: Item) -> "str | None":
        slot = item.slot
        if slot is None:
            return None
        if slot == SLOT_RING:
            if self.worn["ring1"] is None:
                return "ring1"
            if self.worn["ring2"] is None:
                return "ring2"
            return "ring1"  # will displace ring1
        return slot

    def equip(self, item: Item):
        """Equip ``item``. Returns ``(ok, displaced_item, message)``."""
        target = self._target_slot(item)
        if target is None:
            return False, None, f"You can't wear the {item.name}."
        # Two-handed weapons need both hands; a shield blocks them (and
        # vice versa). The player must free the other slot first.
        if target == "weapon" and item.base.two_handed and self.worn["shield"]:
            return False, None, (
                f"You need both hands for the {item.name} — "
                f"your shield is in the way.")
        if target == "shield":
            weapon = self.worn["weapon"]
            if weapon is not None and weapon.base.two_handed:
                return False, None, (
                    f"Your {weapon.name} needs both hands — "
                    f"you can't hold a shield too.")
        current = self.worn[target]
        if current is not None and current.buc == CURSED:
            current.buc_known = True
            return False, None, (
                f"The {current.name} is cursed — you cannot remove it!")
        self.worn[target] = item
        displaced = current
        verb = "wield" if target == "weapon" else "put on"
        msg = f"You {verb} the {item.name}."
        if item.buc == CURSED:
            item.buc_known = True
            msg += " It welds itself on!"
        return True, displaced, msg

    def unequip(self, slot: str):
        """Take off the item in ``slot``. Returns ``(ok, item, message)``."""
        item = self.worn.get(slot)
        if item is None:
            return False, None, "Nothing there to remove."
        if item.buc == CURSED:
            item.buc_known = True
            return False, None, (
                f"The {item.name} is cursed — it won't come off!")
        self.worn[slot] = None
        return True, item, f"You take off the {item.name}."

    def slot_of(self, item: Item) -> "str | None":
        for slot, worn in self.worn.items():
            if worn is item:
                return slot
        return None

    def worn_items(self) -> list:
        return [(s, it) for s in self.SLOTS if (it := self.worn[s]) is not None]

    def weapon(self) -> "Item | None":
        return self.worn["weapon"]

    def recompute(self, actor) -> None:
        """Fold worn gear into the actor's cached combat values (§7.2)."""
        armor_dv = 0
        armor_pv = 0
        for slot, item in self.worn_items():
            if slot == "weapon":
                continue
            armor_dv += item.dv_bonus
            armor_pv += item.pv_bonus
        weapon = self.worn["weapon"]
        if weapon is not None:
            actor.weapon_dice = weapon.base.dmg_dice
            actor.weapon_to_hit = weapon.base.to_hit + weapon.weapon_bonus
            actor.weapon_dmg_bonus = weapon.weapon_bonus
            armor_dv += weapon.base.dv  # parry
            actor.unarmed = False
        else:
            actor.weapon_dice = "1d3"   # unarmed
            actor.weapon_to_hit = 0
            actor.weapon_dmg_bonus = 0
            actor.unarmed = True
        actor.armor_dv = armor_dv
        actor.armor_pv = armor_pv


def carrying_capacity(strength: int) -> int:
    """Weight the hero can bear before being burdened."""
    return 800 + strength * 120


def encumbrance_penalty(weight: int, capacity: int) -> int:
    """Speed penalty for exceeding carrying capacity."""
    if weight <= capacity:
        return 0
    over = weight - capacity
    return min(60, 10 + over // 100 * 10)
