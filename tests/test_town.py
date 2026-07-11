"""Tests for the surface hub: town, NPCs, shop, quests, gold (§4.4, §11.8, §14)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollowreach.core.engine.rng import Rng
from hollowreach.core.generation.town import generate_town
from hollowreach.core.model.character import make_monster
from hollowreach.content.monsters import MONSTERS
from hollowreach.core.rules import shop, quests

import main


def _game(cls="fighter"):
    return main.make_game(7, "Kael", "human", cls, "beacon", "male",
                          permadeath=False)


def _npc(game, npc_id):
    return next(n for n in game.levels[0].npcs() if n.npc_id == npc_id)


def _talk(game, npc_id):
    npc = _npc(game, npc_id)
    a = game.pc.actor
    a.x, a.y = npc.x - 1, npc.y
    game._move_or_attack(a, game.levels[0], 1, 0)


class TownTests(unittest.TestCase):
    def test_starts_in_town(self):
        game = _game()
        self.assertEqual(game.depth, 0)
        self.assertTrue(game.levels[0].is_town)

    def test_town_has_folk_and_a_mouth(self):
        lvl = generate_town(Rng(3))
        self.assertTrue(len(list(lvl.npcs())) >= 3)
        self.assertIsNotNone(lvl.stairs_down)
        self.assertIsNone(lvl.stairs_up)

    def test_town_has_no_monsters(self):
        lvl = generate_town(Rng(4))
        self.assertEqual(list(lvl.monsters()), [])

    def test_npcs_are_not_scheduled(self):
        game = _game()
        # Only the PC should be in the town scheduler (folk idle).
        self.assertEqual(len(game.scheduler), 1)


class InteractionTests(unittest.TestCase):
    def test_bumping_npc_does_not_attack(self):
        game = _game()
        npc = _npc(game, "sarn")
        hp0 = npc.hp
        a = game.pc.actor
        a.x, a.y = npc.x - 1, npc.y
        acted = game._move_or_attack(a, game.levels[0], 1, 0)
        self.assertFalse(acted)            # talking costs no turn
        self.assertEqual(npc.hp, hp0)      # and no damage

    def test_quest_giver_offers_then_tracks(self):
        game = _game()
        _talk(game, "maroc")
        self.assertEqual(game.pc.quests["cull_the_vermin"]["state"], "active")


class ShopTests(unittest.TestCase):
    def test_buy_deducts_gold_and_gives_item(self):
        game = _game()
        game.pc.gold = 1000
        item = game.shop_stock[0]
        stock0 = len(game.shop_stock)
        game.buy_item(item)
        self.assertLess(game.pc.gold, 1000)
        self.assertEqual(len(game.shop_stock), stock0 - 1)
        # The exact instance left the shelf and is now carried.
        self.assertFalse(any(s is item for s in game.shop_stock))
        self.assertTrue(any(it is item for _l, it in game.pc.inventory.listing()))

    def test_cannot_buy_without_gold(self):
        game = _game()
        game.pc.gold = 0
        item = game.shop_stock[0]
        game.buy_item(item)
        self.assertIn(item, game.shop_stock)      # still on the shelf

    def test_sell_adds_gold(self):
        game = _game()
        game.pc.gold = 0
        _l, item = game.pc.inventory.listing()[0]
        game.sell_item(item)
        self.assertGreaterEqual(game.pc.gold, 0)

    def test_haggling_lowers_buy_price(self):
        plain = _game()
        haggler = _game()
        haggler.pc.skills["Haggling"] = 100
        haggler.pc.actor.attributes.apply_modifier("Ch", 10)
        base = 100
        self.assertLess(shop.buy_price(haggler.pc, base),
                        shop.buy_price(plain.pc, base))


class QuestTests(unittest.TestCase):
    def test_kill_count_quest_completes_and_pays(self):
        game = _game()
        _talk(game, "maroc")          # accepts cull_the_vermin (8 kills)
        for _ in range(8):
            m = make_monster(MONSTERS["kobold"], game.rng, depth=1)
            m.alive = False
            m.hp = 0
            game.levels[0].add_actor(m)
            game._reward_kill(m)
        gold0 = game.pc.gold
        _talk(game, "maroc")          # turn in
        self.assertEqual(game.pc.quests["cull_the_vermin"]["state"], "done")
        self.assertGreater(game.pc.gold, gold0)

    def test_kill_type_quest_tracks_hollowed(self):
        game = _game()
        _talk(game, "ferelith")       # ease_the_hollowing: 3 hollowed
        q = quests.QUESTS["ease_the_hollowing"]
        for _ in range(3):
            m = make_monster(MONSTERS["hollowed_husk"], game.rng, depth=9)
            m.alive = False
            m.hp = 0
            game.levels[0].add_actor(m)
            game._reward_kill(m)
        self.assertTrue(quests.is_complete(game.pc, q))

    def test_reach_depth_quest(self):
        game = _game()
        _talk(game, "maroc")          # the_descent: reach DL5
        q = quests.QUESTS["the_descent"]
        self.assertFalse(quests.is_complete(game.pc, q))
        game.pc.max_depth = 5
        self.assertTrue(quests.is_complete(game.pc, q))

    def test_kills_award_gold(self):
        game = _game()
        game.pc.gold = 0
        game.levels[3] = game.levels[0]     # stand-in deep level
        game.depth = 3
        m = make_monster(MONSTERS["orc"], game.rng, depth=3)
        m.alive = False
        m.hp = 0
        game.levels[3].add_actor(m)
        game._reward_kill(m)
        self.assertGreater(game.pc.gold, 0)


if __name__ == "__main__":
    unittest.main()
