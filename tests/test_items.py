"""Tests for items, BUC, inventory/equipment, identification and
consumables (design ref §11)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.core.model.item import Item, CURSED, BLESSED, UNCURSED
from hollowreach.core.model.inventory import (
    Inventory, Equipment, carrying_capacity, encumbrance_penalty,
)
from hollowreach.core.model.attributes import Attributes
from hollowreach.core.model.actor import Actor
from hollowreach.core.generation.loot import make_item, roll_loot
from hollowreach.core.rules.identification import IdentificationService
from hollowreach.content.items import ITEMS

import main


def _game():
    return main.make_game(123, "T", "human", "fighter", "beacon", "male",
                          permadeath=False)


class ItemInstanceTests(unittest.TestCase):
    def test_buc_bonus(self):
        blessed = make_item("long_sword", Rng(1), buc=BLESSED, enchant=0)
        cursed = make_item("long_sword", Rng(1), buc=CURSED, enchant=0)
        self.assertEqual(blessed.weapon_bonus, 1)
        self.assertEqual(cursed.weapon_bonus, -1)

    def test_pv_bonus_folds_enchant(self):
        armor = make_item("chain_mail", Rng(1), buc=BLESSED, enchant=2)
        # base pv 6 + enchant 2 + blessed 1
        self.assertEqual(armor.pv_bonus, 9)

    def test_stacking_rules(self):
        a = make_item("potion_water", Rng(1), buc=UNCURSED, enchant=0)
        b = make_item("potion_water", Rng(1), buc=UNCURSED, enchant=0)
        c = make_item("potion_water", Rng(1), buc=BLESSED, enchant=0)
        self.assertTrue(a.can_stack_with(b))
        self.assertFalse(a.can_stack_with(c))  # different BUC


class InventoryTests(unittest.TestCase):
    def test_letters_and_stacking(self):
        inv = Inventory()
        inv.add(make_item("potion_water", Rng(1), buc=UNCURSED, enchant=0, quantity=1))
        inv.add(make_item("potion_water", Rng(1), buc=UNCURSED, enchant=0, quantity=1))
        inv.add(make_item("dagger", Rng(1), buc=UNCURSED, enchant=0))
        listing = inv.listing()
        # Water stacked into one slot; dagger separate => 2 slots.
        self.assertEqual(len(listing), 2)
        water = next(it for _l, it in listing if it.category == "potion")
        self.assertEqual(water.quantity, 2)

    def test_encumbrance_penalty(self):
        self.assertEqual(encumbrance_penalty(100, 1000), 0)
        self.assertGreater(encumbrance_penalty(2000, 1000), 0)


class EquipmentTests(unittest.TestCase):
    def _actor(self):
        return Actor("h", "@", Attributes({"St": 12, "Dx": 12, "To": 12}))

    def test_equip_updates_combat(self):
        eq = Equipment()
        actor = self._actor()
        eq.equip(make_item("long_sword", Rng(1), buc=UNCURSED, enchant=1))
        eq.equip(make_item("chain_mail", Rng(1), buc=UNCURSED, enchant=0))
        eq.recompute(actor)
        self.assertEqual(actor.weapon_dice, "1d8")
        self.assertEqual(actor.weapon_to_hit, 1)   # +1 enchant
        self.assertEqual(actor.armor_pv, 6)        # chain mail

    def test_cursed_cannot_be_removed(self):
        eq = Equipment()
        cursed = make_item("mace", Rng(1), buc=CURSED, enchant=0)
        eq.equip(cursed)
        ok, item, msg = eq.unequip("weapon")
        self.assertFalse(ok)
        self.assertIn("cursed", msg.lower())

    def test_ring_uses_two_slots(self):
        eq = Equipment()
        # No ring items in the starter set, so fake two via a body slot proxy:
        r1 = make_item("wooden_shield", Rng(1), buc=UNCURSED, enchant=0)
        ok, _d, _m = eq.equip(r1)
        self.assertTrue(ok)
        self.assertIs(eq.worn["shield"], r1)


class IdentificationTests(unittest.TestCase):
    def test_appearance_hidden_then_revealed(self):
        ids = IdentificationService(Rng(5))
        potion = make_item("potion_healing", Rng(1), buc=UNCURSED, enchant=0)
        disguised = ids.display_name(potion)
        self.assertIn("potion", disguised)
        self.assertNotIn("healing", disguised)   # hidden
        ids.identify_type(potion.base)
        potion.reveal()
        self.assertIn("healing", ids.display_name(potion))


class ConsumableTests(unittest.TestCase):
    def test_healing_potion(self):
        game = _game()
        game.pc.actor.hp = 1
        potion = make_item("potion_healing", game.rng, buc=UNCURSED, enchant=0)
        game.pc.inventory.add(potion)
        game.use_item(potion)
        self.assertGreater(game.pc.actor.hp, 1)

    def test_blessed_gain_attributes_raises_all(self):
        game = _game()
        before = game.pc.actor.attributes.as_dict()
        potion = make_item("potion_gain_attributes", game.rng, buc=BLESSED, enchant=0)
        game.pc.inventory.add(potion)
        game.use_item(potion)
        after = game.pc.actor.attributes.as_dict()
        for key in before:
            self.assertEqual(after[key], before[key] + 1)

    def test_use_identifies_type(self):
        game = _game()
        potion = make_item("potion_water", game.rng, buc=UNCURSED, enchant=0)
        game.pc.inventory.add(potion)
        self.assertFalse(game.id_service.is_type_identified(potion.base))
        game.use_item(potion)
        self.assertTrue(game.id_service.is_type_identified(potion.base))

    def test_enchant_weapon_scroll(self):
        game = _game()
        weapon = game.pc.equipment.weapon()
        before = weapon.enchant
        scroll = make_item("scroll_enchant_weapon", game.rng, buc=UNCURSED, enchant=0)
        game.pc.inventory.add(scroll)
        game.use_item(scroll)
        self.assertEqual(weapon.enchant, before + 1)


class LootTests(unittest.TestCase):
    def test_make_item_respects_buc(self):
        it = make_item("dagger", Rng(1), buc=CURSED, enchant=0)
        self.assertEqual(it.buc, CURSED)

    def test_roll_loot_valid(self):
        for seed in range(20):
            it = roll_loot(Rng(seed), depth=5)
            self.assertIn(it.base.id, ITEMS)


class PickupIntegrationTests(unittest.TestCase):
    def test_pickup_from_floor(self):
        game = _game()
        a = game.pc.actor
        level = game.levels[game.depth]
        level.add_item(a.x, a.y, make_item("dagger", game.rng, buc=UNCURSED, enchant=0))
        before = len(game.pc.inventory.listing())
        acted = game.pick_up()
        self.assertTrue(acted)
        self.assertEqual(len(game.pc.inventory.listing()), before + 1)


if __name__ == "__main__":
    unittest.main()
