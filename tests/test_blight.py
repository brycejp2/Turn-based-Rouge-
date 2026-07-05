"""Tests for the Blight clock — the Hollowing pressure mechanic (§9)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.content.warps import WARPS, BLIGHT_PER_WARP, MAX_WARPS
from hollowreach.core.generation.loot import make_item
from hollowreach.core.model.item import BLESSED, UNCURSED, CURSED

import main


def _game(sign="beacon", **kw):
    return main.make_game(7, "T", "human", "fighter", sign, "male",
                          permadeath=False, **kw)


class RateTests(unittest.TestCase):
    def test_shallow_is_safe(self):
        game = _game()
        self.assertEqual(game.blight.rate_per_turn(game.pc, 1), 0.0)
        self.assertEqual(game.blight.rate_per_turn(game.pc, 2), 0.0)

    def test_deeper_is_faster(self):
        game = _game()
        r5 = game.blight.rate_per_turn(game.pc, 5)
        r15 = game.blight.rate_per_turn(game.pc, 15)
        self.assertGreater(r5, 0.0)
        self.assertGreater(r15, r5)

    def test_warden_omen_slows_it(self):
        plain = _game(sign="beacon")
        warden = _game(sign="warden")
        self.assertLess(warden.blight.rate_per_turn(warden.pc, 12),
                        plain.blight.rate_per_turn(plain.pc, 12))

    def test_disabled_never_accrues(self):
        game = _game(blight_enabled=False)
        self.assertEqual(game.blight.rate_per_turn(game.pc, 20), 0.0)
        game.blight.on_turn(game.pc, 20)
        self.assertEqual(game.pc.blight_points, 0.0)


class WarpApplicationTests(unittest.TestCase):
    def _force_order(self, game, first):
        # Deterministic Warp order so we can assert exact effects.
        rest = [w for w in game.blight._order if w != first]
        game.blight._order = [first] + rest

    def test_warp_applies_effects(self):
        game = _game()
        self._force_order(game, "ashen_skin")
        a = game.pc.actor
        dx0, ap0, pv0 = a.attributes.Dx, a.attributes.Ap, a.pv
        events = game.blight.add_blight(game.pc, BLIGHT_PER_WARP)
        self.assertEqual([e.kind for e in events], ["warp"])
        self.assertEqual(game.pc.warps, ["ashen_skin"])
        # ashen skin: Dx -2, Ap -3, PV +4
        self.assertEqual(a.attributes.Dx, dx0 - 2)
        self.assertEqual(a.attributes.Ap, ap0 - 3)
        self.assertEqual(a.pv, pv0 + 4)

    def test_cleanse_reverses_a_warp(self):
        game = _game()
        self._force_order(game, "ashen_skin")
        a = game.pc.actor
        pv0 = a.pv
        game.blight.add_blight(game.pc, BLIGHT_PER_WARP)
        self.assertEqual(a.pv, pv0 + 4)
        events = game.blight.cleanse(game.pc, BLIGHT_PER_WARP)
        self.assertEqual([e.kind for e in events], ["cured"])
        self.assertEqual(game.pc.warps, [])
        self.assertEqual(a.pv, pv0)   # effect fully reversed

    def test_night_vision_special(self):
        game = _game()
        self._force_order(game, "voidsight")
        game.blight.add_blight(game.pc, BLIGHT_PER_WARP)
        self.assertTrue(game.pc.actor.night_vision)
        game.blight.cleanse(game.pc, BLIGHT_PER_WARP)
        self.assertFalse(game.pc.actor.night_vision)

    def test_consumed_at_max(self):
        game = _game()
        events = game.blight.add_blight(game.pc, BLIGHT_PER_WARP * (MAX_WARPS + 1))
        self.assertTrue(any(e.kind == "consumed" for e in events))
        self.assertEqual(len(game.pc.warps), MAX_WARPS)


class ConsumableIntegrationTests(unittest.TestCase):
    def test_cleansing_potion_reduces_blight(self):
        game = _game()
        game.blight.add_blight(game.pc, BLIGHT_PER_WARP + 50)
        before = game.pc.blight_points
        potion = make_item("potion_cleansing", game.rng, buc=UNCURSED, enchant=0)
        game.pc.inventory.add(potion)
        game.use_item(potion)
        self.assertLess(game.pc.blight_points, before)

    def test_cursed_cleansing_backfires(self):
        game = _game()
        game.blight.add_blight(game.pc, 30)
        before = game.pc.blight_points
        potion = make_item("potion_cleansing", game.rng, buc=CURSED, enchant=0)
        game.pc.inventory.add(potion)
        game.use_item(potion)
        self.assertGreater(game.pc.blight_points, before)


class GameLoopIntegrationTests(unittest.TestCase):
    def test_blight_accrues_over_turns_deep(self):
        game = _game()
        # Pretend we're deep and take several turns.
        game.depth = 12
        game.levels[12] = game.levels[game.depth if game.depth in game.levels else 1]
        for _ in range(30):
            game._advance_blight()
        self.assertGreater(game.pc.blight_points, 0.0)


if __name__ == "__main__":
    unittest.main()
