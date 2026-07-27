"""Tests for the divine economy: alignment, piety, sacrifice, prayer,
crowning (§10)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.rules import religion
from hollowreach.core.world import tile as tiles
from hollowreach.core.model.character import make_monster
from hollowreach.content.monsters import MONSTERS

import main


def _game(cls="priest", sign="tome", race="human"):
    return main.make_game(7, "Devout", race, cls, sign, "male",
                          permadeath=False)


def _stand_on_town_altar(game):
    lvl = game.levels[0]
    for y in range(lvl.height):
        for x in range(lvl.width):
            if tiles.altar_alignment(lvl.tile(x, y)) is not None:
                game.pc.actor.x, game.pc.actor.y = x, y
                return tiles.altar_alignment(lvl.tile(x, y))
    return None


class AlignmentTests(unittest.TestCase):
    def test_band_and_extreme(self):
        self.assertEqual(religion.band(1000), "lawful")
        self.assertEqual(religion.band(0), "neutral")
        self.assertEqual(religion.band(-1000), "chaotic")
        self.assertTrue(religion.is_extreme(2500))
        self.assertFalse(religion.is_extreme(1000))

    def test_alignment_is_score_derived(self):
        game = _game(race="troll", sign="beacon")   # chaotic race, neutral omen
        self.assertEqual(game.pc.alignment, "chaotic")
        game.pc.alignment_score = 900
        self.assertEqual(game.pc.alignment, "lawful")

    def test_slaying_hollowed_pulls_lawful(self):
        game = _game()
        game.levels[9] = game.levels[0]
        game.depth = 9
        before = game.pc.alignment_score
        m = make_monster(MONSTERS["hollowed_husk"], game.rng, depth=9)
        m.alive = False
        m.hp = 0
        game.levels[9].add_actor(m)
        game._reward_kill(m)
        self.assertGreater(game.pc.alignment_score, before)


class SacrificeTests(unittest.TestCase):
    def test_town_altar_matches_hero(self):
        game = _game()
        align = _stand_on_town_altar(game)
        self.assertEqual(align, game.pc.alignment)

    def test_offer_gold_gives_piety(self):
        game = _game()
        _stand_on_town_altar(game)
        game.pc.gold = 1000
        piety0 = game.pc.piety
        game._offer()
        self.assertGreater(game.pc.piety, piety0)
        self.assertEqual(game.pc.gold, 0)

    def test_dwarf_tithes_more(self):
        human = _game(race="human")
        dwarf = _game(race="dwarf")
        # Force both neutral so the town altar matches.
        self.assertGreater(religion._gold_rate(dwarf.pc),
                           religion._gold_rate(human.pc))

    def test_drop_on_altar_reveals_buc(self):
        game = _game()
        _stand_on_town_altar(game)
        from hollowreach.core.generation.loot import make_item
        item = make_item("dagger", game.rng, buc="cursed", enchant=0)
        game.pc.inventory.add(item)
        game.drop_item(item)      # co-aligned altar => sacrificed, BUC known
        self.assertTrue(item.buc_known)


class PrayerTests(unittest.TestCase):
    def test_pray_heals_when_hurt(self):
        game = _game()
        game.pc.piety = 2000
        game.pc.actor.hp = 3
        game._pray()
        self.assertGreater(game.pc.actor.hp, 3)

    def test_pray_eases_the_hollowing(self):
        game = _game()
        game.pc.piety = 2000
        game.pc.actor.hp = game.pc.actor.max_hp   # so heal branch is skipped
        game.blight.add_blight(game.pc, 200)       # one warp
        warps0 = len(game.pc.warps)
        game._pray()
        self.assertLess(len(game.pc.warps), warps0)

    def test_faithless_prayer_is_rebuked(self):
        game = _game(cls="fighter")   # starts with low piety
        game.pc.piety = 10
        hp0 = game.pc.actor.hp
        game._pray()
        self.assertLess(game.pc.actor.hp, hp0)     # retribution


class CrowningTests(unittest.TestCase):
    def test_crowning_requires_extreme_and_piety(self):
        game = _game()
        game.pc.actor.hp = game.pc.actor.max_hp
        game.pc.alignment_score = 2500
        game.pc.piety = religion.CROWNING_PIETY + 100
        game._pray()
        self.assertTrue(game.pc.crowned)
        self.assertTrue(game.pc.actor.blessed)

    def test_no_crown_when_not_extreme(self):
        game = _game()
        game.pc.actor.hp = game.pc.actor.max_hp
        game.pc.alignment_score = 500        # neutral, not extreme
        game.pc.piety = 9000
        game._pray()
        self.assertFalse(game.pc.crowned)

    def test_chaotic_crowning_warps(self):
        game = _game(race="troll")           # chaotic
        game.pc.actor.hp = game.pc.actor.max_hp
        game.pc.alignment_score = -2500
        game.pc.piety = religion.CROWNING_PIETY + 100
        warps0 = len(game.pc.warps)
        game._pray()
        self.assertTrue(game.pc.crowned)
        self.assertGreater(len(game.pc.warps), warps0)  # devil's bargain


if __name__ == "__main__":
    unittest.main()
