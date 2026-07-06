"""Tests for the magic system: spells, PP, knowledge, and resolution (§8)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.core.model.character import make_monster
from hollowreach.core.generation.loot import make_item
from hollowreach.content.monsters import MONSTERS
from hollowreach.core.rules.magic import resist_mult

import main


def _game(cls="wizard", sign="beacon"):
    return main.make_game(4, "Mage", "human", cls, sign, "male",
                          permadeath=False)


def _put_monster(game, mid, dx, dy, hp=200):
    lvl = game.levels[game.depth]
    a = game.pc.actor
    m = make_monster(MONSTERS[mid], game.rng, depth=1)
    m.max_hp = m.hp = hp
    m.x, m.y = a.x + dx, a.y + dy
    lvl.add_actor(m)
    game.scheduler.add(m)
    return m


class CasterSetupTests(unittest.TestCase):
    def test_wizard_starts_with_spells_and_pp(self):
        game = _game("wizard")
        self.assertIn("mind_dart", game.pc.spells)
        self.assertGreaterEqual(game.pc.actor.max_pp, 8)

    def test_fighter_has_no_spells(self):
        game = _game("fighter")
        self.assertEqual(game.pc.spells, {})


class CastingTests(unittest.TestCase):
    def test_bolt_damages_monster_and_spends_resources(self):
        game = _game("wizard")
        a = game.pc.actor
        mon = _put_monster(game, "kobold", 1, 0)
        pp0 = a.pp
        castings0 = game.pc.spells["mind_dart"]["castings"]
        acted = game.cast_spell("mind_dart", (1, 0))
        self.assertTrue(acted)
        self.assertLess(mon.hp, mon.max_hp)
        self.assertLess(a.pp, pp0)
        self.assertEqual(game.pc.spells["mind_dart"]["castings"], castings0 - 1)

    def test_bolt_hits_whole_line(self):
        game = _game("wizard")
        m1 = _put_monster(game, "kobold", 1, 0)
        m2 = _put_monster(game, "kobold", 2, 0)
        game.cast_spell("mind_dart", (1, 0))
        self.assertLess(m1.hp, m1.max_hp)
        self.assertLess(m2.hp, m2.max_hp)

    def test_no_pp_blocks_cast(self):
        game = _game("wizard")
        game.pc.actor.pp = 0
        castings0 = game.pc.spells["mind_dart"]["castings"]
        self.assertFalse(game.cast_spell("mind_dart", (1, 0)))
        self.assertEqual(game.pc.spells["mind_dart"]["castings"], castings0)

    def test_no_castings_blocks_cast(self):
        game = _game("wizard")
        game.pc.spells["mind_dart"]["castings"] = 0
        self.assertFalse(game.cast_spell("mind_dart", (1, 0)))

    def test_heal_restores_hp(self):
        game = _game("priest")
        a = game.pc.actor
        a.hp = 3
        game.cast_spell("mend_wounds", None)
        self.assertGreater(a.hp, 3)

    def test_power_grows_with_practice(self):
        game = _game("wizard")
        state = game.pc.spells["mind_dart"]
        state["casts"] = 19
        state["castings"] = 50
        p0 = state["power"]
        _put_monster(game, "kobold", 1, 0)
        game.cast_spell("mind_dart", (1, 0))     # 20th cast
        self.assertEqual(state["power"], p0 + 1)


class ResistanceTests(unittest.TestCase):
    def test_force_never_resisted(self):
        self.assertEqual(resist_mult("force", ("demon", "hollowed")), 1.0)

    def test_light_scorches_hollowed(self):
        self.assertGreater(resist_mult("light", ("hollowed",)), 1.0)

    def test_demon_resists_fire(self):
        self.assertLess(resist_mult("fire", ("demon",)), 1.0)


class SpellbookTests(unittest.TestCase):
    def test_reading_book_teaches_spell(self):
        game = _game("fighter")
        book = make_item("book_mind_dart", game.rng, buc="uncursed", enchant=0)
        game.pc.inventory.add(book)
        acted = game.use_item(book)
        self.assertTrue(acted)
        self.assertIn("mind_dart", game.pc.spells)
        # The book is not consumed.
        self.assertIn(book, [it for _l, it in game.pc.inventory.listing()])


class CostModifierTests(unittest.TestCase):
    def test_ember_omen_cheapens_fire(self):
        beacon = _game("wizard", "beacon")
        ember = _game("wizard", "ember")
        from hollowreach.content.spells import SPELLS
        spell = SPELLS["cinderbolt"]
        b = beacon._spell_cost(spell, beacon.pc.spells["cinderbolt"])
        e = ember._spell_cost(spell, ember.pc.spells["cinderbolt"])
        self.assertLess(e, b)


if __name__ == "__main__":
    unittest.main()
