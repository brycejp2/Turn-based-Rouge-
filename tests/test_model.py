"""Tests for attributes, actor combat formulas, and character build
(§5.1, §5.2, §5.4, §7.2)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adom.core.engine.rng import Rng
from adom.core.model.attributes import Attributes
from adom.core.model.actor import Actor
from adom.core.model.character import build_player, make_monster
from adom.content.monsters import MONSTERS
from adom.core.rules.combat import melee_attack


class AttributeTests(unittest.TestCase):
    def test_clamp_1_to_99(self):
        a = Attributes({"St": 10})
        a.apply_modifier("St", 200)
        self.assertEqual(a.St, 99)
        a.apply_modifier("St", -500)
        self.assertEqual(a.St, 1)

    def test_potential_caps_training(self):
        a = Attributes({"To": 10}, {"To": 12})
        self.assertTrue(a["To"].train(5))     # 10 -> 12 (capped at potential)
        self.assertEqual(a["To"].base, 12)
        self.assertFalse(a["To"].train(5))    # already at potential

    def test_modified_value(self):
        a = Attributes({"Dx": 15})
        a.apply_modifier("Dx", 3)
        self.assertEqual(a.Dx, 18)


class ActorFormulaTests(unittest.TestCase):
    def _actor(self, dx, to):
        return Actor("x", "@", Attributes({"Dx": dx, "To": to}))

    def test_dv_formula(self):
        # DV = trunc((Dx-12)/2) + trunc((Dx-9)/2)  (§7.2)
        a = self._actor(dx=18, to=10)
        self.assertEqual(a.dv, (18 - 12) // 2 + (18 - 9) // 2)  # 3 + 4 = 7

    def test_pv_formula_and_cap(self):
        a = self._actor(dx=10, to=28)
        self.assertEqual(a.pv, (28 - 18) // 2)  # 5
        a2 = self._actor(dx=10, to=99)
        self.assertLessEqual(a2.pv, 20)          # capped +20

    def test_pv_zero_below_threshold(self):
        a = self._actor(dx=10, to=12)
        self.assertEqual(a.pv, 0)

    def test_blessed_pv_bonus(self):
        a = self._actor(dx=10, to=20)
        base = a.pv
        a.blessed = True
        self.assertEqual(a.pv, base + 1)


class CombatTests(unittest.TestCase):
    def test_hit_always_deals_at_least_one(self):
        rng = Rng(4)
        atk = Actor("hero", "@", Attributes({"St": 30, "Dx": 30}))
        atk.weapon_dice = "1d4"
        defn = Actor("wall", "W", Attributes({"To": 99, "Dx": 1}))
        defn.armor_pv = 50
        defn.max_hp = defn.hp = 100
        hits = [melee_attack(atk, defn, rng) for _ in range(50)]
        for r in hits:
            if r.hit:
                self.assertGreaterEqual(r.damage, 1)

    def test_kill_flag(self):
        rng = Rng(9)
        atk = Actor("hero", "@", Attributes({"St": 40, "Dx": 40}))
        atk.weapon_dice = "10d10"
        defn = Actor("rat", "r", Attributes({"To": 1, "Dx": 1}))
        defn.max_hp = defn.hp = 1
        result = None
        for _ in range(20):
            result = melee_attack(atk, defn, rng)
            if result.killed:
                break
        self.assertTrue(result.killed)
        self.assertFalse(defn.is_alive)


class CharacterBuildTests(unittest.TestCase):
    def test_raven_speed_bonus(self):
        rng = Rng(1)
        pc = build_player("R", "human", "fighter", "raven", "male",
                          {"St": 12, "Dx": 12, "To": 12, "Ma": 10, "Pe": 10}, rng)
        self.assertEqual(pc.actor.base_speed, 110)  # Raven +10 (§5.4)

    def test_dwarf_mithril_skin(self):
        rng = Rng(1)
        pc = build_player("D", "dwarf", "fighter", "candle", "male",
                          {"St": 14, "Dx": 12, "To": 16, "Ma": 8, "Pe": 10}, rng)
        self.assertEqual(pc.actor.mithril_skin, 3)  # dwarf-only +3 PV

    def test_troll_xp_penalty(self):
        rng = Rng(1)
        pc = build_player("T", "troll", "barbarian", "wolf", "male",
                          {"St": 18, "Dx": 10, "To": 18, "Ma": 4, "Pe": 8}, rng)
        self.assertEqual(pc.race.xp_mult, 2.5)  # slow leveling (§5.2)

    def test_universal_starting_skills(self):
        rng = Rng(1)
        pc = build_player("S", "human", "fighter", "candle", "male",
                          {"Le": 12}, rng)
        for skill in ("Climbing", "First Aid", "Haggling", "Listening"):
            self.assertIn(skill, pc.skills)

    def test_monster_scaling_with_depth(self):
        rng = Rng(1)
        shallow = make_monster(MONSTERS["orc"], Rng(1), depth=1)
        deep = make_monster(MONSTERS["orc"], Rng(1), depth=10)
        self.assertGreater(deep.dv, shallow.dv)  # DV ~ +0.7*level (§12.1)


if __name__ == "__main__":
    unittest.main()
